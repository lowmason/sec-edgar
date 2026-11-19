import contextlib
import datetime
import hashlib
import io
import json
import unittest
from dataclasses import replace
from operator import itemgetter
from pathlib import Path

from sec_filing_data import cli
from sec_filing_data.amendments import (
    CANDIDATE_FORMS,
    DATE_ISSUER_OWNER_FORMS,
    FILER_PERIOD_FORMS,
    PREVIOUS_ACCESSION_FORMS,
    Declared,
    Match,
    as_cik,
    as_date,
    declaring_form,
    index_filings,
    is_amendment,
    match_date_issuer_owner,
    read_declared,
)
from sec_filing_data.envelope import Party, parse_submission
from sec_filing_data.ownership import extract_ownership
from sec_filing_data.partners import (
    RULES,
    choose_partners,
    distinct_partners,
    read_partners,
    run_partners,
)
from sec_filing_data.sample import ARCHIVES
from sec_filing_data.tables import read_table, write_table
from tests.stage4_root import (
    form13f_cover_xml,
    form345_xml,
    form_d_xml,
    infotable_xml,
    schedule13_xml,
    submission,
)
from tests.test_commands import CommandTestCase

ACCEPTED = "20260805103000"
FILED = "20260805"


def accession(cik: int, number: int) -> str:
    return f"{cik:010d}-26-{number:06d}"


def padded(cik: int) -> str:
    return f"{cik:010d}"


def day(month: int, number: int) -> datetime.date:
    return datetime.date(2026, month, number)


def form_d_a(previous: str, cik: int) -> bytes:
    return submission(
        "D/A",
        accepted=ACCEPTED,
        filed=FILED,
        parties=[("FILER", f"FUND {cik}", padded(cik))],
        documents=[("D/A", "primary_doc.xml", form_d_xml(previous=previous))],
    )


def schedule13_a(form: str, previous: str, issuer: int) -> bytes:
    return submission(
        form,
        accepted=ACCEPTED,
        filed=FILED,
        parties=[("SUBJECT COMPANY", "ISSUER CORP", padded(issuer))],
        documents=[
            (
                form,
                "primary_doc.xml",
                schedule13_xml(
                    form, previous=previous, amendment_no="1", issuer_cik=padded(issuer)
                ),
            )
        ],
    )


def form4_a(original_date: str, issuer: int, owners: list[int]) -> bytes:
    return submission(
        "4/A",
        accepted=ACCEPTED,
        filed=FILED,
        parties=[
            *(("REPORTING-OWNER", f"OWNER {owner}", padded(owner)) for owner in owners),
            ("ISSUER", "ISSUER CORP", padded(issuer)),
        ],
        documents=[
            (
                "4/A",
                "form4a.xml",
                form345_xml(
                    "4/A",
                    original_date=original_date,
                    issuer_cik=padded(issuer),
                    owner_ciks=[padded(owner) for owner in owners],
                ),
            )
        ],
    )


class Index:
    """Index rows: one for each form type and CIK of an accession, numbered in the order added."""

    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(
        self, accession: str, form_types: str, ciks: tuple[int, ...], filed: datetime.date
    ) -> str:
        for form_type in form_types.split(";"):
            for cik in ciks:
                self.rows.append(
                    {
                        "line_number": len(self.rows) + 1,
                        "cik": cik,
                        "company_name": f"COMPANY {cik}",
                        "form_type": form_type,
                        "date_filed": filed,
                        "filename": f"edgar/data/{cik}/{accession}.txt",
                        "accession_number": accession,
                    }
                )
        return accession

    def first(self, accession: str) -> dict:
        rows = [row for row in self.rows if row["accession_number"] == accession]
        return min(rows, key=itemgetter("line_number"))

    def form_types(self, accession: str) -> str:
        return ";".join(
            sorted({row["form_type"] for row in self.rows if row["accession_number"] == accession})
        )


