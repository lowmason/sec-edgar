import contextlib
import io
import json
import unittest
from dataclasses import asdict, fields, replace
from pathlib import Path

from sec_filing_data import cli
from sec_filing_data.envelope import parse_submission
from sec_filing_data.forms345 import no_securities_owned, parse_form345
from sec_filing_data.ownership import OWNERSHIP_FORMS, OwnershipRecord, run_ownership, xml_document
from sec_filing_data.report import run_report
from sec_filing_data.tables import SCHEMAS, read_table
from tests.test_commands import section
from tests.test_xbrl import FactsRootTestCase, submission_with, wrapped

FIXTURES = Path(__file__).parent / "fixtures"
FORM4 = (FIXTURES / "form4.xml").read_bytes()
FORM3 = (FIXTURES / "form3.xml").read_bytes()

# form4.xml is the ownershipDocument of the pilot Form 4 0001628280-26-047997 as filed: both
# non-derivative rows and its derivative row. form3.xml is the ownershipDocument of the pilot
# Form 3 0001729835-26-000009 with only whole rows removed: its first 2 of 10 non-derivative
# holdings and its first 2 of 5 derivative holdings stay.
FORM4_PARTIES = {
    "issuer_cik": "0000874501",
    "issuer_name": "OCTAVE SPECIALTY GROUP INC",
    "owner_cik": "0001480597",
    "owner_name": "Trick David",
    "owner_count": 1,
}
FORM3_PARTIES = {
    "issuer_cik": "0002115119",
    "issuer_name": "Columbia Financial, Inc./MD/",
    "owner_cik": "0001729835",
    "owner_name": "Gibney Dennis E.",
    "owner_count": 1,
}
UNMAPPED = ("issuer_cusip", "shares_kind", "put_call", "percent_of_class", "value_usd")
OTHER_DOCUMENT = b'<?xml version="1.0"?>\n<otherDocument/>'


def record(**values) -> OwnershipRecord:
    """An OwnershipRecord with every column that the test does not name set to None."""
    blank = {field.name: None for field in fields(OwnershipRecord)}
    return OwnershipRecord(**(blank | values))


def ownership_xml(body: str, namespace: str = "") -> bytes:
    return f'<?xml version="1.0"?>\n<ownershipDocument{namespace}>\n{body}\n</ownershipDocument>'.encode()


class RecordTests(unittest.TestCase):
    def test_fields_are_the_ownership_columns_from_record_kind_to_value_usd(self):
        self.assertEqual(
            [field.name for field in fields(OwnershipRecord)], SCHEMAS["ownership"].names[2:]
        )

    def test_record_is_frozen(self):
        with self.assertRaises(AttributeError):
            record(record_kind="x").record_kind = "y"

    def test_ownership_forms(self):
        self.assertEqual(
            OWNERSHIP_FORMS,
            {
                "3", "3/A", "4", "4/A", "5", "5/A",
                "SCHEDULE 13D", "SCHEDULE 13D/A", "SCHEDULE 13G", "SCHEDULE 13G/A",
                "SC 13D", "SC 13D/A", "SC 13G", "SC 13G/A", "13F-HR", "13F-HR/A",
            },
        )  # fmt: skip


