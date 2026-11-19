"""The Stage 4 test root: a submission builder, the XML parts of its documents, and the root.

`submission` gives bytes that `envelope.parse_submission` reads. The XML parts use the element
paths of the live filings, so `amendments.read_declared` and the Stage 3 parsers
(`extract_ownership` for Forms 3, 4 and 5, Schedules 13D and 13G, and Form 13F) read them.
Every CIK is zero-padded text, given by the caller. A value given as None leaves its element
out, as an original filing leaves out the elements of an amendment.

`build_stage4_root` runs every Stage 3 step and every Stage 4 step on a small index, in which
5 sampled filings choose 5 partners, one or more by each rule. `Stage4RootTestCase` builds it
for each test.
"""

import contextlib
import io
import tempfile
from collections.abc import Sequence
from datetime import UTC, datetime
from email.utils import format_datetime
from pathlib import Path
from unittest import mock

from sec_filing_data import cli, index, sample
from sec_filing_data.facts import run_facts
from sec_filing_data.fetch import run_fetch_partners
from sec_filing_data.index import run_index
from sec_filing_data.ownership import run_ownership
from sec_filing_data.partner_tables import run_partner_tables
from sec_filing_data.partners import run_partners
from sec_filing_data.refetches import run_compare_refetches
from sec_filing_data.sample import ARCHIVES, run_sample
from sec_filing_data.submissions import run_envelopes

from tests.test_client import USER_AGENT, FakeResponse
from tests.test_commands import CommandTestCase, FixtureSession
from tests.test_index import FIXTURE, fingerprint, write_zip

_XML_DECLARATION = b"<?xml"


def submission(
    form_type: str,
    *,
    accepted: str,
    filed: str,
    parties: list[tuple[str, str, str]],
    period: str | None = None,
    documents: Sequence[tuple[str, str, bytes]] = (),
) -> bytes:
    """A complete submission file.

    `accepted` is the `ACCEPTANCE-DATETIME` (`YYYYMMDDHHMMSS`), `filed` the `FILED AS OF DATE`
    (`YYYYMMDD`) and `period` the `CONFORMED PERIOD OF REPORT`, left out when None. A party is
    (role, name, padded CIK). A document is (type, filename, text), and a text that starts with
    an XML declaration is wrapped in `<XML>`.
    """
    header = [
        f"<SEC-DOCUMENT>submission.txt : {filed}",
        f"<SEC-HEADER>submission.hdr.sgml : {filed}",
        f"<ACCEPTANCE-DATETIME>{accepted}",
        f"CONFORMED SUBMISSION TYPE:\t{form_type}",
        f"PUBLIC DOCUMENT COUNT:\t\t{len(documents)}",
    ]
    if period is not None:
        header.append(f"CONFORMED PERIOD OF REPORT:\t{period}")
    header.append(f"FILED AS OF DATE:\t\t{filed}")
    for role, name, cik in parties:
        header += [
            "",
            f"{role}:",
            "\tCOMPANY DATA:",
            f"\t\tCOMPANY CONFORMED NAME:\t\t\t{name}",
            f"\t\tCENTRAL INDEX KEY:\t\t\t{cik}",
        ]
    header.append("</SEC-HEADER>")
    body = b"".join(
        _document(sequence, type_, filename, text)
        for sequence, (type_, filename, text) in enumerate(documents, start=1)
    )
    return ("\n".join(header) + "\n").encode() + body + b"</SEC-DOCUMENT>\n"


def _document(sequence: int, type_: str, filename: str, text: bytes) -> bytes:
    if text.lstrip().startswith(_XML_DECLARATION):
        text = b"<XML>\n" + text + b"\n</XML>"
    meta = f"<DOCUMENT>\n<TYPE>{type_}\n<SEQUENCE>{sequence}\n<FILENAME>{filename}\n<TEXT>\n"
    return meta.encode() + text + b"\n</TEXT>\n</DOCUMENT>\n"


