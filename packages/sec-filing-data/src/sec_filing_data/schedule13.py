"""Read the reporting-person records of one Schedule 13D or 13G document, as filed.

The root is `edgarSubmission`. One record per reporting person, in document order. The 13D
and 13G schemas name some elements differently, and a name here is a 13D name or a 13G name:

- the issuer's CIK is `issuerCIK` (13D) or `issuerCik` (13G), under `coverPageHeader/issuerInfo`;
- a person is a `reportingPersonInfo` (13D) or a `coverPageHeaderReportingPersonDetails` (13G);
- the shares are `aggregateAmountOwned` (13D) or
  `reportingPersonBeneficiallyOwnedAggregateNumberOfShares` (13G);
- the percent of class is `percentOfClass` (13D) or `classPercent` (13G).

Elements are matched by local name. A value is the element's text with surrounding
whitespace stripped. A missing or empty element gives None. There is no numeric conversion.
"""

import xml.etree.ElementTree as ET

from sec_filing_data.ownership import OwnershipRecord, element_at, local_name, text_at

RECORD_KIND = "schedule13_reporting_person"
PERSON_ELEMENTS = frozenset({"reportingPersonInfo", "coverPageHeaderReportingPersonDetails"})
ISSUER_CIK_ELEMENTS = ("issuerCIK", "issuerCik")
SHARES_ELEMENTS = (
    "aggregateAmountOwned",
    "reportingPersonBeneficiallyOwnedAggregateNumberOfShares",
)
PERCENT_ELEMENTS = ("percentOfClass", "classPercent")
CUSIP_SEPARATOR = ";"


def parse_schedule13(xml: bytes) -> list[OwnershipRecord]:
    """The records of a Schedule 13D or 13G `edgarSubmission`, one for each reporting person.

    The issuer and the security come from `formData/coverPageHeader`. A person's own child
    elements give the rest, because a 13G repeats `classPercent` in `items`. The owner CIK
    is None for a person with no `reportingPersonCIK` (every 13G person), and `owner_count`
    counts the persons. A filing with several issuer CUSIPs joins them with `;`. The columns
    that a schedule does not hold are None. Raises ET.ParseError for XML that does not parse.
    """
    root = ET.fromstring(xml)
    cover = element_at(root, "formData", "coverPageHeader")
    issuer = element_at(cover, "issuerInfo")
    cusip = _joined_cusips(issuer)
    persons = [element for element in root.iter() if local_name(element.tag) in PERSON_ELEMENTS]
    return [
        OwnershipRecord(
            record_kind=RECORD_KIND,
            issuer_cik=_first_text(issuer, ISSUER_CIK_ELEMENTS),
            issuer_name=text_at(issuer, "issuerName"),
            issuer_cusip=cusip,
            owner_cik=text_at(person, "reportingPersonCIK"),
            owner_name=text_at(person, "reportingPersonName"),
            owner_count=len(persons),
            security_title=text_at(cover, "securitiesClassTitle"),
            shares=_first_text(person, SHARES_ELEMENTS),
            shares_kind=None,
            put_call=None,
            transaction_date=None,
            transaction_code=None,
            acquired_disposed=None,
            price_per_share=None,
            shares_after=None,
            direct_indirect=None,
            percent_of_class=_first_text(person, PERCENT_ELEMENTS),
            value_usd=None,
        )
        for person in persons
    ]


def _first_text(parent: ET.Element | None, names: tuple[str, ...]) -> str | None:
    """The text of the first of the direct children `names` that has any, or None."""
    return next((value for name in names if (value := text_at(parent, name)) is not None), None)


def _joined_cusips(issuer: ET.Element | None) -> str | None:
    """The `issuerCusipNumber` values under `issuerCusips`, in document order, joined with `;`."""
    cusips = element_at(issuer, "issuerCusips")
    if cusips is None:
        return None
    numbers = (
        (number.text or "").strip()
        for number in cusips
        if local_name(number.tag) == "issuerCusipNumber"
    )
    return CUSIP_SEPARATOR.join(number for number in numbers if number) or None
