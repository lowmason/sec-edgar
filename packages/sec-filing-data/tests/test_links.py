"""The `links` table: each held amendment and the original that its bytes declare."""

import hashlib
import unittest
from datetime import UTC, datetime
from operator import itemgetter

from sec_filing_data.links import (
    LINK_RULES,
    HeldFiling,
    amendment_filings,
    link_context,
    link_row,
)
from sec_filing_data.sample import ARCHIVES
from sec_filing_data.tables import (
    FILING_TIME_COLUMNS,
    SCHEMAS,
    TABLE_FORMATS,
    as_table_rows,
    read_stamp,
    read_table,
)

from tests.stage4_root import (
    PARTNER_4,
    PARTNER_13D_A1,
    PARTNER_13D_A2,
    PARTNER_13F_A,
    PARTNER_D,
    SAMPLED_4_A,
    SAMPLED_8K_A,
    SAMPLED_13D,
    SAMPLED_13F,
    SAMPLED_D_A,
    Stage4RootTestCase,
    form13f_cover_xml,
    submission,
)
from tests.test_partners import (
    ACCEPTED,
    FILED,
    Index,
    accession,
    day,
    form4_a,
    form_d_a,
    padded,
    schedule13_a,
)

# The acceptance time of an amendment that a test builds, unless the test gives another.
AMENDMENT_ACCEPTED_AT = datetime(2026, 8, 5, 14, 30, tzinfo=UTC)
# The acceptance time of an original that is accepted before its amendment.
EARLIER = datetime(2026, 7, 1, 13, 0, tzinfo=UTC)


def filings_row(
    accession_number: str,
    form_type: str,
    raw: bytes = b"",
    *,
    outcome: str = "ok",
    accepted_at: datetime | None = AMENDMENT_ACCEPTED_AT,
    period: str | None = None,
) -> dict:
    """A `filings` row with the table's types. A column that is not given is null."""
    return as_table_rows(
        "filings",
        [
            {
                "accession_number": accession_number,
                "form_type": form_type,
                "outcome": outcome,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "source_url": f"{ARCHIVES}edgar/data/{accession_number}.txt",
                "accepted_at": accepted_at,
                "public_at": accepted_at,
                "period_of_report": period,
            }
        ],
    )[0]


def filer_row(accession_number: str, cik: int, role: str = "FILER") -> dict:
    """A `parties` row with the table's types, with a zero-padded CIK."""
    return as_table_rows(
        "parties",
        [{"accession_number": accession_number, "role": role, "name": "FILER", "cik": padded(cik)}],
    )[0]


def form13f_a(period: str, filer: int | None) -> bytes:
    """A 13F-HR/A whose header period is `period` (`YYYYMMDD`) and whose XML period is the same
    day as `MM-DD-YYYY`. With a `filer` of None, the header has no FILER party."""
    xml_period = f"{period[4:6]}-{period[6:]}-{period[:4]}"
    parties = [] if filer is None else [("FILER", "MANAGER LLC", padded(filer))]
    return submission(
        "13F-HR/A",
        accepted=ACCEPTED,
        filed=FILED,
        parties=parties,
        period=period,
        documents=[
            (
                "13F-HR/A",
                "primary_doc.xml",
                form13f_cover_xml(
                    "13F-HR/A",
                    amendment_no="1",
                    amendment_type="RESTATEMENT",
                    period_of_report=xml_period,
                ),
            )
        ],
    )


def outcome(row: dict) -> tuple:
    """(`link_rule`, `original_accession`, `original_held_in`, `link_problem`) of a row."""
    return (
        row["link_rule"],
        row["original_accession"],
        row["original_held_in"],
        row["link_problem"],
    )