def _element(name: str, value: str | None) -> str:
    """`<name>value</name>`, or nothing when `value` is None."""
    return "" if value is None else f"<{name}>{value}</{name}>"


def schedule13_xml(
    form: str, *, previous: str | None = None, amendment_no: str | None = None, issuer_cik: str
) -> bytes:
    """The primary document of a Schedule 13D or 13D/A, with one `reportingPersonInfo`."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<edgarSubmission xmlns="http://www.sec.gov/edgar/schedule13D">
  <headerData>
    <submissionType>{form}</submissionType>
    {_element("previousAccessionNumber", previous)}
    <filerInfo><liveTestFlag>LIVE</liveTestFlag></filerInfo>
  </headerData>
  <formData>
    <coverPageHeader>
      {_element("amendmentNo", amendment_no)}
      <securitiesClassTitle>Common Stock</securitiesClassTitle>
      <issuerInfo>
        <issuerCIK>{issuer_cik}</issuerCIK>
        <issuerCusips><issuerCusipNumber>000000000</issuerCusipNumber></issuerCusips>
        <issuerName>ISSUER CORP</issuerName>
      </issuerInfo>
    </coverPageHeader>
    <reportingPersons>
      <reportingPersonInfo>
        <reportingPersonNoCIK>Y</reportingPersonNoCIK>
        <reportingPersonName>REPORTING PERSON</reportingPersonName>
        <aggregateAmountOwned>1000</aggregateAmountOwned>
        <percentOfClass>5.1</percentOfClass>
      </reportingPersonInfo>
    </reportingPersons>
  </formData>
</edgarSubmission>""".encode()


def form_d_xml(*, previous: str | None = None) -> bytes:
    """The primary document of a Form D, or of a Form D/A when `previous` is given."""
    form, is_amendment = ("D", "false") if previous is None else ("D/A", "true")
    return f"""<?xml version="1.0"?>
<edgarSubmission>
  <schemaVersion>X0708</schemaVersion>
  <submissionType>{form}</submissionType>
  <testOrLive>LIVE</testOrLive>
  <primaryIssuer><entityName>ISSUER FUND LP</entityName></primaryIssuer>
  <offeringData>
    <typeOfFiling>
      <newOrAmendment>
        <isAmendment>{is_amendment}</isAmendment>
        {_element("previousAccessionNumber", previous)}
      </newOrAmendment>
      <dateOfFirstSale><value>2026-07-01</value></dateOfFirstSale>
    </typeOfFiling>
  </offeringData>
</edgarSubmission>""".encode()


def form345_xml(
    form: str, *, original_date: str | None = None, issuer_cik: str, owner_ciks: Sequence[str]
) -> bytes:
    """The `ownershipDocument` of a Form 3, 4 or 5, or an amendment of one, with one
    `reportingOwner` for each owner CIK and one `nonDerivativeTransaction`."""
    owners = "".join(
        f"""
  <reportingOwner>
    <reportingOwnerId>
      <rptOwnerCik>{cik}</rptOwnerCik>
      <rptOwnerName>OWNER {number}</rptOwnerName>
    </reportingOwnerId>
  </reportingOwner>"""
        for number, cik in enumerate(owner_ciks, start=1)
    )
    return f"""<?xml version="1.0"?>
<ownershipDocument>
  <schemaVersion>X0609</schemaVersion>
  <documentType>{form}</documentType>
  <periodOfReport>2026-08-03</periodOfReport>
  {_element("dateOfOriginalSubmission", original_date)}
  <issuer>
    <issuerCik>{issuer_cik}</issuerCik>
    <issuerName>ISSUER CORP</issuerName>
    <issuerTradingSymbol>ISS</issuerTradingSymbol>
  </issuer>{owners}
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <securityTitle><value>Common Stock</value></securityTitle>
      <transactionDate><value>2026-08-03</value></transactionDate>
      <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
      <transactionAmounts>
        <transactionShares><value>100</value></transactionShares>
        <transactionPricePerShare><value>10.00</value></transactionPricePerShare>
        <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
      </transactionAmounts>
      <postTransactionAmounts>
        <sharesOwnedFollowingTransaction><value>1100</value></sharesOwnedFollowingTransaction>
      </postTransactionAmounts>
      <ownershipNature>
        <directOrIndirectOwnership><value>D</value></directOrIndirectOwnership>
      </ownershipNature>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>""".encode()