class ParseForm345Tests(unittest.TestCase):
    def test_form4_transactions(self):
        records = parse_form345(FORM4)

        self.assertEqual(
            [r.record_kind for r in records],
            ["non_derivative_transaction", "non_derivative_transaction", "derivative_transaction"],
        )
        self.assertEqual(
            records[0],
            record(
                record_kind="non_derivative_transaction",
                **FORM4_PARTIES,
                security_title="Common Stock",
                transaction_date="2026-07-09",
                transaction_code="M",
                shares="13206",
                price_per_share=None,  # filed with a footnote and no value
                acquired_disposed="A",
                shares_after="273837",
                direct_indirect="D",
            ),
        )

    def test_form4_other_rows(self):
        records = parse_form345(FORM4)

        self.assertEqual(
            records[1],
            record(
                record_kind="non_derivative_transaction",
                **FORM4_PARTIES,
                security_title="Common Stock",
                transaction_date="2026-07-09",
                transaction_code="F",
                shares="6741",
                price_per_share="6.08",
                acquired_disposed="D",
                shares_after="267096",
                direct_indirect="D",
            ),
        )
        self.assertEqual(
            records[2],
            record(
                record_kind="derivative_transaction",
                **FORM4_PARTIES,
                security_title="Restricted Stock Units",
                transaction_date="2026-07-09",
                transaction_code="M",
                shares="13206",
                price_per_share="0",
                acquired_disposed="D",
                shares_after="124978",
                direct_indirect="D",
            ),
        )

    def test_form3_holdings(self):
        records = parse_form345(FORM3)

        self.assertEqual(
            [r.record_kind for r in records],
            ["non_derivative_holding"] * 2 + ["derivative_holding"] * 2,
        )
        self.assertEqual(
            records[0],
            record(
                record_kind="non_derivative_holding",
                **FORM3_PARTIES,
                security_title="Common Stock",
                shares_after="4296",
                direct_indirect="I",
            ),
        )
        self.assertEqual(
            records[1],
            record(
                record_kind="non_derivative_holding",
                **FORM3_PARTIES,
                security_title="Common Stock",
                shares_after="356092",
                direct_indirect="D",
            ),
        )
        # A derivative holding has no postTransactionAmounts. Its underlying shares are not mapped.
        derivative = record(
            record_kind="derivative_holding",
            **FORM3_PARTIES,
            security_title="Stock Options (right to buy)",
            direct_indirect="D",
        )
        self.assertEqual(records[2:], [derivative, derivative])

    def test_two_reporting_owners(self):
        text = FORM4.decode()
        start = text.index("<reportingOwner>")
        end = text.index("</reportingOwner>") + len("</reportingOwner>")
        second = text[start:end].replace("0001480597", "0009999999").replace("Trick David", "Other")
        two = (text[:end] + "\n    " + second + text[end:]).encode()

        records = parse_form345(two)

        self.assertEqual([r.owner_count for r in records], [2, 2, 2])
        self.assertEqual(
            {(r.owner_cik, r.owner_name) for r in records}, {("0001480597", "Trick David")}
        )

    def test_a_second_reporting_owner_changes_only_the_owner_count(self):
        text = FORM4.decode()
        end = text.index("</reportingOwner>") + len("</reportingOwner>")
        two = (text[:end] + text[text.index("<reportingOwner>") : end] + text[end:]).encode()

        records = parse_form345(two)

        self.assertEqual([replace(r, owner_count=1) for r in records], parse_form345(FORM4))

    def test_columns_outside_the_mapping_are_null(self):
        for records in (parse_form345(FORM4), parse_form345(FORM3)):
            for row in records:
                self.assertEqual([getattr(row, name) for name in UNMAPPED], [None] * 5)

    def test_holdings_have_no_transaction_fields(self):
        for row in parse_form345(FORM3):
            self.assertEqual(
                [
                    row.transaction_date,
                    row.transaction_code,
                    row.shares,
                    row.price_per_share,
                    row.acquired_disposed,
                ],
                [None] * 5,
            )

    def test_text_is_stripped_and_empty_is_null_and_nothing_is_converted(self):
        xml = ownership_xml(
            "<issuer><issuerCik>  0001  </issuerCik><issuerName></issuerName></issuer>"
            "<nonDerivativeTable><nonDerivativeHolding>"
            "<securityTitle><value>  </value></securityTitle>"
            "<postTransactionAmounts><sharesOwnedFollowingTransaction>"
            "<value>\n 0013.50\n</value></sharesOwnedFollowingTransaction></postTransactionAmounts>"
            "</nonDerivativeHolding></nonDerivativeTable>"
        )

        (row,) = parse_form345(xml)

        self.assertEqual(
            (row.issuer_cik, row.issuer_name, row.security_title, row.shares_after),
            ("0001", None, None, "0013.50"),
        )

    def test_elements_match_by_local_name_in_any_namespace(self):
        body = (
            "<o:issuer><o:issuerCik>1</o:issuerCik></o:issuer>"
            "<o:reportingOwner><o:reportingOwnerId><o:rptOwnerName>N</o:rptOwnerName>"
            "</o:reportingOwnerId></o:reportingOwner>"
            "<o:nonDerivativeTable><o:nonDerivativeHolding>"
            "<o:ownershipNature><o:directOrIndirectOwnership><o:value>D</o:value>"
            "</o:directOrIndirectOwnership></o:ownershipNature>"
            "</o:nonDerivativeHolding></o:nonDerivativeTable>"
        )
        xml = (
            '<o:ownershipDocument xmlns:o="urn:example:own">' + body + "</o:ownershipDocument>"
        ).encode()

        (row,) = parse_form345(xml)

        self.assertEqual(
            (row.issuer_cik, row.owner_name, row.owner_count, row.direct_indirect),
            ("1", "N", 1, "D"),
        )

    def test_rows_come_in_document_order_across_row_kinds(self):
        def holding(title):
            return f"<securityTitle><value>{title}</value></securityTitle>"

        xml = ownership_xml(
            "<nonDerivativeTable>"
            f"<nonDerivativeHolding>{holding('a')}</nonDerivativeHolding>"
            f"<nonDerivativeTransaction>{holding('b')}</nonDerivativeTransaction>"
            f"<nonDerivativeHolding>{holding('c')}</nonDerivativeHolding>"
            "</nonDerivativeTable><derivativeTable>"
            f"<derivativeHolding>{holding('d')}</derivativeHolding>"
            f"<derivativeTransaction>{holding('e')}</derivativeTransaction>"
            "</derivativeTable>"
        )

        self.assertEqual(
            [(r.record_kind, r.security_title) for r in parse_form345(xml)],
            [
                ("non_derivative_holding", "a"),
                ("non_derivative_transaction", "b"),
                ("non_derivative_holding", "c"),
                ("derivative_holding", "d"),
                ("derivative_transaction", "e"),
            ],
        )

    def test_a_document_with_no_owner_has_a_null_owner_and_a_zero_count(self):
        xml = ownership_xml("<nonDerivativeTable><nonDerivativeHolding/></nonDerivativeTable>")

        (row,) = parse_form345(xml)

        self.assertEqual((row.owner_cik, row.owner_name, row.owner_count), (None, None, 0))

    def test_no_securities_owned_flag(self):
        flags = {"1": True, "true": True, " 1 ": True, "0": False, "false": False, "": False}
        for text, expected in flags.items():
            with self.subTest(text=text):
                xml = ownership_xml(f"<noSecuritiesOwned>{text}</noSecuritiesOwned>")
                self.assertIs(no_securities_owned(xml), expected)
        self.assertIs(no_securities_owned(ownership_xml("")), False)
        self.assertIs(no_securities_owned(FORM3), False)  # the fixture says 0