class LinkRowTests(unittest.TestCase):
    """`link_row` on bytes from the submission builder, in a context built from rows."""

    def setUp(self) -> None:
        self.index = Index()
        self.filings: dict[str, list[dict]] = {"sample": [], "partner": []}
        self.parties: dict[str, list[dict]] = {"sample": [], "partner": []}

    def hold(self, row: dict, held_in: str = "sample", filer: int | None = None) -> str:
        """Hold the filing of a `filings` row, with a FILER party when `filer` is given."""
        self.filings[held_in].append(row)
        if filer is not None:
            self.parties[held_in].append(filer_row(row["accession_number"], filer))
        return row["accession_number"]

    def link(self, filing: dict, raw: bytes, held_in: str = "sample") -> dict:
        context = link_context(self.index.rows, self.filings, self.parties)
        row = link_row(filing, held_in, raw, context)
        self.assertEqual(set(row), set(SCHEMAS["links"].names))
        return row

    def test_a_named_original_outside_the_index(self):
        original = accession(41, 1)
        amendment = self.index.add(accession(41, 2), "D/A", (41,), day(8, 5))
        raw = form_d_a(original, 41)

        row = self.link(filings_row(amendment, "D/A", raw), raw)

        self.assertEqual(
            outcome(row), ("previous_accession", None, None, "not in the 2026Q3 index")
        )
        self.assertEqual(row["declared_previous_accession"], original)
        self.assertEqual(row["source_document"], "primary_doc.xml")

    def test_rule_2_with_two_index_matches(self):
        first = self.index.add(accession(52, 1), "4", (51, 52), day(8, 3))
        second = self.index.add(accession(52, 2), "4", (51, 52), day(8, 3))
        raw = form4_a("2026-08-03", 51, [52])

        row = self.link(filings_row(accession(52, 3), "4/A", raw), raw)

        self.assertEqual(
            outcome(row),
            ("original_date_issuer_owner", None, None, f"2 index matches: {first}, {second}"),
        )
        self.assertEqual(row["declared_original_date"], "2026-08-03")

    def test_rule_2_with_padded_ciks(self):
        original = self.index.add(accession(52, 1), "4", (51, 52), day(8, 3))
        raw = form4_a("2026-08-03", 51, [52])
        self.assertIn(b"<issuerCik>0000000051</issuerCik>", raw)
        self.assertIn(51, [row["cik"] for row in self.index.rows])
        self.hold(filings_row(original, "4", accepted_at=EARLIER), "partner")

        row = self.link(filings_row(accession(52, 3), "4/A", raw), raw)

        self.assertEqual(outcome(row), ("original_date_issuer_owner", original, "partner", None))
        self.assertEqual(row["source_document"], "form4a.xml")

    def test_a_form_4_a_with_no_original_date_is_none_declared(self):
        self.index.add(accession(52, 1), "4", (51, 52), day(8, 3))
        raw = form4_a(None, 51, [52])

        row = self.link(filings_row(accession(52, 3), "4/A", raw), raw)

        self.assertEqual(outcome(row), ("none_declared", None, None, None))
        self.assertIsNone(row["declared_original_date"])

    def test_an_original_in_the_index_that_is_not_held(self):
        original = self.index.add(accession(41, 1), "D", (41,), day(7, 6))
        raw = form_d_a(original, 41)

        row = self.link(filings_row(accession(41, 2), "D/A", raw), raw)

        self.assertEqual(outcome(row), ("previous_accession", original, None, None))

    def test_filer_period_compares_header_periods(self):
        raw = form13f_a("20211231", 71)
        self.assertIn(b"<periodOfReport>12-31-2021</periodOfReport>", raw)
        amendment = filings_row(accession(71, 9), "13F-HR/A", raw, period="20211231")
        self.hold(amendment, "partner", filer=71)
        # A held 13F-HR of the filer for another period, and one of another filer.
        for filer, period in ((71, "20210930"), (72, "20211231")):
            self.hold(
                filings_row(accession(filer, 1), "13F-HR", accepted_at=EARLIER, period=period),
                filer=filer,
            )

        with self.subTest("no held 13F-HR of the filer for the period"):
            row = self.link(amendment, raw, "partner")

            self.assertEqual(
                outcome(row),
                ("filer_period", None, None, "no held 13F-HR of filer 71 for period 20211231"),
            )
            self.assertEqual(
                (row["declared_period"], row["amendment_number"], row["amendment_type"]),
                ("20211231", "1", "RESTATEMENT"),
            )

        original = self.hold(
            filings_row(accession(71, 2), "13F-HR", accepted_at=EARLIER, period="20211231"),
            filer=71,
        )

        with self.subTest("the held 13F-HR of the filer for the period"):
            row = self.link(amendment, raw, "partner")

            self.assertEqual(outcome(row), ("filer_period", original, "sample", None))

    def test_filer_period_problems(self):
        with self.subTest("no FILER party"):
            raw = form13f_a("20211231", None)

            row = self.link(filings_row(accession(71, 9), "13F-HR/A", raw), raw)

            self.assertEqual(outcome(row), ("filer_period", None, None, "no FILER party"))

        with self.subTest("a FILER CIK that is not a number"):
            raw = form13f_a("20211231", 71).replace(padded(71).encode(), b"CIK71")

            row = self.link(filings_row(accession(71, 9), "13F-HR/A", raw), raw)

            self.assertEqual(
                outcome(row), ("filer_period", None, None, "CIK CIK71 is not a number")
            )

        first = self.hold(
            filings_row(accession(71, 2), "13F-HR", accepted_at=EARLIER, period="20211231"),
            filer=71,
        )
        second = self.hold(
            filings_row(accession(71, 1), "13F-HR", accepted_at=EARLIER, period="20211231"),
            "partner",
            filer=71,
        )

        with self.subTest("two held matches"):
            raw = form13f_a("20211231", 71)

            row = self.link(filings_row(accession(71, 9), "13F-HR/A", raw), raw)

            self.assertEqual(
                outcome(row),
                ("filer_period", None, None, f"2 held 13F-HR matches: {second}, {first}"),
            )

    def test_an_original_accepted_after_its_amendment_is_no_link(self):
        original = self.index.add(accession(41, 1), "D", (41,), day(7, 6))
        raw = form_d_a(original, 41)
        amendment = filings_row(accession(41, 2), "D/A", raw)
        later = datetime(2026, 8, 6, 14, 30, tzinfo=UTC)
        self.hold(filings_row(original, "D", accepted_at=later), "partner")

        row = self.link(amendment, raw)

        self.assertEqual(
            outcome(row),
            (
                "previous_accession",
                None,
                None,
                f"{original} was accepted at 2026-08-06T14:30:00+00:00,"
                " after this amendment at 2026-08-05T14:30:00+00:00",
            ),
        )
        self.assertEqual(row["declared_previous_accession"], original)

    def test_the_order_check_needs_both_times_and_a_later_original(self):
        original = self.index.add(accession(41, 1), "D", (41,), day(7, 6))
        raw = form_d_a(original, 41)
        cases = {
            "the same time": (AMENDMENT_ACCEPTED_AT, AMENDMENT_ACCEPTED_AT),
            "no original time": (None, AMENDMENT_ACCEPTED_AT),
            "no amendment time": (datetime(2026, 8, 6, tzinfo=UTC), None),
        }
        for name, (original_at, amendment_at) in cases.items():
            with self.subTest(name):
                self.filings["partner"] = [filings_row(original, "D", accepted_at=original_at)]
                amendment = filings_row(accession(41, 2), "D/A", raw, accepted_at=amendment_at)

                row = self.link(amendment, raw)

                self.assertEqual(outcome(row), ("previous_accession", original, "partner", None))

    def test_a_slash_a_filing_with_no_xml_is_none_declared(self):
        raw = submission(
            "D/A",
            accepted=ACCEPTED,
            filed=FILED,
            parties=[("FILER", "FUND", padded(41))],
            documents=[("D/A", "form_d_a.htm", b"<html><body>An amended Form D.</body></html>")],
        )

        row = self.link(filings_row(accession(41, 2), "D/A", raw), raw)

        self.assertEqual(outcome(row), ("none_declared", None, None, None))
        for column in (
            "declared_previous_accession",
            "declared_original_date",
            "declared_period",
            "amendment_number",
            "amendment_type",
            "source_document",
        ):
            self.assertIsNone(row[column], column)

        with self.subTest("bytes that do not parse"):
            raw = b"not a submission"

            row = self.link(filings_row(accession(41, 3), "D/A", raw), raw)

            self.assertEqual(row["link_rule"], "none_declared")
            self.assertTrue(row["link_problem"].startswith("submission parse error: "))

    def test_a_repeated_form_type_picks_its_declaring_part(self):
        form_type = "SC 13D/A;SC TO-T/A"
        original = self.index.add(accession(61, 1), "SC 13D", (61, 62), day(7, 14))

        with self.subTest("no XML document"):
            raw = submission(
                "SC 13D/A",
                accepted=ACCEPTED,
                filed=FILED,
                parties=[("SUBJECT COMPANY", "TARGET CORP", padded(61))],
                documents=[("SC 13D/A", "sc13da.htm", b"<html><body>Amendment</body></html>")],
            )

            row = self.link(filings_row(accession(62, 1), form_type, raw), raw)

            self.assertEqual(outcome(row), ("none_declared", None, None, None))

        with self.subTest("an edgarSubmission that names an indexed accession"):
            raw = schedule13_a("SC 13D/A", original, 61)

            row = self.link(filings_row(accession(62, 1), form_type, raw), raw)

            self.assertEqual(outcome(row), ("previous_accession", original, None, None))
            self.assertEqual((row["form_type"], row["amendment_number"]), (form_type, "1"))

    def test_link_row_takes_the_provenance_of_the_amendment(self):
        original = self.index.add(accession(41, 1), "D", (41,), day(7, 6))
        raw = form_d_a(original, 41)
        filing = filings_row(accession(41, 2), "D/A", raw)

        row = self.link(filing, raw, "partner")

        self.assertEqual(
            (row["accession_number"], row["form_type"], row["held_in"]),
            (filing["accession_number"], "D/A", "partner"),
        )
        self.assertEqual(row["source_url"], filing["source_url"])
        self.assertEqual(row["source_sha256"], hashlib.sha256(raw).hexdigest())
        for column in FILING_TIME_COLUMNS:
            self.assertEqual(row[column], filing[column], column)


