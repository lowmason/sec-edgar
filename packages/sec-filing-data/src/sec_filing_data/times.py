"""The time rule of a filing: when it was accepted, when it could first be public, and
when its stored copy was last modified.

Every time here is UTC and comes from text or arguments, never from the clock. This
module does not import `requests`.
"""

from datetime import UTC, date, datetime, time, timedelta
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

NEW_YORK = ZoneInfo("America/New_York")
PUBLIC_RULES = ("acceptance", "next_opening", "private_to_public", "no_acceptance")

OPENING = time(6, 0)
CLOSING = time(22, 0)


def accepted_at(acceptance_datetime: str | None) -> datetime | None:
    """Read `YYYYMMDDHHMMSS` as New York time and return it in UTC; None if unreadable."""
    if acceptance_datetime is None or not _is_digits(acceptance_datetime, 14):
        return None
    year, month, day, hour, minute, second = (
        int(acceptance_datetime[start:end]) for start, end in _ACCEPTANCE_FIELDS
    )
    try:
        local = datetime(year, month, day, hour, minute, second, tzinfo=NEW_YORK)
    except ValueError:
        return None
    return local.astimezone(UTC)


def public_time(
    accepted: datetime | None, filed_as_of_date: str | None, *, private_to_public: bool
) -> tuple[datetime | None, str]:
    """The earliest time a filing could have been public, and the rule that gave it.

    `private_to_public` wins over a missing acceptance. An unreadable `filed_as_of_date`
    leaves `accepted` alone at the later-of step.
    """
    if private_to_public:
        return None, "private_to_public"
    if accepted is None:
        return None, "no_acceptance"
    result = accepted
    filed_opening = _opening_on(filed_as_of_date)
    if filed_opening is not None:
        result = max(result, filed_opening)
    local = result.astimezone(NEW_YORK)
    if local.time() < OPENING:
        result = _at_opening(local.date())
    elif local.time() >= CLOSING:
        result = _at_opening(local.date() + timedelta(days=1))
    rule = "acceptance" if result == accepted else "next_opening"
    return result, rule


def readable_date(text: str | None) -> bool:
    """True when `text` is a real calendar date written as `YYYYMMDD`."""
    return _day_of(text) is not None


def last_modified_at(header: str | None) -> datetime | None:
    """An HTTP date such as `Fri, 18 Sep 2026 10:03:06 GMT`, in UTC; None if unreadable."""
    if header is None:
        return None
    try:
        parsed = parsedate_to_datetime(header)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


_ACCEPTANCE_FIELDS = ((0, 4), (4, 6), (6, 8), (8, 10), (10, 12), (12, 14))


def _is_digits(text: str, length: int) -> bool:
    return len(text) == length and text.isascii() and text.isdigit()


def _at_opening(day: date) -> datetime:
    return datetime.combine(day, OPENING, tzinfo=NEW_YORK).astimezone(UTC)


def _opening_on(yyyymmdd: str | None) -> datetime | None:
    """06:00 New York time on a `YYYYMMDD` date, in UTC; None if unreadable."""
    day = _day_of(yyyymmdd)
    return None if day is None else _at_opening(day)


def _day_of(yyyymmdd: str | None) -> date | None:
    if yyyymmdd is None or not _is_digits(yyyymmdd, 8):
        return None
    try:
        return date(int(yyyymmdd[:4]), int(yyyymmdd[4:6]), int(yyyymmdd[6:]))
    except ValueError:
        return None