class PartnersTestCase(CommandTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.index = Index()
        self.sample: list[dict] = []
        self.files: dict[str, bytes] = {}

    def sampled(self, accession: str, raw: bytes | None = None, stratum: str = "uniform") -> None:
        """Add `accession` to the sample, as `sample` takes it from its first index row."""
        first = self.index.first(accession)
        self.sample.append(
            {
                "draw": len(self.sample) + 1,
                "stratum": stratum,
                "accession_number": accession,
                "form_type": self.index.form_types(accession),
                "cik": first["cik"],
                "company_name": first["company_name"],
                "date_filed": first["date_filed"],
                "filename": first["filename"],
                "url": ARCHIVES + first["filename"],
            }
        )
        if raw is not None:
            self.files[accession] = raw

    def write_root(self) -> None:
        """Write `index` and `sample`, each out of order, and the sampled bytes under `bytes/`."""
        write_table(self.layout, "index", list(reversed(self.index.rows)))
        write_table(self.layout, "sample", list(reversed(self.sample)))
        for sampled, raw in self.files.items():
            path = self.layout.submission(sampled)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)

    def run_rules(self) -> list[dict]:
        self.write_root()
        rows = run_partners(self.layout)
        self.assertEqual(read_partners(self.layout), rows)
        return rows

    def chosen(self) -> list[tuple[str, str, str]]:
        """(partner, rule, sampled accession) of each partner row, in table order."""
        return [
            (row["accession_number"], row["rule"], row["sampled_accession"])
            for row in self.run_rules()
        ]


class FormTests(unittest.TestCase):
    def test_form_sets_follow_c5(self):
        self.assertEqual(
            PREVIOUS_ACCESSION_FORMS,
            {"SCHEDULE 13D/A", "SCHEDULE 13G/A", "SC 13D/A", "SC 13G/A", "D/A"},
        )
        self.assertEqual(DATE_ISSUER_OWNER_FORMS, {"3/A", "4/A", "5/A"})
        self.assertEqual(FILER_PERIOD_FORMS, {"13F-HR/A"})
        self.assertEqual(
            CANDIDATE_FORMS,
            ("SCHEDULE 13D", "SCHEDULE 13G", "SC 13D", "SC 13G", "D", "3", "4", "5", "13F-HR"),
        )
        self.assertEqual(
            RULES,
            ("original_previous_accession", "original_date_issuer_owner", "candidate_amendment"),
        )

    def test_is_amendment_and_declaring_form(self):
        for form_type, amendment in (
            ("4/A", True),
            ("13F-HR/A", True),
            ("SC 13D/A;SC TO-T/A", True),
            ("4;SC 13D/A", True),
            ("4", False),
            ("4;SC 13D", False),
            ("10-K/AB", False),
        ):
            with self.subTest(form_type=form_type):
                self.assertIs(is_amendment(form_type), amendment)
        for form_type, form in (
            ("SC 13D/A;SC TO-T/A", "SC 13D/A"),
            ("SC TO-T/A;SCHEDULE 13D/A", "SCHEDULE 13D/A"),
            ("4/A;SCHEDULE 13D/A", "4/A"),
            ("D/A", "D/A"),
            ("5/A", "5/A"),
            ("13F-HR/A", "13F-HR/A"),
            ("8-K/A", None),
            ("SC TO-T/A", None),
            ("4", None),
        ):
            with self.subTest(form_type=form_type):
                self.assertEqual(declaring_form(form_type), form)

    def test_as_cik_and_as_date_are_strict(self):
        self.assertEqual(as_cik("0000000051"), 51)
        self.assertEqual(as_cik("51"), 51)
        for text in (None, "", " 51", "51 ", "+51", "-51", "5_1", "51a", "٥١"):
            with self.subTest(cik=text):
                self.assertIsNone(as_cik(text))
        self.assertEqual(as_date("2026-07-06"), datetime.date(2026, 7, 6))
        for text in (
            None,
            "",
            "20260706",
            "2026-7-6",
            "2026-02-30",
            "2026-W27-1",
            "2026-07-06T00:00",
            " 2026-07-06",
            "07-06-2026",
            "２026-07-06",
        ):
            with self.subTest(date=text):
                self.assertIsNone(as_date(text))


