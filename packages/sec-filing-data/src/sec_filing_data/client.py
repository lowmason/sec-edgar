"""The SEC client: one GET at a time, each written to the ledger before and after it is sent.

It keeps the plan's client rules: a declared User-Agent, request starts at least 0.34 s
apart, at most 5 attempts per URL, a size limit per response and the budget of the whole
stage. It reads the raw body and decodes gzip and deflate itself, because urllib3's
`raw.tell()` stays 0 for a chunked response, and wire bytes must be measured.
"""

import dataclasses
import fcntl
import hashlib
import math
import os
import random
import time
import uuid
import zlib
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO

import requests

from sec_filing_data.ledger import (
    MAX_REQUESTS,
    MAX_RESPONSE_BYTES,
    MAX_WIRE_BYTES,
    Usage,
    append,
    ledger_usage,
)

REQUEST_SPACING = 0.34
MAX_ATTEMPTS = 5
BACKOFF_CAP = 120
TIMEOUTS = (15, 60)
PIECE_BYTES = 1 << 20
BUDGET_MARGIN = 1_048_576
ACCEPT_ENCODING = "gzip, deflate"
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
TRANSIENT_ERRORS = (
    requests.ConnectionError,
    requests.Timeout,
    requests.exceptions.ChunkedEncodingError,
)

_GZIP_WBITS = 16 + zlib.MAX_WBITS
_RAW_DEFLATE_WBITS = -zlib.MAX_WBITS
_URLLIB3_ERRORS = requests.packages.urllib3.exceptions


class BudgetExhausted(Exception):
    """The ledger shows that the request or wire-byte budget is spent."""


class AccessDenied(Exception):
    """SEC answered 403. The run must stop."""


@dataclass(frozen=True)
class FetchResult:
    """The final attempt of one fetch. Byte counts and the hash come from its response record."""

    key: str
    url: str
    outcome: str
    status: int | None
    attempts: int
    wire_bytes: int
    body_bytes: int
    sha256: str | None
    fetched_at: datetime | None
    reason: str | None


@contextmanager
def exclusive_lock(path: Path) -> Iterator[None]:
    """Hold an exclusive `flock` on `path`, so that no other fetch runs at the same time."""
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError(f"another fetch holds {path}") from None
        try:
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)


@dataclass
class _Received:
    """What one attempt has received so far. It is kept current while the body streams."""

    response: requests.Response | None = None
    wire_bytes: int = 0
    body_bytes: int | None = None


@dataclass(frozen=True)
class _Verdict:
    outcome: str
    reason: str | None = None
    sha256: str | None = None
    retry_after: float | None = None


@dataclass(frozen=True)
class _Answer:
    record: dict
    at: datetime
    retry_after: float | None


class _Decoder:
    """Decode a gzip, deflate or identity body piece by piece.

    Each decoded block holds at most `PIECE_BYTES`, so that a high-ratio piece is checked
    against the size limit before all of it is decoded. A deflate body is tried as
    zlib-wrapped first, and as raw deflate when that fails before any output, as urllib3
    does. A gzip body can hold more than one member.
    """

    def __init__(self, encoding: str) -> None:
        self.encoding = encoding
        self._inflate = None
        self._replay: bytearray | None = None
        if encoding == "gzip":
            self._inflate = zlib.decompressobj(_GZIP_WBITS)
        elif encoding == "deflate":
            self._inflate = zlib.decompressobj(zlib.MAX_WBITS)
            self._replay = bytearray()

    @property
    def complete(self) -> bool:
        return self._inflate is None or self._inflate.eof

    def feed(self, piece: bytes) -> Iterator[bytes]:
        if self._inflate is None:
            if piece:
                yield piece
            return
        if self._replay is not None:
            self._replay += piece
        try:
            yield from self._inflate_all(piece)
        except zlib.error:
            if self._replay is None:
                raise
            replay, self._replay = bytes(self._replay), None
            self._inflate = zlib.decompressobj(_RAW_DEFLATE_WBITS)
            yield from self._inflate_all(replay)

    def _inflate_all(self, data: bytes) -> Iterator[bytes]:
        while True:
            if self._inflate.eof and data:
                if self.encoding != "gzip":
                    raise zlib.error("data after the end of the deflate stream")
                self._inflate = zlib.decompressobj(_GZIP_WBITS)
            block = self._inflate.decompress(data, PIECE_BYTES)
            if block:
                self._replay = None
                yield block
            if self._inflate.eof:
                data = self._inflate.unused_data
                if not data:
                    return
            elif len(block) == PIECE_BYTES:
                # The block is full, so input or output may still wait.
                data = self._inflate.unconsumed_tail
            else:
                return