class LinkContextTests(unittest.TestCase):
    def test_link_context_holds_the_ok_filings(self):
        index = Index()
        indexed = index.add(accession(71, 1), "13F-HR", (71,), day(8, 14))
        held = filings_row(indexed, "13F-HR", accepted_at=EARLIER, period="20260630")
        failed = filings_row(accession(71, 2), "13F-HR/A", outcome="not_found")
        parties = [
            filer_row(indexed, 9, role="FILED BY"),
            filer_row(indexed, 71),
            filer_row(indexed, 72),
            filer_row(failed["accession_number"], 71),
        ]

        context = link_context(
            index.rows,
            {"sample": [held, failed], "partner": []},
            {"sample": parties, "partner": []},
        )

        self.assertEqual(list(context.index), [indexed])
        self.assertEqual(
            context.held,
            {
                indexed: HeldFiling(
                    accession_number=indexed,
                    form_type="13F-HR",
                    held_in="sample",
                    accepted_at=EARLIER,
                    period_of_report="20260630",
                    filer_cik=71,
                )
            },
        )

    def test_amendment_filings_take_held_slash_a_filings_only(self):
        held_amendment = filings_row(accession(41, 2), "D/A")
        repeated = filings_row(accession(61, 2), "SC 13D/A;SC TO-T/A")
        rows = [
            filings_row(accession(41, 1), "D"),
            held_amendment,
            filings_row(accession(41, 3), "D/A", outcome="not_found"),
            repeated,
        ]

        self.assertEqual(amendment_filings(rows), [held_amendment, repeated])

    def test_link_rules(self):
        self.assertEqual(
            LINK_RULES,
            ("previous_accession", "original_date_issuer_owner", "filer_period", "none_declared"),
        )