class ReadDeclaredTests(unittest.TestCase):
    def test_read_declared_reads_each_form(self):
        with self.subTest("SCHEDULE 13D/A"):
            raw = submission(
                "SCHEDULE 13D/A",
                accepted=ACCEPTED,
                filed=FILED,
                parties=[
                    ("SUBJECT COMPANY", "ISSUER CORP", "0000000061"),
                    ("FILED BY", "HOLDER LP", "0000000062"),
                ],
                documents=[
                    (
                        "SCHEDULE 13D/A",
                        "primary_doc.xml",
                        schedule13_xml(
                            "SCHEDULE 13D/A",
                            previous="0000000061-26-000001",
                            amendment_no="4",
                            issuer_cik="0000000061",
                        ),
                    )
                ],
            )
            self.assertEqual(
                read_declared("SCHEDULE 13D/A", raw),
                Declared(
                    previous_accession="0000000061-26-000001",
                    amendment_number="4",
                    source_document="primary_doc.xml",
                ),
            )
        with self.subTest("D/A"):
            self.assertEqual(
                read_declared("D/A", form_d_a("0000000041-26-000001", 41)),
                Declared(
                    previous_accession="0000000041-26-000001",
                    filer_cik="0000000041",
                    source_document="primary_doc.xml",
                ),
            )
        with self.subTest("4/A"):
            raw = submission(
                "4/A",
                accepted=ACCEPTED,
                filed=FILED,
                parties=[
                    ("REPORTING-OWNER", "OWNER ONE", "0001700537"),
                    ("REPORTING-OWNER", "OWNER TWO", "0001700538"),
                    ("ISSUER", "ISSUER CORP", "0000763532"),
                ],
                documents=[
                    (
                        "4/A",
                        "form4a.xml",
                        form345_xml(
                            "4/A",
                            original_date="2026-07-06",
                            issuer_cik="0000763532",
                            owner_ciks=["0001700537", "0001700538"],
                        ),
                    )
                ],
            )
            self.assertEqual(
                read_declared("4/A", raw),
                Declared(
                    original_date="2026-07-06",
                    issuer_cik="0000763532",
                    owner_ciks=("0001700537", "0001700538"),
                    source_document="form4a.xml",
                ),
            )
        with self.subTest("13F-HR/A"):
            raw = submission(
                "13F-HR/A",
                accepted=ACCEPTED,
                filed=FILED,
                period="20211231",
                parties=[("FILER", "MANAGER LLC", "0000000071")],
                documents=[
                    (
                        "13F-HR/A",
                        "primary_doc.xml",
                        form13f_cover_xml(
                            "13F-HR/A",
                            amendment_no="1",
                            amendment_type="NEW HOLDINGS",
                            period_of_report="12-31-2021",
                        ),
                    ),
                    ("INFORMATION TABLE", "infotable.xml", infotable_xml()),
                ],
            )
            self.assertEqual(
                read_declared("13F-HR/A", raw),
                Declared(
                    period="20211231",
                    amendment_number="1",
                    amendment_type="NEW HOLDINGS",
                    filer_cik="0000000071",
                    source_document="primary_doc.xml",
                ),
            )
        with self.subTest("8-K/A with no XML"):
            raw = submission(
                "8-K/A",
                accepted=ACCEPTED,
                filed=FILED,
                parties=[("FILER", "ACME CORP", "0000000081")],
                documents=[("8-K/A", "acme-8ka.htm", b"<html><body>amended</body></html>")],
            )
            self.assertEqual(read_declared("8-K/A", raw), Declared(filer_cik="0000000081"))
        with self.subTest("no SEC-HEADER"):
            declared = read_declared("D/A", b"<html>not a submission</html>")
            self.assertTrue(declared.problem.startswith("submission parse error: "), declared)
            self.assertEqual(replace(declared, problem=None), Declared())

    def test_a_form_reads_only_its_own_paths(self):
        with self.subTest("a form outside C5 reads no XML"):
            raw = submission(
                "8-K/A",
                accepted=ACCEPTED,
                filed=FILED,
                parties=[("FILER", "ACME CORP", "0000000081")],
                documents=[
                    (
                        "EX-99",
                        "primary_doc.xml",
                        schedule13_xml(
                            "SCHEDULE 13D/A",
                            previous="0000000081-26-000001",
                            amendment_no="2",
                            issuer_cik="0000000081",
                        ),
                    )
                ],
            )
            self.assertEqual(read_declared("8-K/A", raw), Declared(filer_cik="0000000081"))
        with self.subTest("a 4/A with no ownershipDocument"):
            raw = schedule13_a("SCHEDULE 13D/A", "0000000061-26-000001", 61)
            self.assertEqual(read_declared("4/A", raw), Declared())
        with self.subTest("a D/A does not read the schedule path"):
            raw = schedule13_a("SCHEDULE 13D/A", "0000000061-26-000001", 61)
            self.assertEqual(read_declared("D/A", raw), Declared(source_document="primary_doc.xml"))
        with self.subTest("a repeated form type with no edgarSubmission"):
            raw = submission(
                "SC 13D/A",
                accepted=ACCEPTED,
                filed=FILED,
                parties=[("FILED BY", "HOLDER LP", "0000000091")],
                documents=[("SC TO-T/A", "offer.htm", b"<html>offer</html>")],
            )
            self.assertEqual(read_declared(declaring_form("SC 13D/A;SC TO-T/A"), raw), Declared())
        with self.subTest("a D names no previous accession"):
            raw = submission(
                "D",
                accepted=ACCEPTED,
                filed=FILED,
                parties=[],
                documents=[("D", "primary_doc.xml", form_d_xml())],
            )
            self.assertEqual(read_declared("D/A", raw), Declared(source_document="primary_doc.xml"))


class MatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.index = Index()
        self.index.add(accession(9, 3), "4", (10, 9), day(8, 4))
        self.index.add(accession(9, 4), "4", (9, 11), day(8, 4))
        self.index.add(accession(9, 5), "4", (9, 11), day(8, 4))
        self.filings = index_filings(self.index.rows)

    def declared(self, original_date: str, issuer: str | None = None, *owners: str) -> Declared:
        return Declared(original_date=original_date, issuer_cik=issuer, owner_ciks=owners)

    def test_index_filings_group_each_accession(self):
        rows = list(reversed(self.index.rows))
        rows.append({**self.index.first(accession(9, 3)), "line_number": 99, "form_type": "4/A"})

        filing = index_filings(rows)[accession(9, 3)]

        self.assertEqual(filing.first, self.index.first(accession(9, 3)))
        self.assertEqual(filing.form_types, frozenset({"4", "4/A"}))
        self.assertEqual(filing.date_filed, day(8, 4))
        self.assertEqual(filing.ciks, frozenset({9, 10}))

    def test_match_date_issuer_owner(self):
        cases = {
            "the one match": (
                self.declared("2026-08-04", "0000000010", "0000000009"),
                Match(accession(9, 3), None),
            ),
            "a date that is not YYYY-MM-DD": (
                self.declared("08/04/2026"),
                Match(None, "dateOfOriginalSubmission 08/04/2026 is not a YYYY-MM-DD date"),
            ),
            "no issuer": (
                self.declared("2026-08-04", None, "0000000009"),
                Match(None, "no issuerCik or rptOwnerCik"),
            ),
            "no owner": (
                self.declared("2026-08-04", "0000000010"),
                Match(None, "no issuerCik or rptOwnerCik"),
            ),
            "a CIK that is not a number": (
                self.declared("2026-08-04", "0000000010", "N/A"),
                Match(None, "CIK N/A is not a number"),
            ),
            "no match on another date": (
                self.declared("2026-08-05", "0000000010", "0000000009"),
                Match(None, "no index match for 2026-08-05 and CIKs 9, 10"),
            ),
            "no match on a subset of the CIKs": (
                self.declared("2026-08-04", "0000000010", "0000000010"),
                Match(None, "no index match for 2026-08-04 and CIKs 10"),
            ),
            "two matches": (
                self.declared("2026-08-04", "0000000011", "0000000009"),
                Match(None, f"2 index matches: {accession(9, 4)}, {accession(9, 5)}"),
            ),
        }
        for name, (declared, expected) in cases.items():
            with self.subTest(name):
                self.assertEqual(match_date_issuer_owner(declared, "4/A", self.filings), expected)

    def test_match_takes_the_base_form(self):
        declared = self.declared("2026-08-04", "0000000010", "0000000009")
        self.assertEqual(
            match_date_issuer_owner(declared, "3/A", self.filings),
            Match(None, "no index match for 2026-08-04 and CIKs 9, 10"),
        )


