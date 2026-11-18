import contextlib
import io
import json
import re
import unittest
from dataclasses import asdict, fields, replace
from pathlib import Path

from sec_filing_data import cli
from sec_filing_data.envelope import parse_submission
from sec_filing_data.facts import run_facts
from sec_filing_data.form13f import parse_form13f_table
from sec_filing_data.forms345 import no_securities_owned, parse_form345
from sec_filing_data.ownership import (
    OWNERSHIP_FORMS,
    OwnershipRecord,
    XmlDocument,
    run_ownership,
    xml_document,
)
from sec_filing_data.report import run_report
from sec_filing_data.schedule13 import parse_schedule13
from sec_filing_data.tables import SCHEMAS, read_table
from tests.test_commands import section
from tests.test_envelope import build_document, build_submission
from tests.test_xbrl import PRIMARY, FactsRootTestCase, submission_with, wrapped

FIXTURES = Path(__file__).parent / "fixtures"
FORM4 = (FIXTURES / "form4.xml").read_bytes()
FORM3 = (FIXTURES / "form3.xml").read_bytes()
SCHEDULE13D = (FIXTURES / "schedule13d.xml").read_bytes()
SCHEDULE13G = (FIXTURES / "schedule13g.xml").read_bytes()
INFOTABLE = (FIXTURES / "infotable.xml").read_bytes()

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

# schedule13d.xml is the primary document of the pilot SCHEDULE 13D 0000912282-26-001247 with
# only whole elements removed: authorizedPersons, items 2 to 7 of items1To7, and signatureInfo.
# Both reporting persons stay. The first has a reportingPersonCIK. The second has none.
# schedule13g.xml is the primary document of the pilot SCHEDULE 13G 0000093751-26-000557 with
# only whole elements removed: items 2, 3 and 5 to 10 of items. Both reporting persons, item 4
# (it repeats classPercent) and the signatureInformation elements (they repeat
# reportingPersonName) stay. infotable.xml is the INFORMATION TABLE document of the pilot
# 13F-HR 0001051359-26-000008 with 45 of its 48 infoTable rows removed: its first row and its
# fifth and sixth rows (the fifth has a putCall).
SCHEDULE_KIND = "schedule13_reporting_person"
SCHEDULE13D_ISSUER = {
    "record_kind": SCHEDULE_KIND,
    "issuer_cik": "0001833141",
    "issuer_name": "Cybin Inc.",
    "issuer_cusip": "23256X407",
    "owner_count": 2,
    "security_title": "Common Shares, No Par Value",
}
SCHEDULE13G_ISSUER = {
    "record_kind": SCHEDULE_KIND,
    "issuer_cik": "0001706946",
    "issuer_name": "VIRGIN GALACTIC HOLDINGS INC",
    "issuer_cusip": "92766K403",
    "owner_count": 2,
    "security_title": "COMMON STOCK",
}
PAR = ("FILER", "0001051359", "PAR CAPITAL MANAGEMENT INC")
FORM13F_OWNER = {"owner_cik": "0001051359", "owner_name": "PAR CAPITAL MANAGEMENT INC"}
FORM13F_KIND = "form13f_holding"
COVER_13F = b'<?xml version="1.0"?>\n<edgarSubmission xmlns="urn:example:cover"/>'
UNMAPPED = ("issuer_cusip", "shares_kind", "put_call", "percent_of_class", "value_usd")
OTHER_DOCUMENT = b'<?xml version="1.0"?>\n<otherDocument/>'
BOM = b"\xef\xbb\xbf"


def record(**values) -> OwnershipRecord:
    """An OwnershipRecord with every column that the test does not name set to None."""
    blank = {field.name: None for field in fields(OwnershipRecord)}
    return OwnershipRecord(**(blank | values))


def ownership_xml(body: str, namespace: str = "") -> bytes:
    return f'<?xml version="1.0"?>\n<ownershipDocument{namespace}>\n{body}\n</ownershipDocument>'.encode()


