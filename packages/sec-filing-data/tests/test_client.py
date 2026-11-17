import gzip
import hashlib
import http.client
import io
import json
import random
import tempfile
import unittest
import zlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

from sec_filing_data import client
from sec_filing_data.client import (
    AccessDenied,
    BudgetExhausted,
    SecClient,
    exclusive_lock,
)
from sec_filing_data.ledger import (
    MAX_REQUESTS,
    MAX_RESPONSE_BYTES,
    MAX_WIRE_BYTES,
    Usage,
    ledger_usage,
    read_ledger,
)

# Only client.py imports requests. The tests reach its classes through the client module.
requests_errors = client.requests.exceptions
urllib3 = client.requests.packages.urllib3

USER_AGENT = "sec-filing-data-tests test@example.invalid"
KEY = "0000000001-26-000001"
URL = f"https://www.sec.gov/Archives/edgar/data/1000/{KEY}.txt"
MIB = 1 << 20
FIRST_TIME = datetime(2026, 11, 17, 18, 4, 5, 123456, tzinfo=UTC)


class FakeRaw:
    """The raw body: scripted pieces as they come off the wire, then an optional error."""

    def __init__(self, pieces: list[bytes], error: BaseException | None) -> None:
        self.pieces = pieces
        self.error = error
        self.stream_calls: list[tuple] = []

    def stream(self, amt, decode_content=None):
        self.stream_calls.append((amt, decode_content))
        yield from self.pieces
        if self.error is not None:
            raise self.error


class FakeResponse:
    def __init__(self, status_code=200, pieces=(), headers=None, error=None) -> None:
        self.status_code = status_code
        self.headers = client.requests.structures.CaseInsensitiveDict(headers or {})
        self.raw = FakeRaw(list(pieces), error)
        self.closed = False

    def close(self) -> None:
        self.closed = True


def ok_response(body=b"filing text\n", headers=None) -> FakeResponse:
    return FakeResponse(200, [body], headers)


def status_response(status_code: int, headers=None) -> FakeResponse:
    return FakeResponse(status_code, [b"error page"], headers)


class FakeSession:
    """Returns (or raises) one scripted reply per call to `get`."""

    def __init__(self, *replies) -> None:
        self.replies = list(replies)
        self.calls: list[dict] = []

    def get(self, url, *, headers, stream, timeout, allow_redirects):
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "stream": stream,
                "timeout": timeout,
                "allow_redirects": allow_redirects,
            }
        )
        reply = self.replies.pop(0)
        if isinstance(reply, BaseException):
            raise reply
        return reply