class RuleTests(PartnersTestCase):
    def test_rule_1(self):
        named = self.index.add(accession(41, 1), "D", (41,), day(7, 1))
        names_indexed = self.index.add(accession(41, 2), "D/A", (41,), day(8, 5))
        names_missing = self.index.add(accession(42, 2), "D/A", (42,), day(8, 5))
        sampled_original = self.index.add(accession(43, 1), "D", (43,), day(7, 1))
        names_sampled = self.index.add(accession(43, 2), "D/A", (43,), day(8, 5))
        named_schedule = self.index.add(
            accession(44, 1), "SC 13D/A;SC TO-T/A", (44, 45), day(7, 2)
        )
        schedule = self.index.add(accession(44, 2), "SC 13D/A", (44, 45), day(8, 6))
        self.sampled(names_indexed, form_d_a(named, 41))
        self.sampled(names_missing, form_d_a(accession(42, 99), 42))
        self.sampled(sampled_original)
        self.sampled(names_sampled, form_d_a(sampled_original, 43))
        self.sampled(schedule, schedule13_a("SC 13D/A", named_schedule, 44))

        rows = self.run_rules()

        self.assertEqual(
            rows[0],
            {
                "accession_number": "0000000041-26-000001",
                "form_type": "D",
                "cik": 41,
                "company_name": "COMPANY 41",
                "date_filed": datetime.date(2026, 7, 1),
                "filename": "edgar/data/41/0000000041-26-000001.txt",
                "url": "https://www.sec.gov/Archives/edgar/data/41/0000000041-26-000001.txt",
                "rule": "original_previous_accession",
                "sampled_accession": "0000000041-26-000002",
            },
        )
        self.assertEqual(
            [
                (row["accession_number"], row["form_type"], row["cik"], row["sampled_accession"])
                for row in rows[1:]
            ],
            [(named_schedule, "SC 13D/A;SC TO-T/A", 44, schedule)],
        )
        self.assertEqual({row["rule"] for row in rows}, {"original_previous_accession"})

    def test_rule_2_compares_ciks_as_numbers_and_dates_as_dates(self):
        found = self.index.add(accession(51, 3), "4", (51, 52), day(8, 4))
        self.index.add(accession(51, 4), "4", (51,), day(8, 4))
        self.index.add(accession(51, 5), "4", (51, 52, 59), day(8, 4))
        self.index.add(accession(51, 6), "3", (51, 52), day(8, 4))
        one_match = self.index.add(accession(51, 9), "4/A", (51, 52), day(8, 10))
        self.index.add(accession(53, 3), "4", (53, 54), day(8, 5))
        other_date = self.index.add(accession(53, 9), "4/A", (53, 54), day(8, 10))
        self.index.add(accession(55, 3), "4", (55, 56), day(8, 4))
        self.index.add(accession(55, 4), "4", (55, 56), day(8, 4))
        two_matches = self.index.add(accession(55, 9), "4/A", (55, 56), day(8, 10))
        sampled_original = self.index.add(accession(57, 3), "4", (57, 58), day(8, 4))
        names_sampled = self.index.add(accession(57, 9), "4/A", (57, 58), day(8, 10))
        for amendment, issuer, owner in (
            (one_match, 51, 52),
            (other_date, 53, 54),
            (two_matches, 55, 56),
            (names_sampled, 57, 58),
        ):
            self.sampled(amendment, form4_a("2026-08-04", issuer, [owner]))
        self.sampled(sampled_original, stratum="quota")

        self.assertEqual(self.chosen(), [(found, "original_date_issuer_owner", one_match)])

    def test_rule_3(self):
        sampled = self.index.add(accession(61, 1), "SCHEDULE 13D", (61, 62), day(8, 3))
        later = self.index.add(accession(61, 2), "SCHEDULE 13D/A", (61, 62), day(8, 10))
        same_day = self.index.add(accession(61, 3), "SCHEDULE 13D/A", (62, 61), day(8, 3))
        self.index.add(accession(61, 4), "SCHEDULE 13D/A", (61, 62, 63), day(8, 10))
        self.index.add(accession(61, 5), "SCHEDULE 13D/A", (61, 62), day(8, 2))
        sampled_amendment = self.index.add(
            accession(61, 6), "SCHEDULE 13D/A", (61, 62), day(8, 11)
        )
        self.index.add(accession(61, 7), "SCHEDULE 13D/A", (61,), day(8, 10))
        self.index.add(accession(61, 8), "SC 13D/A", (61, 62), day(8, 10))
        self.sampled(sampled, stratum="quota")
        self.sampled(sampled_amendment)
        self.assertEqual(self.sample[0]["cik"], 61)

        self.assertEqual(
            self.chosen(),
            [(later, "candidate_amendment", sampled), (same_day, "candidate_amendment", sampled)],
        )

    def test_repeated_rows_and_partners_of_partners_are_skipped(self):
        named = self.index.add(accession(91, 1), "SC 13D", (91, 92), day(7, 1))
        repeated = self.index.add(accession(91, 2), "SC 13D/A;SC TO-T/A", (91, 92), day(8, 5))
        repeated_raw = schedule13_a("SC 13D/A", named, 91)
        self.sampled(repeated, repeated_raw, stratum="repeated")
        original = self.index.add(accession(41, 1), "D", (41,), day(7, 1))
        amendment = self.index.add(accession(41, 2), "D/A", (41,), day(8, 5))
        self.index.add(accession(41, 3), "D/A", (41,), day(8, 6))
        self.sampled(amendment, form_d_a(original, 41))
        # Without the skip, rule 1 would read the repeated filing's previous accession.
        form = declaring_form(self.sample[0]["form_type"])
        self.assertEqual(read_declared(form, repeated_raw).previous_accession, named)

        self.assertEqual(self.chosen(), [(original, "original_previous_accession", amendment)])

    def test_one_partner_chosen_twice_is_one_distinct_partner(self):
        first = self.index.add(accession(61, 1), "SCHEDULE 13D", (61, 62), day(8, 3))
        second = self.index.add(accession(62, 1), "SCHEDULE 13D", (62, 61), day(8, 4))
        amendment = self.index.add(accession(61, 2), "SCHEDULE 13D/A", (61, 62), day(8, 10))
        self.sampled(second, stratum="quota")
        self.sampled(first, stratum="quota")

        rows = self.run_rules()

        self.assertEqual(
            [(row["accession_number"], row["rule"], row["sampled_accession"]) for row in rows],
            [(amendment, "candidate_amendment", first), (amendment, "candidate_amendment", second)],
        )
        self.assertEqual(distinct_partners(rows), [rows[0]])

    def test_distinct_partners_keep_the_first_row_in_accession_order(self):
        rows = [
            {"accession_number": "B", "sampled_accession": "1"},
            {"accession_number": "A", "sampled_accession": "2"},
            {"accession_number": "B", "sampled_accession": "3"},
            {"accession_number": "A", "sampled_accession": "4"},
        ]
        self.assertEqual(distinct_partners(rows), [rows[1], rows[0]])

    def test_choose_partners_reads_only_sampled_amendments(self):
        named = self.index.add(accession(41, 1), "D", (41,), day(7, 1))
        amendment = self.index.add(accession(41, 2), "D/A", (41,), day(8, 5))
        sampled_8k = self.index.add(accession(81, 1), "8-K", (81,), day(8, 5))
        self.sampled(amendment)
        self.sampled(sampled_8k)
        read = []

        def read_sampled(sampled: str) -> bytes | None:
            read.append(sampled)
            return form_d_a(named, 41)

        rows = choose_partners(self.index.rows, self.sample, read_sampled)

        self.assertEqual(read, [amendment])
        self.assertEqual([row["accession_number"] for row in rows], [named])