class XmlDocumentTests(unittest.TestCase):
    def submission(self, *documents: tuple[str, str, str]) -> tuple[bytes, object]:
        raw = submission_with(*documents, form="4")
        return raw, parse_submission(raw)

    def test_the_first_document_with_the_root_comes_back_as_its_text(self):
        raw, submission = self.submission(
            ("EX-24.1", "poa.htm", "<HTML>\n<BODY><P>power<BR></BODY>\n</HTML>\n"),
            ("GRAPHIC", "sig.jpg", "begin 644 sig.jpg\nM_]C_X\n"),
            ("4", "first.xml", wrapped(FORM4, "XML")),
            ("4", "second.xml", wrapped(FORM3, "XML")),
        )

        self.assertEqual(xml_document(raw, submission, "ownershipDocument"), FORM4)

    def test_a_document_that_is_not_xml_with_that_root_gives_none(self):
        raw, submission = self.submission(("4", "a.xml", wrapped(OTHER_DOCUMENT, "XML")))
        self.assertIsNone(xml_document(raw, submission, "ownershipDocument"))
        self.assertEqual(xml_document(raw, submission, "otherDocument"), OTHER_DOCUMENT)

        raw, submission = self.submission()
        self.assertIsNone(xml_document(raw, submission, "ownershipDocument"))

    def test_the_root_matches_by_local_name_in_any_namespace(self):
        default = b'<ownershipDocument xmlns="urn:example:own"/>'
        prefixed = b'<o:ownershipDocument xmlns:o="urn:example:own"/>'
        for text in (default, prefixed):
            with self.subTest(text=text):
                raw, submission = self.submission(("4", "a.xml", wrapped(text, "XML")))
                self.assertEqual(xml_document(raw, submission, "ownershipDocument"), text)

    def test_text_that_does_not_start_with_an_angle_bracket_is_skipped(self):
        raw, submission = self.submission(
            ("4", "a.xml", "x<ownershipDocument/>\n"),
            ("4", "b.xml", "\n  \n  <ownershipDocument/>\n"),
        )

        self.assertEqual(
            xml_document(raw, submission, "ownershipDocument"), b"<ownershipDocument/>"
        )

    def test_a_doctype_is_refused(self):
        doctype = b'<!DOCTYPE ownershipDocument [<!ENTITY x "y">]>\n<ownershipDocument>&x;</ownershipDocument>'
        raw, submission = self.submission(("4", "a.xml", wrapped(doctype, "XML")))

        self.assertIsNone(xml_document(raw, submission, "ownershipDocument"))

    def test_a_document_that_does_not_parse_is_skipped_not_raised(self):
        raw, submission = self.submission(
            ("4", "a.xml", "<ownershipDocument><unclosed>\n"),
            ("4", "b.xml", wrapped(FORM3, "XML")),
        )

        self.assertEqual(xml_document(raw, submission, "ownershipDocument"), FORM3)


