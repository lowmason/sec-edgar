"""Read the records of one Form 3, 4 or 5 `ownershipDocument`, as filed.

One record per `nonDerivativeTransaction`, `nonDerivativeHolding`, `derivativeTransaction`
and `derivativeHolding`, in document order. Elements are matched by local name. A value is
the element's text with surrounding whitespace stripped. A missing or empty element gives
None. There is no numeric conversion.
"""

import xml.etree.ElementTree as ET

from sec_filing_data.ownership import OwnershipRecord, element_at, local_name, text_at

RECORD_KINDS = {
    "nonDerivativeTransaction": "non_derivative_transaction",
    "nonDerivativeHolding": "non_derivative_holding",
    "derivativeTransaction": "derivative_transaction",
    "derivativeHolding": "derivative_holding",
}
_TRUE = ("1", "true")


def parse_form345(xml: bytes) -> list[OwnershipRecord]:
    """The records of an `ownershipDocument`, in document order.

    The owner is the first `reportingOwner`, and `owner_count` counts them. The columns
    that a Form 3, 4 or 5 does not hold (`issuer_cusip`, `shares_kind`, `put_call`,
    `percent_of_class`, `value_usd`) are None. A holding has no transaction columns.
    Raises ET.ParseError for XML that does not parse.
    """
    root = ET.fromstring(xml)
    issuer = element_at(root, "issuer")
    owners = [child for child in root if local_name(child.tag) == "reportingOwner"]
    owner_id = element_at(owners[0], "reportingOwnerId") if owners else None
    return [
        OwnershipRecord(
            record_kind=RECORD_KINDS[local_name(row.tag)],
            issuer_cik=text_at(issuer, "issuerCik"),
            issuer_name=text_at(issuer, "issuerName"),
            issuer_cusip=None,
            owner_cik=text_at(owner_id, "rptOwnerCik"),
            owner_name=text_at(owner_id, "rptOwnerName"),
            owner_count=len(owners),
            security_title=text_at(row, "securityTitle", "value"),
            shares=text_at(row, "transactionAmounts", "transactionShares", "value"),
            shares_kind=None,
            put_call=None,
            transaction_date=text_at(row, "transactionDate", "value"),
            transaction_code=text_at(row, "transactionCoding", "transactionCode"),
            acquired_disposed=text_at(
                row, "transactionAmounts", "transactionAcquiredDisposedCode", "value"
            ),
            price_per_share=text_at(row, "transactionAmounts", "transactionPricePerShare", "value"),
            shares_after=text_at(
                row, "postTransactionAmounts", "sharesOwnedFollowingTransaction", "value"
            ),
            direct_indirect=text_at(row, "ownershipNature", "directOrIndirectOwnership", "value"),
            percent_of_class=None,
            value_usd=None,
        )
        for row in root.iter()
        if local_name(row.tag) in RECORD_KINDS
    ]


def no_securities_owned(xml: bytes) -> bool:
    """True when the document's `noSecuritiesOwned` flag is `1` or `true`."""
    return text_at(ET.fromstring(xml), "noSecuritiesOwned") in _TRUE