class PartnersCommandTests(PartnersTestCase):
    def build(self) -> None:
        """Rule 1 gives a D, rule 2 a 4, and rule 3 two 13D/As, one of them from two filings."""
        original_d = self.index.add(accession(41, 1), "D", (41,), day(7, 1))
        amendment_d = self.index.add(accession(41, 2), "D/A", (41,), day(8, 5))
        self.index.add(accession(51, 3), "4", (51, 52), day(8, 4))
        amendment_4 = self.index.add(accession(51, 9), "4/A", (51, 52), day(8, 10))
        first_13d = self.index.add(accession(61, 1), "SCHEDULE 13D", (61, 62), day(8, 3))
        self.index.add(accession(61, 2), "SCHEDULE 13D/A", (61, 62), day(8, 10))
        second_13d = self.index.add(accession(62, 1), "SCHEDULE 13D", (61, 62), day(8, 11))
        self.index.add(accession(61, 3), "SCHEDULE 13D/A", (61, 62), day(8, 12))
        other = self.index.add(accession(81, 1), "8-K", (81,), day(8, 5))
        self.sampled(amendment_d, form_d_a(original_d, 41))
        self.sampled(amendment_4, form4_a("2026-08-04", 51, [52]))
        self.sampled(first_13d, stratum="quota")
        self.sampled(second_13d, stratum="quota")
        self.sampled(other)

    def hashes(self) -> dict[Path, str]:
        return {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for folder in (self.layout.tables, self.layout.bytes_dir)
            for path in folder.rglob("*")
            if path.is_file()
        }

    def test_partners_command_writes_under_stage4(self):
        self.build()
        self.write_root()
        before = self.hashes()
        stdout, stderr = io.StringIO(), io.StringIO()

        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = cli.main(["partners", "--out", str(self.layout.root)])

        self.assertEqual((code, stderr.getvalue()), (0, ""))
        self.assertEqual(
            stdout.getvalue(),
            "partners: 4\n"
            "original_previous_accession: 1\n"
            "original_date_issuer_owner: 1\n"
            "candidate_amendment: 3\n",
        )
        table = read_table(self.layout.stage4_view, "partners").to_pylist()
        self.assertEqual(
            [(row["accession_number"], row["rule"]) for row in table],
            [
                (accession(41, 1), "original_previous_accession"),
                (accession(51, 3), "original_date_issuer_owner"),
                (accession(61, 2), "candidate_amendment"),
                (accession(61, 3), "candidate_amendment"),
                (accession(61, 3), "candidate_amendment"),
            ],
        )
        self.assertEqual(self.hashes(), before)
        outside = {
            path.relative_to(self.layout.root).as_posix()
            for path in self.layout.root.rglob("*")
            if path.is_file()
            and not path.is_relative_to(self.layout.tables)
            and not path.is_relative_to(self.layout.bytes_dir)
        }
        self.assertEqual(outside, {"runs.jsonl", "stage4/tables/partners.parquet"})
        steps = [
            json.loads(line)["step"]
            for line in self.layout.runs.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(steps, ["partners"])

    def test_read_partners_needs_the_table(self):
        with self.assertRaises(FileNotFoundError) as caught:
            read_partners(self.layout)

        path = self.layout.root / "stage4" / "tables" / "partners.parquet"
        self.assertEqual(str(caught.exception), f"{path} is missing: run partners first")


class BuilderTests(unittest.TestCase):
    """The submission builder gives bytes that the envelope parser and Stage 3 parsers read."""

    def test_the_envelope_reads_the_header(self):
        raw = submission(
            "13F-HR",
            accepted=ACCEPTED,
            filed=FILED,
            period="20260630",
            parties=[("FILER", "MANAGER LLC", "0000000071")],
            documents=[
                ("13F-HR", "primary_doc.xml", form13f_cover_xml("13F-HR")),
                ("INFORMATION TABLE", "infotable.xml", infotable_xml()),
            ],
        )

        parsed = parse_submission(raw)

        self.assertEqual(parsed.acceptance_datetime, ACCEPTED)
        self.assertEqual(parsed.field("CONFORMED SUBMISSION TYPE"), "13F-HR")
        self.assertEqual(parsed.field("FILED AS OF DATE"), FILED)
        self.assertEqual(parsed.field("CONFORMED PERIOD OF REPORT"), "20260630")
        self.assertEqual(parsed.field("PUBLIC DOCUMENT COUNT"), "2")
        self.assertEqual(parsed.parties, (Party("FILER", "MANAGER LLC", "0000000071"),))
        self.assertEqual(
            [(document.type, document.filename) for document in parsed.documents],
            [("13F-HR", "primary_doc.xml"), ("INFORMATION TABLE", "infotable.xml")],
        )
        no_period = parse_submission(submission("8-K", accepted=ACCEPTED, filed=FILED, parties=[]))
        self.assertIsNone(no_period.field("CONFORMED PERIOD OF REPORT"))

    def test_the_parts_parse_as_stage3_reads_them(self):
        schedule = submission(
            "SCHEDULE 13D",
            accepted=ACCEPTED,
            filed=FILED,
            parties=[("SUBJECT COMPANY", "ISSUER CORP", "0000000061")],
            documents=[
                (
                    "SCHEDULE 13D",
                    "primary_doc.xml",
                    schedule13_xml("SCHEDULE 13D", issuer_cik="0000000061"),
                )
            ],
        )
        form4 = submission(
            "4",
            accepted=ACCEPTED,
            filed=FILED,
            parties=[("ISSUER", "ISSUER CORP", "0000000051")],
            documents=[
                (
                    "4",
                    "form4.xml",
                    form345_xml("4", issuer_cik="0000000051", owner_ciks=["0000000052"]),
                )
            ],
        )
        form13f = submission(
            "13F-HR",
            accepted=ACCEPTED,
            filed=FILED,
            period="20260630",
            parties=[("FILER", "MANAGER LLC", "0000000071")],
            documents=[
                ("13F-HR", "primary_doc.xml", form13f_cover_xml("13F-HR")),
                ("INFORMATION TABLE", "infotable.xml", infotable_xml()),
            ],
        )
        for form, raw, document, owner in (
            ("SCHEDULE 13D", schedule, "primary_doc.xml", None),
            ("4", form4, "form4.xml", "0000000052"),
            ("13F-HR", form13f, "infotable.xml", "0000000071"),
        ):
            with self.subTest(form=form):
                extraction = extract_ownership(form, "ok", raw)
                self.assertEqual(
                    (extraction.reason, len(extraction.records), extraction.source_document),
                    (None, 1, document),
                )
                self.assertEqual(extraction.records[0].owner_cik, owner)


if __name__ == "__main__":
    unittest.main()