class RunOwnershipTestCase(FactsRootTestCase):
    """A temporary root as in the facts tests. Its `run_facts` method is not used here."""

    def add_filing(self, form_type: str, xml: bytes | None = FORM4) -> str:
        """Sample one fetched filing whose only document holds `xml` (no document for None)."""
        first_part = form_type.split(";")[0]
        documents = [] if xml is None else [(first_part, "doc.xml", wrapped(xml, "XML"))]
        return self.add(form_type, submission_with(*documents, form=first_part))

    def run_ownership(self, **kwargs) -> tuple[list[dict], list[dict]]:
        self.write_tables(**kwargs)
        self.assertEqual(run_ownership(self.layout), 0)
        records = read_table(self.layout, "ownership")
        status = read_table(self.layout, "ownership_status")
        self.assertEqual(records.schema, SCHEMAS["ownership"])
        self.assertEqual(status.schema, SCHEMAS["ownership_status"])
        return records.to_pylist(), status.to_pylist()


def ownership_row(accession: str, form_type: str, row: OwnershipRecord) -> dict:
    return {"accession_number": accession, "form_type": form_type} | asdict(row)


class RunOwnershipTests(RunOwnershipTestCase):
    def test_form4_and_form3_rows_follow_the_sample_and_the_records(self):
        form3 = self.add_filing("3", FORM3)
        form4 = self.add_filing("4", FORM4)

        rows, status = self.run_ownership()

        self.assertEqual(
            rows,
            [ownership_row(form3, "3", r) for r in parse_form345(FORM3)]
            + [ownership_row(form4, "4", r) for r in parse_form345(FORM4)],
        )
        self.assertEqual(
            status,
            [
                {"accession_number": form3, "form_type": "3", "record_count": 4, "reason": None},
                {"accession_number": form4, "form_type": "4", "record_count": 3, "reason": None},
            ],
        )

    def test_no_ownership_xml_gives_reason(self):
        other = self.add_filing("4", OTHER_DOCUMENT)

        rows, status = self.run_ownership()

        self.assertEqual(rows, [])
        self.assertEqual(
            status,
            [
                {
                    "accession_number": other,
                    "form_type": "4",
                    "record_count": 0,
                    "reason": "no ownership XML document",
                }
            ],
        )

    def test_a_submission_with_no_document_gives_the_same_reason(self):
        nothing = self.add_filing("4", None)

        rows, status = self.run_ownership()

        self.assertEqual(rows, [])
        self.assertEqual(
            [(row["accession_number"], row["record_count"], row["reason"]) for row in status],
            [(nothing, 0, "no ownership XML document")],
        )

    def test_reasons_follow_the_order_of_the_checks(self):
        good = self.add_filing("4", FORM4)
        not_found = self.add("4", None, outcome="not_found")
        corrupt = self.add("5", b"not a submission\n")
        schedule = self.add_filing("SCHEDULE 13D", FORM4)
        repeated = self.add_filing("SC 13D/A;SC TO-T/A", FORM4)
        joined = self.add_filing("4;SC 13D", FORM4)
        thirteen_f_missing = self.add("13F-HR", None, outcome="not_found")
        thirteen_f_corrupt = self.add("13F-HR/A", b"not a submission\n")
        no_xml = self.add_filing("4/A", OTHER_DOCUMENT)
        owns_nothing = self.add_filing(
            "3", ownership_xml("<noSecuritiesOwned>1</noSecuritiesOwned>")
        )
        owns_nothing_true = self.add_filing(
            "3/A", ownership_xml("<noSecuritiesOwned>true</noSecuritiesOwned>")
        )
        no_records = self.add_filing("5", ownership_xml("<noSecuritiesOwned>0</noSecuritiesOwned>"))
        empty = self.add_filing("5/A", ownership_xml(""))
        self.add_filing("8-K", FORM4)
        self.add_filing("424B2", FORM4)
        failed = self.add("4", None, outcome="failed")
        last = self.add_filing("4", FORM3)

        rows, status = self.run_ownership()

        self.assertEqual(
            [
                (row["accession_number"], row["form_type"], row["record_count"], row["reason"])
                for row in status
            ],
            [
                (good, "4", 3, None),
                (not_found, "4", 0, "not_found"),
                (
                    corrupt,
                    "5",
                    0,
                    "submission parse error: no <SEC-HEADER> ... </SEC-HEADER> block",
                ),
                (schedule, "SCHEDULE 13D", 0, "parser not built"),
                (repeated, "SC 13D/A;SC TO-T/A", 0, "parser not built"),
                (joined, "4;SC 13D", 0, "parser not built"),
                (thirteen_f_missing, "13F-HR", 0, "not_found"),
                (
                    thirteen_f_corrupt,
                    "13F-HR/A",
                    0,
                    "submission parse error: no <SEC-HEADER> ... </SEC-HEADER> block",
                ),
                (no_xml, "4/A", 0, "no ownership XML document"),
                (owns_nothing, "3", 0, "no securities owned"),
                (owns_nothing_true, "3/A", 0, "no securities owned"),
                (no_records, "5", 0, "no records in the ownership document"),
                (empty, "5/A", 0, "no records in the ownership document"),
                (failed, "4", 0, "failed"),
                (last, "4", 4, None),
            ],
        )
        self.assertEqual(
            [(row["accession_number"], row["form_type"]) for row in rows],
            [(good, "4")] * 3 + [(last, "4")] * 4,
        )

    def test_fetches_are_built_from_the_ledger_when_the_table_is_missing(self):
        self.add_filing("4", FORM4)
        self.add("3", None, outcome="not_attempted")

        rows, status = self.run_ownership(fetches=False)

        self.assertFalse(self.layout.table("fetches").exists())
        self.assertEqual(len(rows), 3)
        self.assertEqual([row["reason"] for row in status], [None, "not_attempted"])