def schedule_xml(body: str) -> bytes:
    return f'<?xml version="1.0"?>\n<edgarSubmission>\n{body}\n</edgarSubmission>'.encode()


def submission_13f(table: bytes | None, *parties: tuple[str, str, str]) -> bytes:
    """A 13F-HR submission: a cover document, the information table (if any), the parties.

    A party is `(role, cik, name)`. The header holds one party block for each.
    """
    header = "CONFORMED SUBMISSION TYPE:\t13F-HR\n" + "".join(
        f"{role}:\n\tCOMPANY DATA:\n\t\tCOMPANY CONFORMED NAME:\t{name}\n"
        f"\t\tCENTRAL INDEX KEY:\t{cik}\n\n"
        for role, cik, name in parties
    )
    documents = [("13F-HR", "primary_doc.xml", wrapped(COVER_13F, "XML"))]
    if table is not None:
        documents.append(("INFORMATION TABLE", "infotable.xml", wrapped(table, "XML")))
    return build_submission(
        header=header,
        documents=tuple(
            build_document(
                text,
                type_line=f"<TYPE>{type_}\n",
                extra=f"<SEQUENCE>{number}\n<FILENAME>{filename}\n",
            )
            for number, (type_, filename, text) in enumerate(documents, start=1)
        ),
    )


_OWNERSHIP_NAMES = SCHEMAS["ownership"].names
RECORD_COLUMNS = _OWNERSHIP_NAMES[2 : _OWNERSHIP_NAMES.index("value_usd") + 1]