class FixtureLinksTests(Stage4RootTestCase):
    def test_fixture_links(self):
        stage4 = self.layout.stage4_view
        table = read_table(stage4, "links")
        self.assertEqual(table.schema, SCHEMAS["links"])
        stamp = read_stamp(stage4.table("links"))
        self.assertEqual(stamp["table_format"], str(TABLE_FORMATS["links"]))
        expected = [
            (PARTNER_13D_A1, "previous_accession", SAMPLED_13D, "sample", None),
            (PARTNER_13D_A2, "previous_accession", PARTNER_13D_A1, "partner", None),
            (PARTNER_13F_A, "filer_period", SAMPLED_13F, "sample", None),
            (SAMPLED_D_A, "previous_accession", PARTNER_D, "partner", None),
            (SAMPLED_4_A, "original_date_issuer_owner", PARTNER_4, "partner", None),
            (SAMPLED_8K_A, "none_declared", None, None, None),
        ]

        rows = table.to_pylist()

        self.assertEqual(
            [(row["accession_number"], *outcome(row)) for row in rows],
            [(amendment, *rest) for amendment, *rest in sorted(expected, key=itemgetter(0))],
        )
        filings = {
            row["accession_number"]: (held_in, path_of, row)
            for held_in, layout, path_of in (
                ("sample", self.layout, self.layout.submission),
                ("partner", stage4, self.layout.partner_submission),
            )
            for row in read_table(layout, "filings").to_pylist()
        }
        for row in rows:
            amendment = row["accession_number"]
            held_in, path_of, filing = filings[amendment]
            with self.subTest(amendment=amendment):
                data = path_of(amendment).read_bytes()
                self.assertEqual(row["held_in"], held_in)
                self.assertEqual(row["form_type"], filing["form_type"])
                self.assertEqual(row["source_sha256"], hashlib.sha256(data).hexdigest())
                self.assertEqual(row["source_url"], filing["source_url"])
                for column in FILING_TIME_COLUMNS:
                    self.assertEqual(row[column], filing[column], column)
        (form13f,) = (row for row in rows if row["accession_number"] == PARTNER_13F_A)
        self.assertEqual(
            (form13f["declared_period"], form13f["amendment_type"]), ("20260630", "NEW HOLDINGS")
        )