class FakeClock:
    """A monotonic clock that only moves when the client sleeps."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class FakeUtcNow:
    """One second later at each call, so each record has its own time."""

    def __init__(self) -> None:
        self.times: list[datetime] = []

    def __call__(self) -> datetime:
        moment = FIRST_TIME + timedelta(seconds=len(self.times))
        self.times.append(moment)
        return moment


def matched_pair(number: int, wire_bytes: int) -> list[dict]:
    request_id = f"earlier-{number}"
    return [
        {
            "event": "request",
            "id": request_id,
            "key": f"earlier-{number}",
            "url": URL,
            "attempt": 1,
            "at": "2026-11-16T10:00:00.000000Z",
        },
        {
            "event": "response",
            "id": request_id,
            "key": f"earlier-{number}",
            "status": 200,
            "wire_bytes": wire_bytes,
            "body_bytes": wire_bytes,
            "sha256": "0" * 64,
            "outcome": "ok",
            "reason": None,
            "content_encoding": None,
            "etag": None,
            "last_modified": None,
            "at": "2026-11-16T10:00:01.000000Z",
        },
    ]


def fill_ledger(path: Path, wire_bytes: list[int]) -> None:
    """Write one matched request and response pair per entry of `wire_bytes`."""
    with path.open("w", encoding="utf-8") as ledger:
        for number, size in enumerate(wire_bytes):
            for record in matched_pair(number, size):
                ledger.write(json.dumps(record) + "\n")


def split(data: bytes, size: int) -> list[bytes]:
    return [data[start : start + size] for start in range(0, len(data), size)]


class ClientTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Start again in a new empty folder, for a second case inside one test."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.ledger = self.root / "fetch-log.jsonl"
        self.dest = self.root / "bytes" / f"{KEY}.txt"
        self.part = self.dest.with_name(self.dest.name + ".part")
        self.clock = FakeClock()
        self.utcnow = FakeUtcNow()

    def make_client(self, session: FakeSession) -> SecClient:
        return SecClient(
            USER_AGENT,
            self.ledger,
            session=session,
            monotonic=self.clock.monotonic,
            sleep=self.clock.sleep,
            utcnow=self.utcnow,
            rng=random.Random(7),
        )

    def fetch(self, *replies):
        session = FakeSession(*replies)
        result = self.make_client(session).fetch(URL, self.dest, key=KEY)
        return result, session

    def records(self, event: str) -> list[dict]:
        return [record for record in read_ledger(self.ledger) if record["event"] == event]

    def assert_no_files(self) -> None:
        self.assertFalse(self.dest.exists())
        self.assertFalse(self.part.exists())


class PlanTests(ClientTestCase):
    def test_ok_writes_bytes_hash_and_ledger(self):
        body = b"<SEC-DOCUMENT>one filing\n" * 100
        result, _ = self.fetch(
            FakeResponse(
                200, [gzip.compress(body)], {"Content-Encoding": "gzip", "ETag": '"e1"'}
            )
        )

        self.assertEqual(self.dest.read_bytes(), body)
        self.assertEqual(result.outcome, "ok")
        self.assertEqual(result.sha256, hashlib.sha256(body).hexdigest())
        requests_sent = self.records("request")
        responses = self.records("response")
        self.assertEqual(len(requests_sent), 1)
        self.assertEqual(len(responses), 1)
        response = responses[0]
        self.assertEqual(response["content_encoding"], "gzip")
        self.assertEqual(response["etag"], '"e1"')
        self.assertIsNone(response["last_modified"])

    def test_sends_declared_user_agent(self):
        _, session = self.fetch(ok_response())

        self.assertEqual(len(session.calls), 1)
        self.assertEqual(session.calls[0]["headers"]["User-Agent"], USER_AGENT)

    def test_spacing_between_requests(self):
        session = FakeSession(ok_response(), ok_response())
        sec = self.make_client(session)

        sec.fetch(URL, self.dest, key=KEY)
        sec.fetch(URL, self.root / "bytes" / "second.txt", key="second")

        self.assertEqual(self.clock.sleeps, [0.34])

    def test_retries_then_succeeds(self):
        result, _ = self.fetch(status_response(503), ok_response())

        self.assertEqual(result.outcome, "ok")
        self.assertEqual(result.attempts, 2)
        self.assertGreaterEqual(max(self.clock.sleeps), 2)

        self.reset()
        result, _ = self.fetch(
            status_response(503, {"Retry-After": "30"}), ok_response()
        )

        self.assertEqual(result.attempts, 2)
        self.assertGreaterEqual(max(self.clock.sleeps), 30)

    def test_gives_up_after_five_attempts(self):
        result, _ = self.fetch(*(status_response(503) for _ in range(5)))

        self.assertEqual(result.outcome, "failed")
        self.assertEqual(len(self.records("request")), 5)

    def test_connection_error_is_recorded_and_retried(self):
        result, _ = self.fetch(
            requests_errors.ConnectionError("connection reset"), ok_response()
        )

        self.assertEqual(result.outcome, "ok")
        first_request = self.records("request")[0]
        first_response = next(
            record
            for record in self.records("response")
            if record["id"] == first_request["id"]
        )
        self.assertEqual(first_response["outcome"], "retry")

    def test_not_found_is_not_retried(self):
        result, session = self.fetch(status_response(404), ok_response())

        self.assertEqual(result.outcome, "not_found")
        self.assertEqual(result.attempts, 1)
        self.assertEqual(len(session.calls), 1)
        self.assert_no_files()

    def test_forbidden_halts(self):
        session = FakeSession(status_response(403), ok_response())

        with self.assertRaises(AccessDenied):
            self.make_client(session).fetch(URL, self.dest, key=KEY)

        self.assertEqual(len(session.calls), 1)
        self.assertEqual(
            [record["outcome"] for record in self.records("response")], ["forbidden"]
        )

    def test_too_large_by_header_and_by_stream(self):
        result, _ = self.fetch(
            FakeResponse(
                200, [b"x"], {"Content-Length": str(MAX_RESPONSE_BYTES + 1)}
            )
        )
        self.assertEqual(result.outcome, "too_large")
        self.assert_no_files()

        piece = bytes(MIB)
        result, _ = self.fetch(
            FakeResponse(200, [piece] * (MAX_RESPONSE_BYTES // MIB + 1))
        )
        self.assertEqual(result.outcome, "too_large")
        self.assert_no_files()

    def test_budget_refuses_before_sending(self):
        for wire_bytes in ([0] * MAX_REQUESTS, [MAX_WIRE_BYTES]):
            with self.subTest(pairs=len(wire_bytes), wire_bytes=sum(wire_bytes)):
                fill_ledger(self.ledger, wire_bytes)
                session = FakeSession(ok_response())

                with self.assertRaises(BudgetExhausted):
                    self.make_client(session).fetch(URL, self.dest, key=KEY)

                self.assertEqual(session.calls, [])
                self.assertEqual(len(self.records("request")), len(wire_bytes))

    def test_budget_stops_inside_stream(self):
        fill_ledger(self.ledger, [MAX_WIRE_BYTES - 3 * MIB])
        session = FakeSession(FakeResponse(200, [bytes(MIB)] * 10))

        with self.assertRaises(BudgetExhausted):
            self.make_client(session).fetch(URL, self.dest, key=KEY)

        self.assertLessEqual(ledger_usage(self.ledger).wire_bytes, MAX_WIRE_BYTES)
        self.assertEqual(self.records("response")[-1]["outcome"], "budget")
        self.assert_no_files()

    def test_unmatched_request_counts_full_response(self):
        self.ledger.write_text(json.dumps(matched_pair(0, 10)[0]) + "\n")

        self.assertEqual(ledger_usage(self.ledger), Usage(1, 268_435_456))

    def test_second_lock_fails(self):
        lock = self.root / "fetch.lock"

        with exclusive_lock(lock):
            with self.assertRaises(RuntimeError) as raised:
                with exclusive_lock(lock):
                    pass

        self.assertEqual(str(raised.exception), f"another fetch holds {lock}")


class RequestTests(ClientTestCase):
    def test_empty_user_agent_is_refused(self):
        for user_agent in ("", "   "):
            with self.subTest(user_agent=user_agent):
                with self.assertRaises(ValueError):
                    SecClient(user_agent, self.ledger, session=FakeSession())

    def test_request_options(self):
        response = ok_response()
        _, session = self.fetch(response)

        call = session.calls[0]
        self.assertEqual(call["url"], URL)
        self.assertEqual(call["headers"]["Accept-Encoding"], "gzip, deflate")
        self.assertIs(call["stream"], True)
        self.assertEqual(call["timeout"], (15, 60))
        self.assertIs(call["allow_redirects"], False)
        self.assertEqual(response.raw.stream_calls, [(MIB, False)])
        self.assertTrue(response.closed)

    def test_first_request_does_not_wait(self):
        self.fetch(ok_response())

        self.assertEqual(self.clock.sleeps, [])

    def test_spacing_counts_time_already_passed(self):
        session = FakeSession(ok_response(), ok_response())
        sec = self.make_client(session)

        sec.fetch(URL, self.dest, key=KEY)
        self.clock.now += 0.30
        sec.fetch(URL, self.root / "bytes" / "second.txt", key="second")

        self.assertEqual(len(self.clock.sleeps), 1)
        self.assertAlmostEqual(self.clock.sleeps[0], 0.04)

    def test_redirect_and_other_statuses_fail_at_once(self):
        for status in (301, 400):
            with self.subTest(status=status):
                self.reset()
                result, session = self.fetch(status_response(status), ok_response())

                self.assertEqual(result.outcome, "failed")
                self.assertEqual(result.status, status)
                self.assertEqual(result.attempts, 1)
                self.assertEqual(result.reason, f"HTTP {status}")
                self.assertEqual(len(session.calls), 1)
                self.assert_no_files()

    def test_every_response_is_closed(self):
        replies = [status_response(503), status_response(404)]
        self.fetch(*replies)

        self.assertTrue(all(reply.closed for reply in replies))


class LedgerRecordTests(ClientTestCase):
    def test_records_share_an_id_and_hold_every_field(self):
        body = b"plain text body\n"
        self.fetch(ok_response(body, {"Last-Modified": "Tue, 01 Jul 2026 10:00:00 GMT"}))

        [request] = self.records("request")
        [response] = self.records("response")
        self.assertEqual(
            set(request), {"event", "id", "key", "url", "attempt", "at"}
        )
        self.assertEqual(
            set(response),
            {
                "event",
                "id",
                "key",
                "status",
                "wire_bytes",
                "body_bytes",
                "sha256",
                "outcome",
                "reason",
                "content_encoding",
                "etag",
                "last_modified",
                "at",
            },
        )
        self.assertEqual(request["id"], response["id"])
        self.assertEqual(request["key"], KEY)
        self.assertEqual(request["url"], URL)
        self.assertEqual(request["attempt"], 1)
        self.assertEqual(request["at"], "2026-11-17T18:04:05.123456Z")
        self.assertEqual(response["status"], 200)
        self.assertEqual(response["wire_bytes"], len(body))
        self.assertEqual(response["body_bytes"], len(body))
        self.assertIsNone(response["reason"])
        self.assertIsNone(response["content_encoding"])
        self.assertIsNone(response["etag"])
        self.assertEqual(response["last_modified"], "Tue, 01 Jul 2026 10:00:00 GMT")
        self.assertEqual(response["at"], "2026-11-17T18:04:06.123456Z")

    def test_ok_result_carries_the_record_time(self):
        body = b"plain text body\n"
        result, _ = self.fetch(ok_response(body))

        self.assertEqual(result.key, KEY)
        self.assertEqual(result.url, URL)
        self.assertEqual(result.status, 200)
        self.assertEqual(result.attempts, 1)
        self.assertEqual(result.wire_bytes, len(body))
        self.assertEqual(result.body_bytes, len(body))
        self.assertIsNone(result.reason)
        self.assertEqual(result.fetched_at, FIRST_TIME + timedelta(seconds=1))
        self.assertEqual(result.fetched_at.tzinfo, UTC)

    def test_results_other_than_ok_have_no_fetch_time(self):
        result, _ = self.fetch(status_response(404))

        self.assertIsNone(result.fetched_at)
        self.assertIsNone(result.sha256)
        self.assertEqual(result.body_bytes, 0)
        self.assertEqual(result.reason, "HTTP 404")

    def test_attempts_are_numbered(self):
        self.fetch(status_response(503), status_response(502), ok_response())

        self.assertEqual(
            [record["attempt"] for record in self.records("request")], [1, 2, 3]
        )
        self.assertEqual(
            [record["outcome"] for record in self.records("response")],
            ["retry", "retry", "ok"],
        )


class RetryTests(ClientTestCase):
    def test_backoff_doubles_between_attempts(self):
        self.fetch(*(status_response(500) for _ in range(5)))

        self.assertEqual(len(self.clock.sleeps), 4)
        for sleep, base in zip(self.clock.sleeps, (2, 4, 8, 16)):
            self.assertGreaterEqual(sleep, base)
            self.assertLess(sleep, base + 1)

    def test_last_attempt_is_recorded_failed(self):
        result, _ = self.fetch(*(status_response(429) for _ in range(5)))

        self.assertEqual(
            [record["outcome"] for record in self.records("response")],
            ["retry"] * 4 + ["failed"],
        )
        self.assertEqual(result.attempts, 5)
        self.assertEqual(result.status, 429)

    def test_retry_wait_and_spacing_do_not_add_up(self):
        self.fetch(status_response(503), ok_response())

        self.assertEqual(self.clock.sleeps, [2 + random.Random(7).uniform(0, 1)])

    def test_short_retry_after_does_not_shorten_backoff(self):
        self.fetch(status_response(503, {"Retry-After": "1"}), ok_response())

        self.assertGreaterEqual(self.clock.sleeps[0], 2)

    def test_non_numeric_retry_after_is_ignored(self):
        for value in ("Wed, 18 Nov 2026 10:00:00 GMT", "nan", "inf", "-5"):
            with self.subTest(value=value):
                self.reset()
                self.fetch(status_response(503, {"Retry-After": value}), ok_response())

                self.assertGreaterEqual(self.clock.sleeps[0], 2)
                self.assertLess(self.clock.sleeps[0], 3)

    def test_timeout_is_retried(self):
        result, _ = self.fetch(requests_errors.ReadTimeout("read timed out"), ok_response())

        self.assertEqual(result.attempts, 2)

    def test_mid_body_chunked_encoding_error_is_retried(self):
        broken = FakeResponse(
            200, [b"first part"], error=requests_errors.ChunkedEncodingError("cut")
        )
        result, _ = self.fetch(broken, ok_response())

        self.assertEqual(result.outcome, "ok")
        first = self.records("response")[0]
        self.assertEqual(first["outcome"], "retry")
        self.assertEqual(first["wire_bytes"], len(b"first part"))
        self.assertTrue(broken.closed)

    def test_raw_read_errors_mid_body_are_retried(self):
        errors = [
            urllib3.exceptions.ProtocolError(
                "Connection broken", urllib3.exceptions.IncompleteRead(10, 90)
            ),
            urllib3.exceptions.ReadTimeoutError(None, URL, "Read timed out."),
            urllib3.exceptions.SSLError("bad record mac"),
        ]
        for error in errors:
            with self.subTest(error=type(error).__name__):
                self.reset()
                session = FakeSession(
                    FakeResponse(200, [b"first part"], error=error), ok_response()
                )
                result = self.make_client(session).fetch(URL, self.dest, key=KEY)

                self.assertEqual(result.outcome, "ok")
                self.assertEqual(result.attempts, 2)
                first = self.records("response")[0]
                self.assertEqual(first["outcome"], "retry")
                self.assertEqual(first["wire_bytes"], len(b"first part"))
                self.assertFalse(self.part.exists())

    def test_raw_read_error_on_every_attempt_fails(self):
        result, _ = self.fetch(
            *(
                FakeResponse(
                    200,
                    [b"part"],
                    error=urllib3.exceptions.ProtocolError("Connection broken"),
                )
                for _ in range(5)
            )
        )

        self.assertEqual(result.outcome, "failed")
        self.assertEqual(result.attempts, 5)
        self.assertIn("ChunkedEncodingError", result.reason)
        self.assert_no_files()

    def test_interrupt_is_recorded_and_propagates(self):
        session = FakeSession(
            FakeResponse(200, [b"first part"], error=KeyboardInterrupt())
        )

        with self.assertRaises(KeyboardInterrupt):
            self.make_client(session).fetch(URL, self.dest, key=KEY)

        [response] = self.records("response")
        self.assertEqual(response["outcome"], "failed")
        self.assertEqual(response["reason"], "KeyboardInterrupt")
        self.assertEqual(response["wire_bytes"], len(b"first part"))
        self.assertEqual(ledger_usage(self.ledger), Usage(1, len(b"first part")))
        self.assert_no_files()

    def test_unexpected_exception_is_recorded_and_propagates(self):
        session = FakeSession(ValueError("bad url"))

        with self.assertRaises(ValueError):
            self.make_client(session).fetch(URL, self.dest, key=KEY)

        [response] = self.records("response")
        self.assertEqual(response["outcome"], "failed")
        self.assertEqual(response["reason"], "ValueError: bad url")
        self.assertIsNone(response["status"])
        self.assertEqual(response["wire_bytes"], 0)


class BodyTests(ClientTestCase):
    def test_gzip_wire_bytes_are_the_compressed_bytes(self):
        body = b"<SEC-DOCUMENT>text that compresses well\n" * 5000
        wire = gzip.compress(body)
        result, _ = self.fetch(
            FakeResponse(200, split(wire, 1000), {"Content-Encoding": "gzip"})
        )

        self.assertEqual(self.dest.read_bytes(), body)
        [response] = self.records("response")
        self.assertEqual(response["wire_bytes"], len(wire))
        self.assertEqual(response["body_bytes"], len(body))
        self.assertLess(response["wire_bytes"], response["body_bytes"])
        self.assertEqual(result.wire_bytes, len(wire))
        self.assertEqual(ledger_usage(self.ledger), Usage(1, len(wire)))

    def test_deflate_bodies_decode_wrapped_or_raw(self):
        body = b"deflate body\n" * 1000
        raw_deflate = zlib.compressobj(wbits=-zlib.MAX_WBITS)
        wires = {
            "zlib-wrapped": zlib.compress(body),
            "raw": raw_deflate.compress(body) + raw_deflate.flush(),
        }
        for name, wire in wires.items():
            for size in (1, 7, len(wire)):
                with self.subTest(form=name, piece_size=size):
                    self.reset()
                    result, _ = self.fetch(
                        FakeResponse(200, split(wire, size), {"Content-Encoding": "deflate"})
                    )

                    self.assertEqual(result.outcome, "ok")
                    self.assertEqual(self.dest.read_bytes(), body)
                    self.assertEqual(result.wire_bytes, len(wire))

    def test_every_gzip_member_is_decoded(self):
        wire = gzip.compress(b"first member\n") + gzip.compress(b"second member\n")
        result, _ = self.fetch(FakeResponse(200, [wire], {"Content-Encoding": "gzip"}))

        self.assertEqual(result.outcome, "ok")
        self.assertEqual(self.dest.read_bytes(), b"first member\nsecond member\n")

    def test_truncated_gzip_is_retried(self):
        body = b"a filing that will be cut short\n" * 200
        wire = gzip.compress(body)
        result, _ = self.fetch(
            FakeResponse(200, [wire[: len(wire) // 2]], {"Content-Encoding": "gzip"}),
            FakeResponse(200, [wire], {"Content-Encoding": "gzip"}),
        )

        self.assertEqual(result.outcome, "ok")
        self.assertEqual(result.attempts, 2)
        self.assertEqual(self.records("response")[0]["outcome"], "retry")
        self.assertEqual(self.dest.read_bytes(), body)

    def test_unexpected_content_encoding_fails(self):
        result, session = self.fetch(
            FakeResponse(200, [b"\x0b\x02\x80"], {"Content-Encoding": "br"}),
            ok_response(),
        )

        self.assertEqual(result.outcome, "failed")
        self.assertEqual(result.attempts, 1)
        self.assertIn("br", result.reason)
        self.assertEqual(len(session.calls), 1)
        self.assert_no_files()

    def test_corrupt_gzip_is_recorded_and_propagates(self):
        wire = bytearray(gzip.compress(b"corrupt me\n" * 100))
        wire[20:30] = b"\xff" * 10
        session = FakeSession(
            FakeResponse(200, [bytes(wire)], {"Content-Encoding": "gzip"}),
            ok_response(),
        )

        with self.assertRaises(zlib.error):
            self.make_client(session).fetch(URL, self.dest, key=KEY)

        [response] = self.records("response")
        self.assertEqual(response["outcome"], "failed")
        self.assertEqual(response["wire_bytes"], len(wire))
        self.assertEqual(len(session.calls), 1)
        self.assert_no_files()

    def test_body_at_the_limit_is_kept(self):
        with mock.patch.object(client, "MAX_RESPONSE_BYTES", 10):
            result, _ = self.fetch(
                FakeResponse(200, [b"0123456789"], {"Content-Length": "10"})
            )
            self.assertEqual(result.outcome, "ok")

            self.reset()
            result, _ = self.fetch(FakeResponse(200, [b"01234", b"567890"]))
            self.assertEqual(result.outcome, "too_large")
            self.assert_no_files()

    def test_high_ratio_piece_is_checked_before_it_is_all_decoded(self):
        limit = 3 * MIB
        wire = gzip.compress(bytes(16 * MIB))
        with mock.patch.object(client, "MAX_RESPONSE_BYTES", limit):
            result, _ = self.fetch(
                FakeResponse(200, [wire], {"Content-Encoding": "gzip"})
            )

        self.assertEqual(result.outcome, "too_large")
        [response] = self.records("response")
        self.assertLessEqual(response["body_bytes"], limit + MIB)
        self.assertEqual(response["wire_bytes"], len(wire))
        self.assert_no_files()

    def test_stale_part_file_is_replaced(self):
        self.dest.parent.mkdir(parents=True)
        self.part.write_bytes(b"left by an interrupted run")

        self.fetch(ok_response(b"fresh\n"))

        self.assertEqual(self.dest.read_bytes(), b"fresh\n")
        self.assertFalse(self.part.exists())


class RealUrllib3Tests(ClientTestCase):
    """Real urllib3 responses over in-memory bytes: no socket is opened."""

    def response(self, wire_body: bytes, headers: dict) -> object:
        head = "HTTP/1.1 200 OK\r\n" + "".join(
            f"{name}: {value}\r\n" for name, value in headers.items()
        )
        message = head.encode() + b"\r\n" + wire_body

        class Socket:
            def makefile(self, mode, *args, **kwargs):
                return io.BytesIO(message)

        original = http.client.HTTPResponse(Socket(), method="GET")
        original.begin()
        raw = urllib3.response.HTTPResponse(
            body=original,
            headers=dict(original.getheaders()),
            status=original.status,
            preload_content=False,
            decode_content=True,
            original_response=original,
        )
        response = client.requests.Response()
        response.raw = raw
        response.status_code = original.status
        response.headers = client.requests.structures.CaseInsensitiveDict(raw.headers)
        return response

    def test_chunked_gzip_counts_wire_bytes(self):
        body = b"<SEC-DOCUMENT>chunked filing text\n" * 20000
        wire = gzip.compress(body)
        chunked = b"".join(
            b"%x\r\n" % len(piece) + piece + b"\r\n" for piece in split(wire, 4096)
        ) + b"0\r\n\r\n"

        result, _ = self.fetch(
            self.response(
                chunked, {"Content-Encoding": "gzip", "Transfer-Encoding": "chunked"}
            )
        )

        self.assertEqual(result.outcome, "ok")
        self.assertEqual(self.dest.read_bytes(), body)
        self.assertEqual(result.wire_bytes, len(wire))

    def test_short_body_is_retried(self):
        body = b"a body shorter than its Content-Length\n"
        result, _ = self.fetch(
            self.response(body, {"Content-Length": str(len(body) + 100)}),
            ok_response(body),
        )

        self.assertEqual(result.attempts, 2)
        first = self.records("response")[0]
        self.assertEqual(first["outcome"], "retry")
        self.assertIn("ChunkedEncodingError", first["reason"])
        self.assertEqual(first["wire_bytes"], len(body))


class BudgetTests(ClientTestCase):
    def test_budget_is_checked_before_each_retry(self):
        fill_ledger(self.ledger, [0] * (MAX_REQUESTS - 1))
        session = FakeSession(status_response(503), ok_response())

        with self.assertRaises(BudgetExhausted):
            self.make_client(session).fetch(URL, self.dest, key=KEY)

        self.assertEqual(len(session.calls), 1)
        self.assertEqual(ledger_usage(self.ledger).requests, MAX_REQUESTS)

    def test_one_request_below_the_limit_is_sent(self):
        fill_ledger(self.ledger, [0] * (MAX_REQUESTS - 1))

        result, _ = self.fetch(ok_response())

        self.assertEqual(result.outcome, "ok")

    def test_refuses_when_less_than_one_mib_remains(self):
        for used, refused in ((MAX_WIRE_BYTES - MIB, False), (MAX_WIRE_BYTES - MIB + 1, True)):
            with self.subTest(used=used):
                self.reset()
                fill_ledger(self.ledger, [used])
                session = FakeSession(ok_response(b""))
                sec = self.make_client(session)

                if refused:
                    with self.assertRaises(BudgetExhausted):
                        sec.fetch(URL, self.dest, key=KEY)
                    self.assertEqual(session.calls, [])
                else:
                    self.assertEqual(sec.fetch(URL, self.dest, key=KEY).outcome, "ok")

    def test_stream_guard_leaves_a_normal_response_alone(self):
        fill_ledger(self.ledger, [MAX_WIRE_BYTES - 10 * MIB])

        result, _ = self.fetch(FakeResponse(200, [bytes(MIB)] * 3))

        self.assertEqual(result.outcome, "ok")
        self.assertEqual(result.wire_bytes, 3 * MIB)

    def test_unfinished_requests_from_other_runs_count(self):
        records = matched_pair(0, 5) + [matched_pair(1, 0)[0]]
        self.ledger.write_text("".join(json.dumps(record) + "\n" for record in records))

        self.assertEqual(ledger_usage(self.ledger), Usage(2, 5 + MAX_RESPONSE_BYTES))

    def test_missing_ledger_is_unused(self):
        self.assertEqual(ledger_usage(self.ledger), Usage(0, 0))


class LockTests(ClientTestCase):
    def test_lock_is_released_on_exit(self):
        lock = self.root / "fetch.lock"

        with exclusive_lock(lock):
            pass
        with exclusive_lock(lock):
            pass


if __name__ == "__main__":
    unittest.main()