def form13f_cover_xml(
    form: str,
    *,
    amendment_no: str | None = None,
    amendment_type: str | None = None,
    period_of_report: str = "06-30-2026",
) -> bytes:
    """The cover document of a Form 13F-HR or 13F-HR/A. `period_of_report` is `MM-DD-YYYY`,
    as the XML writes it."""
    is_amendment = "false" if amendment_no is None else "true"
    info = None if amendment_type is None else _element("amendmentType", amendment_type)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<edgarSubmission xmlns="http://www.sec.gov/edgar/thirteenffiler">
  <headerData>
    <submissionType>{form}</submissionType>
    <filerInfo>
      <liveTestFlag>LIVE</liveTestFlag>
      <periodOfReport>{period_of_report}</periodOfReport>
    </filerInfo>
  </headerData>
  <formData>
    <coverPage>
      <reportCalendarOrQuarter>{period_of_report}</reportCalendarOrQuarter>
      <isAmendment>{is_amendment}</isAmendment>
      {_element("amendmentNo", amendment_no)}
      {_element("amendmentInfo", info)}
      <filingManager><name>MANAGER LLC</name></filingManager>
      <reportType>13F HOLDINGS REPORT</reportType>
    </coverPage>
  </formData>
</edgarSubmission>""".encode()


def infotable_xml() -> bytes:
    """The information table of a Form 13F, with one `infoTable`."""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
  <infoTable>
    <nameOfIssuer>EXAMPLE CORP</nameOfIssuer>
    <titleOfClass>COM</titleOfClass>
    <cusip>000000000</cusip>
    <value>1000</value>
    <shrsOrPrnAmt><sshPrnamt>100</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt>
    <investmentDiscretion>SOLE</investmentDiscretion>
  </infoTable>
</informationTable>"""


# The accessions of the root. Each sampled filing finds its partners as the comments say.
SAMPLED_D_A = "0000000041-26-000002"  # D/A: its previousAccessionNumber names PARTNER_D (rule 1)
PARTNER_D = "0000000041-26-000001"
SAMPLED_4_A = "0000000051-26-000009"  # 4/A: date, issuer and owner find PARTNER_4 (rule 2)
PARTNER_4 = "0000000051-26-000003"
SAMPLED_13D = "0000000061-26-000001"  # SCHEDULE 13D: two candidate amendments (rule 3)
PARTNER_13D_A1 = "0000000061-26-000002"  # names SAMPLED_13D
PARTNER_13D_A2 = "0000000061-26-000003"  # names PARTNER_13D_A1
SAMPLED_13F = "0000000071-26-000001"  # 13F-HR: one candidate amendment (rule 3)
PARTNER_13F_A = "0000000071-26-000002"  # same filer and period
SAMPLED_8K_A = "0000000081-26-000001"  # 8-K/A with no XML document: it declares nothing
UNRELATED_10K = "0000000091-26-000001"  # in the index only: the draw drops it, no rule takes it

# In accession order.
SAMPLED = (SAMPLED_D_A, SAMPLED_4_A, SAMPLED_13D, SAMPLED_13F, SAMPLED_8K_A)
PARTNERS = (PARTNER_D, PARTNER_4, PARTNER_13D_A1, PARTNER_13D_A2, PARTNER_13F_A)

_COMPANIES = {
    41: "EXAMPLE FUND LP",
    51: "EXAMPLE ISSUER INC",
    52: "EXAMPLE OWNER",
    61: "TARGET CORP",
    62: "ACTIVIST PARTNERS LP",
    71: "EXAMPLE MANAGER LLC",
    81: "EXAMPLE EIGHT CORP",
    91: "UNRELATED CORP",
}