class RecordTests(unittest.TestCase):
    def test_fields_are_the_ownership_columns_from_record_kind_to_value_usd(self):
        self.assertEqual([field.name for field in fields(OwnershipRecord)], RECORD_COLUMNS)

    def test_the_provenance_columns_follow_the_record_columns(self):
        self.assertEqual(
            _OWNERSHIP_NAMES[len(RECORD_COLUMNS) + 2 :],
            [
                "source_url",
                "source_sha256",
                "source_document",
                "accepted_at",
                "public_at",
                "public_rule",
                "last_modified_at",
                "fetched_at",
            ],
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


class ParseSchedule13Tests(unittest.TestCase):
    def test_schedule13d_reporting_persons(self):
        records = parse_schedule13(SCHEDULE13D)

        self.assertEqual(
            records,
            [
                record(
                    **SCHEDULE13D_ISSUER,
                    owner_cik="0002118509",
                    owner_name="Glavine Paul",
                    shares="4407456",
                    percent_of_class="5.8",
                ),
                # The second person is filed with reportingPersonNoCIK Y and no reportingPersonCIK.
                record(
                    **SCHEDULE13D_ISSUER,
                    owner_cik=None,
                    owner_name="PLG Family Trust",
                    shares="336204",
                    percent_of_class="0.4",
                ),
            ],
        )

    def test_schedule13g_reporting_persons(self):
        records = parse_schedule13(SCHEDULE13G)

        # A 13G person has no CIK element. Item 4 repeats the first person's classPercent
        # (7.9), and signatureInformation repeats reportingPersonName, so the second record
        # shows that the person's own elements are read, and that the count is of persons.
        self.assertEqual(
            records,
            [
                record(
                    **SCHEDULE13G_ISSUER,
                    owner_cik=None,
                    owner_name="STATE STREET CORPORATION",
                    shares="7931674.00",
                    percent_of_class="7.9",
                ),
                record(
                    **SCHEDULE13G_ISSUER,
                    owner_cik=None,
                    owner_name="SSGA FUNDS MANAGEMENT, INC.",
                    shares="6177392.00",
                    percent_of_class="6.1",
                ),
            ],
        )

    def test_columns_outside_the_mapping_are_null(self):
        unmapped = [
            name
            for name in RECORD_COLUMNS
            if name
            not in {
                "record_kind", "issuer_cik", "issuer_name", "issuer_cusip", "owner_cik",
                "owner_name", "owner_count", "security_title", "shares", "percent_of_class",
            }
        ]  # fmt: skip
        for records in (parse_schedule13(SCHEDULE13D), parse_schedule13(SCHEDULE13G)):
            for row in records:
                self.assertEqual([getattr(row, name) for name in unmapped], [None] * len(unmapped))

    def test_several_issuer_cusips_join_in_document_order(self):
        two = SCHEDULE13D.replace(
            b"</issuerCusipNumber>",
            b"</issuerCusipNumber><issuerCusipNumber> 99999Z999 </issuerCusipNumber>",
        )

        self.assertEqual(
            {r.issuer_cusip for r in parse_schedule13(two)}, {"23256X407;99999Z999"}
        )

    def test_no_issuer_cusip_gives_none(self):
        without = SCHEDULE13G.replace(b"92766K403", b"  ")

        self.assertEqual({r.issuer_cusip for r in parse_schedule13(without)}, {None})

    def test_both_spellings_of_the_issuer_cik_are_read(self):
        # The 13D fixture spells it issuerCIK and the 13G fixture spells it issuerCik.
        self.assertEqual(parse_schedule13(SCHEDULE13D)[0].issuer_cik, "0001833141")
        self.assertEqual(parse_schedule13(SCHEDULE13G)[0].issuer_cik, "0001706946")

    def test_text_is_stripped_and_empty_is_null_and_nothing_is_converted(self):
        xml = schedule_xml(
            "<formData><coverPageHeader><securitiesClassTitle>  </securitiesClassTitle>"
            "<issuerInfo><issuerCik> 0001 </issuerCik><issuerName></issuerName></issuerInfo>"
            "</coverPageHeader><reportingPersons><reportingPersonInfo>"
            "<reportingPersonName>\n N \n</reportingPersonName>"
            "<aggregateAmountOwned> 0012.50 </aggregateAmountOwned>"
            "</reportingPersonInfo></reportingPersons></formData>"
        )

        (row,) = parse_schedule13(xml)

        self.assertEqual(
            (row.issuer_cik, row.issuer_name, row.security_title, row.owner_name),
            ("0001", None, None, "N"),
        )
        self.assertEqual((row.shares, row.percent_of_class, row.owner_cik), ("0012.50", None, None))

    def test_a_document_with_no_reporting_person_gives_no_records(self):
        xml = schedule_xml("<formData><coverPageHeader/></formData>")

        self.assertEqual(parse_schedule13(xml), [])

    def test_elements_match_by_local_name_in_any_namespace(self):
        body = (
            "<s:formData><s:coverPageHeader><s:issuerInfo><s:issuerCIK>1</s:issuerCIK>"
            "</s:issuerInfo></s:coverPageHeader>"
            "<s:reportingPersons><s:reportingPersonInfo><s:reportingPersonName>N"
            "</s:reportingPersonName><s:percentOfClass>5</s:percentOfClass>"
            "</s:reportingPersonInfo></s:reportingPersons></s:formData>"
        )
        xml = f'<s:edgarSubmission xmlns:s="urn:example:s">{body}</s:edgarSubmission>'.encode()

        (row,) = parse_schedule13(xml)

        self.assertEqual(
            (row.issuer_cik, row.owner_name, row.owner_count, row.percent_of_class),
            ("1", "N", 1, "5"),
        )


class ParseForm13fTests(unittest.TestCase):
    OWNER = {"owner_cik": "0001051359", "owner_name": "PAR CAPITAL MANAGEMENT INC"}

    def parse(self, xml: bytes = INFOTABLE) -> list[OwnershipRecord]:
        return parse_form13f_table(xml, **self.OWNER)

    def test_13f_holdings(self):
        common = {
            "record_kind": FORM13F_KIND,
            **FORM13F_OWNER,
            "owner_count": 1,
            "shares_kind": "SH",
        }

        self.assertEqual(
            self.parse(),
            [
                record(
                    **common,
                    issuer_name="AFFIRM HLDGS INC",
                    issuer_cusip="00827B106",
                    security_title="COM CL A",
                    value_usd="326200",
                    shares="4000",
                    put_call=None,
                ),
                record(
                    **common,
                    issuer_name="ALPHABET INC",
                    issuer_cusip="02079K107",
                    security_title="CAP STK CL C",
                    value_usd="883325",
                    shares="2500",
                    put_call="Put",
                ),
                record(
                    **common,
                    issuer_name="ALPHABET INC",
                    issuer_cusip="02079K107",
                    security_title="CAP STK CL C",
                    value_usd="8903916",
                    shares="25200",
                    put_call=None,
                ),
            ],
        )

    def test_13f_prefixed_namespace(self):
        # The SEC files of some filers hold `<ns1:informationTable xmlns:ns1="...">` with an
        # ns1 prefix on every element. This rewrites the fixture the same way, with its own
        # namespace bound to the prefix instead of being the default.
        text = INFOTABLE.decode()
        prefixed = re.sub(r"<(/?)([A-Za-z])", r"<\1ns1:\2", text).replace(
            ' xmlns="', ' xmlns:ns1="', 1
        )
        self.assertIn("<ns1:informationTable ", prefixed)
        self.assertIn("<ns1:putCall>Put</ns1:putCall>", prefixed)
        self.assertNotIn(" xmlns=", prefixed)

        self.assertEqual(self.parse(prefixed.encode()), self.parse())
        self.assertEqual(len(self.parse(prefixed.encode())), 3)

    def test_the_owner_comes_from_the_arguments_and_may_be_none(self):
        rows = parse_form13f_table(INFOTABLE, owner_cik=None, owner_name=None)

        self.assertEqual({(r.owner_cik, r.owner_name, r.owner_count) for r in rows}, {(None, None, 1)})

    def test_columns_outside_the_mapping_are_null(self):
        unmapped = [
            "issuer_cik", "transaction_date", "transaction_code", "acquired_disposed",
            "price_per_share", "shares_after", "direct_indirect", "percent_of_class",
        ]  # fmt: skip
        for row in self.parse():
            self.assertEqual([getattr(row, name) for name in unmapped], [None] * len(unmapped))

    def test_text_is_stripped_and_empty_or_missing_is_null_and_nothing_is_converted(self):
        xml = (
            b"<informationTable><infoTable><nameOfIssuer>  A B  </nameOfIssuer>"
            b"<titleOfClass></titleOfClass><value> 0001.50 </value>"
            b"<shrsOrPrnAmt><sshPrnamt>\n 0007 \n</sshPrnamt></shrsOrPrnAmt>"
            b"<putCall>  </putCall></infoTable>"
            b"<infoTable><cusip>X</cusip></infoTable></informationTable>"
        )

        first, second = self.parse(xml)

        self.assertEqual(
            (first.issuer_name, first.security_title, first.value_usd, first.shares),
            ("A B", None, "0001.50", "0007"),
        )
        self.assertEqual((first.shares_kind, first.put_call, first.issuer_cusip), (None, None, None))
        self.assertEqual(
            (second.issuer_cusip, second.issuer_name, second.shares, second.shares_kind),
            ("X", None, None, None),
        )

    def test_only_the_info_table_children_of_the_root_are_records(self):
        xml = (
            b"<informationTable><other><infoTable/></other><infoTable/><note/>"
            b"<infoTable/></informationTable>"
        )

        self.assertEqual(len(self.parse(xml)), 2)
        self.assertEqual(self.parse(b"<informationTable/>"), [])


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

        self.assertEqual(xml_document(raw, submission, "ownershipDocument").text, FORM4)

    def test_a_document_that_is_not_xml_with_that_root_gives_none(self):
        raw, submission = self.submission(("4", "a.xml", wrapped(OTHER_DOCUMENT, "XML")))
        self.assertIsNone(xml_document(raw, submission, "ownershipDocument"))
        self.assertEqual(xml_document(raw, submission, "otherDocument").text, OTHER_DOCUMENT)

        raw, submission = self.submission()
        self.assertIsNone(xml_document(raw, submission, "ownershipDocument"))

    def test_the_root_matches_by_local_name_in_any_namespace(self):
        default = b'<ownershipDocument xmlns="urn:example:own"/>'
        prefixed = b'<o:ownershipDocument xmlns:o="urn:example:own"/>'
        for text in (default, prefixed):
            with self.subTest(text=text):
                raw, submission = self.submission(("4", "a.xml", wrapped(text, "XML")))
                self.assertEqual(xml_document(raw, submission, "ownershipDocument").text, text)

    def test_text_that_does_not_start_with_an_angle_bracket_is_skipped(self):
        raw, submission = self.submission(
            ("4", "a.xml", "x<ownershipDocument/>\n"),
            ("4", "b.xml", "\n  \n  <ownershipDocument/>\n"),
        )

        self.assertEqual(
            xml_document(raw, submission, "ownershipDocument").text, b"<ownershipDocument/>"
        )

    def test_a_utf8_byte_order_mark_before_the_xml_is_removed(self):
        # The text comes back without the mark, and without any whitespace after it. A
        # byte-order mark and then whitespace and then `<?xml` is not XML as filed.
        for prefix in (BOM, BOM + b"\n  "):
            with self.subTest(prefix=prefix):
                raw, submission = self.submission(("4", "a.xml", wrapped(prefix + FORM4, "XML")))

                self.assertEqual(xml_document(raw, submission, "ownershipDocument").text, FORM4)

    def test_only_one_byte_order_mark_is_removed(self):
        raw, submission = self.submission(("4", "a.xml", wrapped(BOM + BOM + FORM4, "XML")))

        self.assertIsNone(xml_document(raw, submission, "ownershipDocument"))

    def test_a_byte_order_mark_does_not_change_the_other_rules(self):
        doctype = b'<!DOCTYPE ownershipDocument [<!ENTITY x "y">]>\n<ownershipDocument>&x;</ownershipDocument>'
        raw, submission = self.submission(
            ("4", "a.xml", wrapped(BOM + doctype, "XML")),
            ("4", "b.xml", wrapped(BOM + b"<ownershipDocument><unclosed>", "XML")),
            ("4", "c.xml", wrapped(BOM + OTHER_DOCUMENT, "XML")),
            ("4", "d.xml", wrapped(BOM + FORM3, "XML")),
            ("4", "e.xml", wrapped(BOM + FORM4, "XML")),
        )

        self.assertEqual(xml_document(raw, submission, "ownershipDocument").text, FORM3)

    def test_a_doctype_is_refused(self):
        doctype = b'<!DOCTYPE ownershipDocument [<!ENTITY x "y">]>\n<ownershipDocument>&x;</ownershipDocument>'
        raw, submission = self.submission(("4", "a.xml", wrapped(doctype, "XML")))

        self.assertIsNone(xml_document(raw, submission, "ownershipDocument"))

    def test_xml_document_gives_its_filename(self):
        raw, submission = self.submission(
            ("4", "poa.xml", wrapped(OTHER_DOCUMENT, "XML")),
            ("4", "first.xml", wrapped(FORM4, "XML")),
            ("4", "second.xml", wrapped(FORM3, "XML")),
        )

        document = xml_document(raw, submission, "ownershipDocument")

        self.assertEqual(document, XmlDocument("first.xml", FORM4))
        self.assertEqual(
            xml_document(raw, submission, "otherDocument"), XmlDocument("poa.xml", OTHER_DOCUMENT)
        )

    def test_a_document_with_no_filename_gives_none_as_its_filename(self):
        raw = build_submission(
            header="CONFORMED SUBMISSION TYPE:\t4\n",
            documents=(build_document(wrapped(FORM4, "XML"), type_line="<TYPE>4\n"),),
        )

        document = xml_document(raw, parse_submission(raw), "ownershipDocument")

        self.assertEqual(document, XmlDocument(None, FORM4))

    def test_a_document_that_does_not_parse_is_skipped_not_raised(self):
        raw, submission = self.submission(
            ("4", "a.xml", "<ownershipDocument><unclosed>\n"),
            ("4", "b.xml", wrapped(FORM3, "XML")),
        )

        self.assertEqual(xml_document(raw, submission, "ownershipDocument").text, FORM3)


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


def ownership_row(
    accession: str,
    form_type: str,
    row: OwnershipRecord,
    provenance: dict,
    source_document: str | None,
) -> dict:
    return (
        {"accession_number": accession, "form_type": form_type}
        | asdict(row)
        | {"source_document": source_document}
        | provenance
    )


class RunOwnershipTests(RunOwnershipTestCase):
    def test_form4_and_form3_rows_follow_the_sample_and_the_records(self):
        form3 = self.add_filing("3", FORM3)
        form4 = self.add_filing("4", FORM4)

        rows, status = self.run_ownership()

        self.assertEqual(
            rows,
            [
                ownership_row(form3, "3", r, self.provenance(form3), "doc.xml")
                for r in parse_form345(FORM3)
            ]
            + [
                ownership_row(form4, "4", r, self.provenance(form4), "doc.xml")
                for r in parse_form345(FORM4)
            ],
        )
        self.assertEqual(
            status,
            [
                {"accession_number": form3, "form_type": "3", "record_count": 4, "reason": None},
                {"accession_number": form4, "form_type": "4", "record_count": 3, "reason": None},
            ],
        )

    def test_ownership_names_its_source_document(self):
        # The first document is not ownership XML, and the third has the root but comes second.
        raw = submission_with(
            ("4", "poa.xml", wrapped(OTHER_DOCUMENT, "XML")),
            ("4", "form4.xml", wrapped(FORM4, "XML")),
            ("4", "other-form4.xml", wrapped(FORM3, "XML")),
            form="4",
        )
        first = self.add("4", raw)
        second = self.add_filing("4", FORM4)

        rows, _ = self.run_ownership()

        records = parse_form345(FORM4)
        self.assertEqual(len(rows), 2 * len(records))
        self.assertEqual(
            rows,
            [ownership_row(first, "4", r, self.provenance(first), "form4.xml") for r in records]
            + [ownership_row(second, "4", r, self.provenance(second), "doc.xml") for r in records],
        )
        self.assertEqual({row["source_document"] for row in rows[: len(records)]}, {"form4.xml"})
        self.assertEqual(rows[0]["source_url"], self.sampled[0]["url"])
        self.assertEqual(rows[0]["source_sha256"], "sha-1")
        self.assertEqual(rows[-1]["source_sha256"], "sha-2")
        self.assertNotEqual(rows[0]["accepted_at"], rows[-1]["accepted_at"])

    def test_facts_and_ownership_need_filings(self):
        self.add_filing("4", FORM4)
        self.add("10-Q", submission_with(PRIMARY))
        self.write_tables(filings=False)

        for run in (run_facts, run_ownership):
            with self.subTest(run=run.__name__):
                with self.assertRaises(FileNotFoundError) as caught:
                    run(self.layout)
                self.assertIn("envelopes", str(caught.exception))
                self.assertIn("filings", str(caught.exception))

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

    def test_a_byte_order_mark_does_not_hide_the_ownership_document(self):
        marked = self.add_filing("4", BOM + FORM4)

        rows, status = self.run_ownership()

        self.assertEqual(
            rows,
            [
                ownership_row(marked, "4", r, self.provenance(marked), "doc.xml")
                for r in parse_form345(FORM4)
            ],
        )
        self.assertEqual(
            status, [{"accession_number": marked, "form_type": "4", "record_count": 3, "reason": None}]
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
                (schedule, "SCHEDULE 13D", 0, "no ownership XML document"),
                (repeated, "SC 13D/A;SC TO-T/A", 0, "no ownership XML document"),
                # The first part in sorted order that is an ownership form is "4".
                (joined, "4;SC 13D", 3, None),
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
            [(good, "4")] * 3 + [(joined, "4;SC 13D")] * 3 + [(last, "4")] * 4,
        )

    def test_fetches_are_built_from_the_ledger_when_the_table_is_missing(self):
        self.add_filing("4", FORM4)
        self.add("3", None, outcome="not_attempted")

        rows, status = self.run_ownership(fetches=False)

        self.assertFalse(self.layout.table("fetches").exists())
        self.assertEqual(len(rows), 3)
        self.assertEqual([row["reason"] for row in status], [None, "not_attempted"])


class RunScheduleAnd13fTests(RunOwnershipTestCase):
    def add_13f(self, table: bytes | None, *parties: tuple[str, str, str], form="13F-HR") -> str:
        return self.add(form, submission_13f(table, *parties))

    def test_schedule_and_13f_rows_follow_the_sample_and_the_records(self):
        schedule_d = self.add_filing("SCHEDULE 13D", SCHEDULE13D)
        schedule_g = self.add_filing("SCHEDULE 13G/A", SCHEDULE13G)
        old_style = self.add_filing("SC 13G", SCHEDULE13G)
        thirteen_f = self.add_13f(INFOTABLE, PAR)

        rows, status = self.run_ownership()

        self.assertEqual(
            rows,
            [
                ownership_row(schedule_d, "SCHEDULE 13D", r, self.provenance(schedule_d), "doc.xml")
                for r in parse_schedule13(SCHEDULE13D)
            ]
            + [
                ownership_row(
                    schedule_g, "SCHEDULE 13G/A", r, self.provenance(schedule_g), "doc.xml"
                )
                for r in parse_schedule13(SCHEDULE13G)
            ]
            + [
                ownership_row(old_style, "SC 13G", r, self.provenance(old_style), "doc.xml")
                for r in parse_schedule13(SCHEDULE13G)
            ]
            + [
                ownership_row(
                    thirteen_f, "13F-HR", r, self.provenance(thirteen_f), "infotable.xml"
                )
                for r in parse_form13f_table(INFOTABLE, **FORM13F_OWNER)
            ],
        )
        self.assertEqual(
            [(row["form_type"], row["record_count"], row["reason"]) for row in status],
            [
                ("SCHEDULE 13D", 2, None),
                ("SCHEDULE 13G/A", 2, None),
                ("SC 13G", 2, None),
                ("13F-HR", 3, None),
            ],
        )
        self.assertEqual(
            [row["record_kind"] for row in rows],
            [SCHEDULE_KIND] * 6 + [FORM13F_KIND] * 3,
        )

    def test_the_13f_owner_is_the_first_filer_party(self):
        other = ("FILED BY", "0000000007", "NOT THE FILER")
        second = ("FILER", "0000000009", "SECOND FILER")
        with_filer = self.add_13f(INFOTABLE, other, PAR, second)
        no_filer = self.add_13f(INFOTABLE, other, form="13F-HR/A")
        no_party = self.add_13f(INFOTABLE)

        rows, status = self.run_ownership()

        owners = {
            accession: {
                (row["owner_cik"], row["owner_name"], row["owner_count"])
                for row in rows
                if row["accession_number"] == accession
            }
            for accession in (with_filer, no_filer, no_party)
        }
        self.assertEqual(
            owners,
            {
                with_filer: {("0001051359", "PAR CAPITAL MANAGEMENT INC", 1)},
                no_filer: {(None, None, 1)},
                no_party: {(None, None, 1)},
            },
        )
        self.assertEqual([row["record_count"] for row in status], [3, 3, 3])

    def test_the_13f_cover_document_gives_no_records(self):
        cover_only = self.add_13f(None, PAR)

        rows, status = self.run_ownership()

        self.assertEqual(rows, [])
        self.assertEqual(
            [(row["accession_number"], row["record_count"], row["reason"]) for row in status],
            [(cover_only, 0, "no ownership XML document")],
        )

    def test_a_filing_whose_documents_belong_to_another_form_has_no_ownership_document(self):
        self.add_filing("SCHEDULE 13G", INFOTABLE)
        self.add_filing("SC 13D/A", FORM4)
        self.add_13f(SCHEDULE13D, PAR)
        self.add_13f(FORM4, PAR)

        rows, status = self.run_ownership()

        self.assertEqual(rows, [])
        self.assertEqual(
            [row["reason"] for row in status], ["no ownership XML document"] * 4
        )

    def test_a_document_with_no_records_gives_the_reason(self):
        self.add_filing("SCHEDULE 13D", schedule_xml("<formData><coverPageHeader/></formData>"))
        self.add_13f(b"<informationTable/>", PAR)
        # noSecuritiesOwned is a Form 3, 4 and 5 element. It does not explain an empty schedule.
        self.add_filing(
            "SCHEDULE 13G", schedule_xml("<noSecuritiesOwned>1</noSecuritiesOwned>")
        )

        rows, status = self.run_ownership()

        self.assertEqual(rows, [])
        self.assertEqual(
            [(row["record_count"], row["reason"]) for row in status],
            [(0, "no records in the ownership document")] * 3,
        )

    def test_a_joined_form_goes_to_its_first_ownership_part_in_sorted_order(self):
        # "10-K" is not an ownership form, so "SCHEDULE 13D" is the first part that is.
        schedule = self.add_filing("SCHEDULE 13D;10-K", SCHEDULE13D)
        # "13F-HR" sorts before "SCHEDULE 13D".
        thirteen_f = self.add_13f(INFOTABLE, PAR, form="SCHEDULE 13D;13F-HR")
        wrong = self.add_filing("SCHEDULE 13D;13F-HR", SCHEDULE13D)

        rows, status = self.run_ownership()

        self.assertEqual(
            [(row["accession_number"], row["record_count"], row["reason"]) for row in status],
            [
                (schedule, 2, None),
                (thirteen_f, 3, None),
                (wrong, 0, "no ownership XML document"),
            ],
        )
        self.assertEqual(
            {row["record_kind"] for row in rows if row["accession_number"] == thirteen_f},
            {FORM13F_KIND},
        )

    def test_legacy_text_schedule_gives_reason(self):
        text = (
            "SCHEDULE 13D\nUnder the Securities Exchange Act of 1934\n(Amendment No. 3)\n"
            "CUSIP No. 23256X407\n1. NAME OF REPORTING PERSON\n   Glavine Paul\n"
        )
        legacy = self.add(
            "SC 13D/A", submission_with(("SC 13D/A", "d.txt", text), form="SC 13D/A")
        )

        rows, status = self.run_ownership()

        self.assertEqual(rows, [])
        self.assertEqual(
            status,
            [
                {
                    "accession_number": legacy,
                    "form_type": "SC 13D/A",
                    "record_count": 0,
                    "reason": "no ownership XML document",
                }
            ],
        )


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
            "status no ownership XML document: 1\n"
            "status no securities owned: 1\n"
            "status not_found: 1\n",
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
        self.assertEqual(titles[-6:-3], ["## Facts", "## Ownership", "## Platform checks"])
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
                "  - no ownership XML document: 1",
                "  - no securities owned: 1",
                "  - not_found: 1",
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
