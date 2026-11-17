"""Read the holdings of one Form 13F `informationTable`, as filed.

One record per `infoTable` child of the root, in document order. Elements are matched by
local name, so a filer's `ns1:` prefix does not matter. A value is the element's text with
surrounding whitespace stripped. A missing or empty element gives None. There is no
numeric conversion.
"""

import xml.etree.ElementTree as ET

from sec_filing_data.ownership import OwnershipRecord, local_name, text_at

RECORD_KIND = "form13f_holding"


def parse_form13f_table(
    xml: bytes, *, owner_cik: str | None, owner_name: str | None
) -> list[OwnershipRecord]:
    """The records of an `informationTable`, one for each `infoTable`.

    The table does not name its filer, so the caller gives the owner: the 13F filing
    manager. `owner_count` is 1. `issuer_cik` and the columns that a holding does not
    hold are None. Raises ET.ParseError for XML that does not parse.
    """
    return [
        OwnershipRecord(
            record_kind=RECORD_KIND,
            issuer_cik=None,
            issuer_name=text_at(row, "nameOfIssuer"),
            issuer_cusip=text_at(row, "cusip"),
            owner_cik=owner_cik,
            owner_name=owner_name,
            owner_count=1,
            security_title=text_at(row, "titleOfClass"),
            shares=text_at(row, "shrsOrPrnAmt", "sshPrnamt"),
            shares_kind=text_at(row, "shrsOrPrnAmt", "sshPrnamtType"),
            put_call=text_at(row, "putCall"),
            transaction_date=None,
            transaction_code=None,
            acquired_disposed=None,
            price_per_share=None,
            shares_after=None,
            direct_indirect=None,
            percent_of_class=None,
            value_usd=text_at(row, "value"),
        )
        for row in ET.fromstring(xml)
        if local_name(row.tag) == "infoTable"
    ]