# Each accession of the index: its form type, its date filed and its CIKs. The index lists it
# once for each CIK, in this order, so its first CIK names its file and its URL.
INDEX_FILINGS: dict[str, tuple[str, str, tuple[int, ...]]] = {
    PARTNER_D: ("D", "2026-07-06", (41,)),
    SAMPLED_D_A: ("D/A", "2026-07-20", (41,)),
    PARTNER_4: ("4", "2026-08-04", (51, 52)),
    SAMPLED_4_A: ("4/A", "2026-08-06", (51, 52)),
    SAMPLED_13D: ("SCHEDULE 13D", "2026-07-14", (61, 62)),
    PARTNER_13D_A1: ("SCHEDULE 13D/A", "2026-08-11", (61, 62)),
    PARTNER_13D_A2: ("SCHEDULE 13D/A", "2026-09-02", (61, 62)),
    SAMPLED_13F: ("13F-HR", "2026-08-14", (71,)),
    PARTNER_13F_A: ("13F-HR/A", "2026-09-15", (71,)),
    SAMPLED_8K_A: ("8-K/A", "2026-09-22", (81,)),
    UNRELATED_10K: ("10-K", "2026-08-20", (91,)),
}


def padded(cik: int) -> str:
    """A CIK as the XML and the header write it: zero-padded to 10 digits."""
    return f"{cik:010d}"


def url(accession: str) -> str:
    """The URL of an accession's submission file, from its first index row."""
    _, _, ciks = INDEX_FILINGS[accession]
    return f"{ARCHIVES}edgar/data/{ciks[0]}/{accession}.txt"


def _index_text() -> str:
    """The `master.idx` text: the header block of the shared fixture, then one row for each
    CIK of each accession."""
    lines = FIXTURE.read_text(encoding="utf-8").split("\n")
    dashes_at = lines.index(index.HEADER) + 1
    rows = [
        f"{cik}|{_COMPANIES[cik]}|{form_type}|{filed}|edgar/data/{cik}/{accession}.txt"
        for accession, (form_type, filed, ciks) in INDEX_FILINGS.items()
        for cik in ciks
    ]
    return "\n".join([*lines[: dashes_at + 1], *rows]) + "\n"


INDEX_TEXT = _index_text()


def _filing(
    accession: str,
    accepted: str,
    roles: Sequence[str],
    documents: Sequence[tuple[str, str, bytes]],
    period: str | None = None,
) -> bytes:
    """The submission file of an accession of INDEX_FILINGS, filed on its date filed.

    `accepted` is the New York time of acceptance on that day (`HHMMSS`). Each CIK of the
    accession is one party, with the role at the same place in `roles`.
    """
    form_type, filed, ciks = INDEX_FILINGS[accession]
    day = filed.replace("-", "")
    return submission(
        form_type,
        accepted=day + accepted,
        filed=day,
        parties=[
            (role, _COMPANIES[cik], padded(cik)) for role, cik in zip(roles, ciks, strict=True)
        ],
        period=period,
        documents=documents,
    )


_FORM4_PARTIES = ("ISSUER", "REPORTING-OWNER")
_SCHEDULE_PARTIES = ("SUBJECT COMPANY", "FILED BY")
_PERIOD_13F = "20260630"


def _form4(form: str, original_date: str | None = None) -> bytes:
    return form345_xml(
        form, original_date=original_date, issuer_cik=padded(51), owner_ciks=[padded(52)]
    )


def _schedule13(form: str, previous: str | None = None, amendment_no: str | None = None) -> bytes:
    return schedule13_xml(form, previous=previous, amendment_no=amendment_no, issuer_cik=padded(61))


