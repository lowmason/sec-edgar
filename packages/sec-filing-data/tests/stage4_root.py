"""The Stage 4 test root: a submission builder and the XML parts of its documents.

`submission` gives bytes that `envelope.parse_submission` reads. The XML parts use the element
paths of the live filings, so `amendments.read_declared` and the Stage 3 parsers
(`extract_ownership` for Forms 3, 4 and 5, Schedules 13D and 13G, and Form 13F) read them.
Every CIK is zero-padded text, given by the caller. A value given as None leaves its element
out, as an original filing leaves out the elements of an amendment.
"""

from collections.abc import Sequence

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