class SecClient:
    def __init__(
        self,
        user_agent: str,
        ledger: Path,
        *,
        session=None,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        utcnow: Callable[[], datetime] = lambda: datetime.now(UTC),
        rng: random.Random | None = None,
    ) -> None:
        if not user_agent.strip():
            raise ValueError("user_agent is empty")
        self._headers = {"User-Agent": user_agent, "Accept-Encoding": ACCEPT_ENCODING}
        self._ledger = ledger
        self._session = session if session is not None else requests.Session()
        self._monotonic = monotonic
        self._sleep = sleep
        self._utcnow = utcnow
        self._rng = rng if rng is not None else random.Random()
        self._last_start: float | None = None

    def fetch(self, url: str, dest: Path, *, key: str) -> FetchResult:
        """Fetch `url` into `dest`, with up to `MAX_ATTEMPTS` attempts.

        Raises `BudgetExhausted` or `AccessDenied` to stop the run. Any other exception
        is recorded in the ledger and then propagates.
        """
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")
        delay = 0.0
        attempt = 0
        while True:
            attempt += 1
            usage = self._usage_with_room()
            self._wait(delay)
            answer = self._attempt(url, dest, part, key, attempt, usage)
            if answer.record["outcome"] != "retry":
                return _result(url, attempt, answer)
            delay = self._retry_delay(attempt, answer.retry_after)

    def _usage_with_room(self) -> Usage:
        usage = ledger_usage(self._ledger)
        if usage.requests >= MAX_REQUESTS:
            raise BudgetExhausted(f"{usage.requests} requests sent, the limit is {MAX_REQUESTS}")
        if MAX_WIRE_BYTES - usage.wire_bytes < BUDGET_MARGIN:
            raise BudgetExhausted(
                f"{usage.wire_bytes} wire bytes received, the limit is {MAX_WIRE_BYTES}"
            )
        return usage

    def _wait(self, delay: float) -> None:
        """Sleep for the retry delay or the request spacing, whichever is longer."""
        if self._last_start is not None:
            delay = max(delay, self._last_start + REQUEST_SPACING - self._monotonic())
        if delay > 0:
            self._sleep(delay)

    def _retry_delay(self, attempt: int, retry_after: float | None) -> float:
        backoff = min(BACKOFF_CAP, 2 * 2 ** (attempt - 1)) + self._rng.uniform(0, 1)
        return max(backoff, retry_after or 0.0)

    def _attempt(
        self, url: str, dest: Path, part: Path, key: str, attempt: int, usage: Usage
    ) -> _Answer:
        request_id = uuid.uuid4().hex
        append(
            self._ledger,
            {
                "event": "request",
                "id": request_id,
                "key": key,
                "url": url,
                "attempt": attempt,
                "at": _stamp(self._utcnow()),
            },
        )
        received = _Received()
        try:
            try:
                self._last_start = self._monotonic()
                received.response = self._session.get(
                    url,
                    headers=self._headers,
                    stream=True,
                    timeout=TIMEOUTS,
                    allow_redirects=False,
                )
                verdict = self._read_response(received, part, usage)
            except TRANSIENT_ERRORS as error:
                verdict = _Verdict("retry", _describe(error))
            except BaseException as error:
                self._record(request_id, key, received, _Verdict("failed", _describe(error)))
                raise
            if verdict.outcome == "retry" and attempt == MAX_ATTEMPTS:
                verdict = dataclasses.replace(verdict, outcome="failed")
            answer = self._record(request_id, key, received, verdict)
            if verdict.outcome == "ok":
                part.replace(dest)
            elif verdict.outcome == "budget":
                raise BudgetExhausted(verdict.reason)
            elif verdict.outcome == "forbidden":
                raise AccessDenied(f"{url}: {verdict.reason}")
            return answer
        finally:
            if received.response is not None:
                received.response.close()
            part.unlink(missing_ok=True)

    def _read_response(self, received: _Received, part: Path, usage: Usage) -> _Verdict:
        status = received.response.status_code
        if status == 200:
            return self._read_body(received, part, usage)
        if status == 404:
            return _Verdict("not_found", "HTTP 404")
        if status == 403:
            return _Verdict("forbidden", "HTTP 403")
        if status in RETRY_STATUSES:
            retry_after = _retry_after(received.response.headers)
            return _Verdict("retry", f"HTTP {status}", retry_after=retry_after)
        return _Verdict("failed", f"HTTP {status}")

    def _read_body(self, received: _Received, part: Path, usage: Usage) -> _Verdict:
        headers = received.response.headers
        length = _content_length(headers)
        if length is not None and length > MAX_RESPONSE_BYTES:
            return _Verdict("too_large", f"Content-Length {length} is above {MAX_RESPONSE_BYTES}")
        encoding = _content_encoding(headers)
        if encoding not in ("gzip", "deflate", "identity"):
            return _Verdict("failed", f"unexpected Content-Encoding {encoding!r}")
        received.body_bytes = 0
        with part.open("wb") as out:
            return self._copy_body(received, _Decoder(encoding), out, usage)

    def _copy_body(
        self, received: _Received, decoder: _Decoder, out: BinaryIO, usage: Usage
    ) -> _Verdict:
        """Stream raw pieces, count them as wire bytes, and write the decoded bytes."""
        digest = hashlib.sha256()
        pieces = received.response.raw.stream(PIECE_BYTES, decode_content=False)
        while True:
            if MAX_WIRE_BYTES - (usage.wire_bytes + received.wire_bytes) < BUDGET_MARGIN:
                return _Verdict("budget", f"fewer than {BUDGET_MARGIN} wire bytes of budget remain")
            piece = _next_piece(pieces)
            if piece is None:
                break
            received.wire_bytes += len(piece)
            for block in decoder.feed(piece):
                received.body_bytes += len(block)
                if received.body_bytes > MAX_RESPONSE_BYTES:
                    return _Verdict("too_large", f"decoded body passed {MAX_RESPONSE_BYTES} bytes")
                digest.update(block)
                out.write(block)
        if not decoder.complete:
            return _Verdict("retry", f"{decoder.encoding} body ends before its stream ends")
        return _Verdict("ok", sha256=digest.hexdigest())

    def _record(
        self, request_id: str, key: str, received: _Received, verdict: _Verdict
    ) -> _Answer:
        response = received.response
        headers = response.headers if response is not None else {}
        at = self._utcnow()
        record = {
            "event": "response",
            "id": request_id,
            "key": key,
            "status": response.status_code if response is not None else None,
            "wire_bytes": received.wire_bytes,
            "body_bytes": received.body_bytes,
            "sha256": verdict.sha256,
            "outcome": verdict.outcome,
            "reason": verdict.reason,
            "content_encoding": headers.get("Content-Encoding"),
            "etag": headers.get("ETag"),
            "last_modified": headers.get("Last-Modified"),
            "at": _stamp(at),
        }
        append(self._ledger, record)
        return _Answer(record, at, verdict.retry_after)


