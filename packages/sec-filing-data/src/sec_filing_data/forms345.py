"""Read the records of one Form 3, 4 or 5 `ownershipDocument`, as filed.

One record per `nonDerivativeTransaction`, `nonDerivativeHolding`, `derivativeTransaction`
and `derivativeHolding`, in document order. Elements are matched by local name. A value is
the element's text with surrounding whitespace stripped. A missing or empty element gives
None. There is no numeric conversion.
"""

import xml.etree.ElementTree as ET

from sec_filing_data.ownership import OwnershipRecord, local_name

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
    issuer = _child(root, "issuer")
    owners = [child for child in root if local_name(child.tag) == "reportingOwner"]
    owner_id = _child(owners[0], "reportingOwnerId") if owners else None
    return [
        OwnershipRecord(
            record_kind=RECORD_KINDS[local_name(row.tag)],
            issuer_cik=_text(issuer, "issuerCik"),
            issuer_name=_text(issuer, "issuerName"),
            issuer_cusip=None,
            owner_cik=_text(owner_id, "rptOwnerCik"),
            owner_name=_text(owner_id, "rptOwnerName"),
            owner_count=len(owners),
            security_title=_text(row, "securityTitle", "value"),
            shares=_text(row, "transactionAmounts", "transactionShares", "value"),
            shares_kind=None,
            put_call=None,
            transaction_date=_text(row, "transactionDate", "value"),
            transaction_code=_text(row, "transactionCoding", "transactionCode"),
            acquired_disposed=_text(
                row, "transactionAmounts", "transactionAcquiredDisposedCode", "value"
            ),
            price_per_share=_text(row, "transactionAmounts", "transactionPricePerShare", "value"),
            shares_after=_text(
                row, "postTransactionAmounts", "sharesOwnedFollowingTransaction", "value"
            ),
            direct_indirect=_text(row, "ownershipNature", "directOrIndirectOwnership", "value"),
            percent_of_class=None,
            value_usd=None,
        )
        for row in root.iter()
        if local_name(row.tag) in RECORD_KINDS
    ]


def no_securities_owned(xml: bytes) -> bool:
    """True when the document's `noSecuritiesOwned` flag is `1` or `true`."""
    return _text(ET.fromstring(xml), "noSecuritiesOwned") in _TRUE


def _child(parent: ET.Element | None, *path: str) -> ET.Element | None:
    """The element at `path`, each step the first direct child with that local name."""
    for name in path:
        if parent is None:
            return None
        parent = next((child for child in parent if local_name(child.tag) == name), None)
    return parent


def _text(parent: ET.Element | None, *path: str) -> str | None:
    element = _child(parent, *path)
    if element is None:
        return None
    return (element.text or "").strip() or None