# Each filing is accepted between 06:00 and 22:00 New York time on its date filed, so its
# `public_at` is its `accepted_at`. Each original is accepted before its amendment.
SUBMISSIONS: dict[str, bytes] = {
    PARTNER_D: _filing(PARTNER_D, "100000", ["FILER"], [("D", "primary_doc.xml", form_d_xml())]),
    SAMPLED_D_A: _filing(
        SAMPLED_D_A,
        "110000",
        ["FILER"],
        [("D/A", "primary_doc.xml", form_d_xml(previous=PARTNER_D))],
    ),
    PARTNER_4: _filing(PARTNER_4, "163000", _FORM4_PARTIES, [("4", "form4.xml", _form4("4"))]),
    SAMPLED_4_A: _filing(
        SAMPLED_4_A,
        "120000",
        _FORM4_PARTIES,
        [("4/A", "form4a.xml", _form4("4/A", original_date="2026-08-04"))],
    ),
    SAMPLED_13D: _filing(
        SAMPLED_13D,
        "090000",
        _SCHEDULE_PARTIES,
        [("SCHEDULE 13D", "primary_doc.xml", _schedule13("SCHEDULE 13D"))],
    ),
    PARTNER_13D_A1: _filing(
        PARTNER_13D_A1,
        "140000",
        _SCHEDULE_PARTIES,
        [("SCHEDULE 13D/A", "primary_doc.xml", _schedule13("SCHEDULE 13D/A", SAMPLED_13D, "1"))],
    ),
    PARTNER_13D_A2: _filing(
        PARTNER_13D_A2,
        "153000",
        _SCHEDULE_PARTIES,
        [
            (
                "SCHEDULE 13D/A",
                "primary_doc.xml",
                _schedule13("SCHEDULE 13D/A", PARTNER_13D_A1, "2"),
            )
        ],
    ),
    SAMPLED_13F: _filing(
        SAMPLED_13F,
        "160523",
        ["FILER"],
        [
            ("13F-HR", "primary_doc.xml", form13f_cover_xml("13F-HR")),
            ("INFORMATION TABLE", "infotable.xml", infotable_xml()),
        ],
        period=_PERIOD_13F,
    ),
    PARTNER_13F_A: _filing(
        PARTNER_13F_A,
        "101500",
        ["FILER"],
        [
            (
                "13F-HR/A",
                "primary_doc.xml",
                form13f_cover_xml("13F-HR/A", amendment_no="1", amendment_type="NEW HOLDINGS"),
            ),
            ("INFORMATION TABLE", "infotable.xml", infotable_xml()),
        ],
        period=_PERIOD_13F,
    ),
    SAMPLED_8K_A: _filing(
        SAMPLED_8K_A,
        "170000",
        ["FILER"],
        [("8-K/A", "form8ka.htm", b"<html><body>An amended current report.</body></html>")],
    ),
}


def _http_date(month: int, day: int, hour: int, minute: int, second: int) -> str:
    """A UTC time of 2026 as a `Last-Modified` header writes it, with its weekday."""
    moment = datetime(2026, month, day, hour, minute, second, tzinfo=UTC)
    return format_datetime(moment, usegmt=True)


# The `Last-Modified` header of each fetched accession. Each is at or after the filing's
# `public_at` (New York is UTC-4 in these months) and before `index.INDEX_LAST_MODIFIED_AT`,
# and no two are equal. PARTNER_D's copy is last modified after SAMPLED_D_A's, so that pair's
# amendment answers first. In every other pair, the original is last modified first.
LAST_MODIFIED: dict[str, str] = {
    PARTNER_D: _http_date(7, 21, 9, 0, 0),  # accepted 2026-07-06 14:00:00Z
    SAMPLED_D_A: _http_date(7, 20, 15, 0, 30),  # accepted 2026-07-20 15:00:00Z
    PARTNER_4: _http_date(8, 4, 20, 30, 45),  # accepted 2026-08-04 20:30:00Z
    SAMPLED_4_A: _http_date(8, 6, 16, 0, 20),  # accepted 2026-08-06 16:00:00Z
    SAMPLED_13D: _http_date(7, 14, 13, 0, 15),  # accepted 2026-07-14 13:00:00Z
    PARTNER_13D_A1: _http_date(8, 11, 18, 0, 25),  # accepted 2026-08-11 18:00:00Z
    PARTNER_13D_A2: _http_date(9, 2, 19, 30, 10),  # accepted 2026-09-02 19:30:00Z
    SAMPLED_13F: _http_date(8, 14, 20, 5, 40),  # accepted 2026-08-14 20:05:23Z
    PARTNER_13F_A: _http_date(9, 15, 14, 15, 30),  # accepted 2026-09-15 14:15:00Z
    SAMPLED_8K_A: _http_date(9, 22, 21, 0, 5),  # accepted 2026-09-22 21:00:00Z
}

