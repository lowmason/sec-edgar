import unittest
from datetime import UTC, datetime, timedelta

from sec_filing_data.times import accepted_at, last_modified_at, public_time, readable_date


def utc(*parts: int) -> datetime:
    return datetime(*parts, tzinfo=UTC)


def pt(accepted: datetime | None, filed: str | None) -> tuple[datetime | None, str]:
    return public_time(accepted, filed, private_to_public=False)


class TimeRuleTest(unittest.TestCase):
    def test_same_day_acceptance(self):
        accepted = accepted_at("20260814160523")

        self.assertEqual(accepted, utc(2026, 8, 14, 20, 5, 23))
        self.assertEqual(pt(accepted, "20260814"), (utc(2026, 8, 14, 20, 5, 23), "acceptance"))

    def test_date_moved_to_the_next_weekday(self):
        self.assertEqual(
            pt(accepted_at("20260813173512"), "20260814"), (utc(2026, 8, 14, 10, 0), "next_opening")
        )

    def test_date_moved_past_a_weekend(self):
        self.assertEqual(
            pt(accepted_at("20260814190000"), "20260817"), (utc(2026, 8, 17, 10, 0), "next_opening")
        )

    def test_effect_case(self):
        self.assertEqual(
            pt(accepted_at("20260918001500"), "20260917"), (utc(2026, 9, 18, 10, 0), "next_opening")
        )

    def test_at_or_after_2200(self):
        self.assertEqual(
            pt(accepted_at("20260814220000"), "20260814"), (utc(2026, 8, 15, 10, 0), "next_opening")
        )
        self.assertEqual(
            pt(accepted_at("20260814215959"), "20260814"),
            (utc(2026, 8, 15, 1, 59, 59), "acceptance"),
        )

    def test_private_to_public(self):
        self.assertEqual(
            public_time(utc(2026, 8, 14, 20, 5, 23), "20260814", private_to_public=True),
            (None, "private_to_public"),
        )
        self.assertEqual(
            public_time(None, "20260814", private_to_public=True), (None, "private_to_public")
        )

    def test_no_acceptance(self):
        self.assertEqual(pt(None, "20260814"), (None, "no_acceptance"))

    def test_summer_and_winter_offsets(self):
        self.assertEqual(accepted_at("20260814160523"), utc(2026, 8, 14, 20, 5, 23))
        self.assertEqual(accepted_at("20261215160523"), utc(2026, 12, 15, 21, 5, 23))

    def test_last_modified_parse(self):
        self.assertEqual(
            last_modified_at("Fri, 18 Sep 2026 10:03:06 GMT"), utc(2026, 9, 18, 10, 3, 6)
        )
        self.assertIsNone(last_modified_at(None))
        self.assertIsNone(last_modified_at("not a date"))

    def test_unreadable_acceptance_and_filing_date(self):
        for text in ("2026081416052", "20261332160523", "2026-08-14 16:05", ""):
            with self.subTest(text=text):
                self.assertIsNone(accepted_at(text))
        accepted = utc(2026, 8, 15, 3, 10)
        for filed in (None, "2026-08-14"):
            with self.subTest(filed=filed):
                self.assertEqual(pt(accepted, filed), (utc(2026, 8, 15, 10, 0), "next_opening"))

    def test_readable_date(self):
        self.assertTrue(readable_date("20260814"))
        for text in ("2026-08-14", "2026081", "", None, "20261332", "２０２６０８１４"):
            with self.subTest(text=text):
                self.assertFalse(readable_date(text))

    def test_public_time_is_never_before_acceptance(self):
        for hour in range(24):
            accepted = accepted_at(f"202608{14}{hour:02d}0000")
            for filed in ("20260813", "20260814", "20260817"):
                with self.subTest(hour=hour, filed=filed):
                    public_at, _ = pt(accepted, filed)
                    self.assertGreaterEqual(public_at, accepted)

    def test_non_ascii_digits_are_unreadable(self):
        self.assertIsNone(accepted_at("２０２６０８１４１６０５２３"))

    def test_daylight_saving_change_day(self):
        # 2026-11-01: clocks go back, so 22:00 EST is 03:00 UTC the next day.
        self.assertEqual(
            pt(accepted_at("20261101220000"), "20261101"), (utc(2026, 11, 2, 11, 0), "next_opening")
        )

    def test_result_is_utc(self):
        public_at, _ = pt(accepted_at("20260814160523"), "20260814")

        self.assertEqual(public_at.utcoffset(), timedelta(0))