class OwnershipCommandTests(RunOwnershipTestCase):
    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = cli.main([*argv, "--out", str(self.layout.root)])
        return code, stdout.getvalue(), stderr.getvalue()

    def build_root(self) -> None:
        self.add_filing("4", FORM4)
        self.add_filing("3", FORM3)
        self.add_filing("3", ownership_xml("<noSecuritiesOwned>1</noSecuritiesOwned>"))
        self.add_filing("13F-HR", FORM4)
        self.add("5", None, outcome="not_found")
        self.add_filing("10-K", FORM4)
        self.write_tables()

    def test_ownership_prints_records_and_status_per_reason(self):
        self.build_root()

        code, stdout, stderr = self.run_cli("ownership")

        self.assertEqual((code, stderr), (0, ""))
        self.assertEqual(
            stdout,
            "ownership: 7\n"
            "status ok: 2\n"
            "status no securities owned: 1\n"
            "status not_found: 1\n"
            "status parser not built: 1\n",
        )
        steps = [
            json.loads(line)["step"]
            for line in self.layout.runs.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(steps, ["ownership"])

    def test_report_has_an_ownership_section_between_facts_and_the_platform_checks(self):
        self.build_root()
        self.run_cli("ownership")

        report = run_report(self.layout)

        titles = [line for line in report.split("\n") if line.startswith("## ")]
        self.assertEqual(titles[-3:], ["## Facts", "## Ownership", "## Platform checks"])
        self.assertEqual(
            section(report, "Ownership"),
            [
                "- filings in the ownership forms: 5",
                "- records: 7",
                "  - derivative_holding: 2",
                "  - derivative_transaction: 1",
                "  - non_derivative_holding: 2",
                "  - non_derivative_transaction: 2",
                "- filings with records: 2",
                "- filings with no records: 3",
                "  - no securities owned: 1",
                "  - not_found: 1",
                "  - parser not built: 1",
            ],
        )

    def test_report_says_when_a_table_is_missing(self):
        self.build_root()

        self.assertEqual(
            section(run_report(self.layout), "Ownership"), ["- no `ownership_status` table yet"]
        )

        self.run_cli("ownership")
        self.layout.table("ownership").unlink()

        self.assertEqual(
            section(run_report(self.layout), "Ownership"), ["- no `ownership` table yet"]
        )


if __name__ == "__main__":
    unittest.main()