_REAL_DRAW = sample.draw_sample


def _draw_sampled(index_rows: list[dict], *args, **kwargs) -> list[dict]:
    """The real draw, with only the rows of SAMPLED, in draw order, numbered again from 1 (C16).

    The index has fewer than 500 accessions, so the real draw takes every one of them.
    """
    kept = [
        row
        for row in _REAL_DRAW(index_rows, *args, **kwargs)
        if row["accession_number"] in SAMPLED
    ]
    return [{**row, "draw": draw} for draw, row in enumerate(kept, start=1)]


def _session(accessions: Sequence[str], failing: frozenset[str] = frozenset()) -> FixtureSession:
    """Serves each accession's submission file with its `Last-Modified` header, or a 404 for
    an accession in `failing`."""
    return FixtureSession(
        {
            url(accession): (
                FakeResponse(404, [b"not found"])
                if accession in failing
                else FakeResponse(
                    200, [SUBMISSIONS[accession]], {"Last-Modified": LAST_MODIFIED[accession]}
                )
            )
            for accession in accessions
        }
    )


def build_stage4_root(case: CommandTestCase, *, failing: frozenset[str] = frozenset()) -> Path:
    """Run every Stage 3 step and every Stage 4 step on `case.layout`. Give the zip path.

    The partner fetch gets a 404 for each partner in `failing`. `index.INDEX_SHA256`,
    `INDEX_SIZE` and `sample.draw_sample` stay patched until the test ends, so `rebuild` and
    `verify` read the same index and draw the same sample.
    """
    folder = tempfile.TemporaryDirectory()
    case.addCleanup(folder.cleanup)
    zip_path = write_zip(Path(folder.name), INDEX_TEXT)
    sha256, size = fingerprint(zip_path)
    case.enterContext(mock.patch.object(index, "INDEX_SHA256", sha256))
    case.enterContext(mock.patch.object(index, "INDEX_SIZE", size))
    case.enterContext(mock.patch.object(sample, "draw_sample", _draw_sampled))
    layout = case.layout
    run_index(layout, zip_path)
    run_sample(layout)
    sampled = _session(SAMPLED)
    case.assertEqual(case.fetch(sampled), 0)
    # A URL with no scripted reply gets the 13F fixture, so each reply must be used.
    case.assertEqual(sampled.replies, {})
    for step in (run_envelopes, run_facts, run_ownership, run_compare_refetches):
        case.assertEqual(step(layout), 0)
    run_partners(layout)
    partners = _session(PARTNERS, failing)
    code = run_fetch_partners(
        layout,
        user_agent=USER_AGENT,
        session=partners,
        monotonic=case.clock.monotonic,
        sleep=case.clock.sleep,
    )
    case.assertEqual(code, 0)
    case.assertEqual(partners.replies, {})
    run_partner_tables(layout)
    return zip_path


class Stage4RootTestCase(CommandTestCase):
    """A root from `build_stage4_root`, with no failing partner. `zip_path` is its zip."""

    def setUp(self) -> None:
        super().setUp()
        self.zip_path = build_stage4_root(self)

    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        """Run one command on the root. Give its exit code, stdout and stderr."""
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = cli.main([*argv, "--out", str(self.layout.root)])
        return code, stdout.getvalue(), stderr.getvalue()