def _next_piece(pieces: Iterator[bytes]) -> bytes | None:
    """Read one raw piece. Map urllib3 read errors as `Response.iter_content` does."""
    try:
        return next(pieces, None)
    except _URLLIB3_ERRORS.ProtocolError as error:
        raise requests.exceptions.ChunkedEncodingError(error) from error
    except _URLLIB3_ERRORS.ReadTimeoutError as error:
        raise requests.exceptions.ConnectionError(error) from error
    except _URLLIB3_ERRORS.SSLError as error:
        raise requests.exceptions.SSLError(error) from error


def _result(url: str, attempts: int, answer: _Answer) -> FetchResult:
    record = answer.record
    return FetchResult(
        key=record["key"],
        url=url,
        outcome=record["outcome"],
        status=record["status"],
        attempts=attempts,
        wire_bytes=record["wire_bytes"],
        body_bytes=record["body_bytes"] or 0,
        sha256=record["sha256"],
        fetched_at=answer.at if record["outcome"] == "ok" else None,
        reason=record["reason"],
    )


def _content_length(headers: Mapping[str, str]) -> int | None:
    value = (headers.get("Content-Length") or "").strip()
    return int(value) if value.isdecimal() else None


def _content_encoding(headers: Mapping[str, str]) -> str:
    return (headers.get("Content-Encoding") or "").strip().lower() or "identity"


def _retry_after(headers: Mapping[str, str]) -> float | None:
    """The numeric `Retry-After` seconds. Another form (an HTTP date) is ignored."""
    try:
        seconds = float(headers.get("Retry-After"))
    except (TypeError, ValueError):
        return None
    return seconds if math.isfinite(seconds) and seconds >= 0 else None


def _describe(error: BaseException) -> str:
    message = str(error)
    return f"{type(error).__name__}: {message}" if message else type(error).__name__


def _stamp(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
