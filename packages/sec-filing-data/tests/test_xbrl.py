import contextlib
import datetime
import io
import json
import tempfile
import unittest
from pathlib import Path

from sec_filing_data import cli
from sec_filing_data.envelope import Document
from sec_filing_data.facts import FACT_FORMS, run_facts
from sec_filing_data.layout import Layout
from sec_filing_data.report import run_report
from sec_filing_data.tables import SCHEMAS, read_table, write_table
from sec_filing_data.xbrl import Fact, XbrlError, find_instance, parse_instance
from tests.test_commands import section
from tests.test_envelope import build_document, build_submission

FIXTURE_BYTES = (Path(__file__).parent / "fixtures" / "instance-10q.xml").read_bytes()

# The fixture is trimmed from the SEC-extracted instance of the pilot 10-Q 0001193125-26-322462
# (vicr-20260630_htm.xml): its root with every namespace declaration and its schemaRef, two
# contexts, two units and four facts, with ids, prefixes and values as filed. Two facts point at a kept context
# that the filed fact did not use: dei:DocumentType (filed in a duration context with no
# member) and the par value per share (filed in an instant context with a member).
INSTANT = "C_a5fd0091-0318-4ca3-9be0-e767d6ca06b0"
DURATION = "C_801f4d44-448d-4a43-b210-3deb821d73d3"
EUROPE = "srt:StatementGeographicalAxis=srt:EuropeMember"
REVENUE = "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"

FIXTURE_FACTS = [
    Fact(
        concept="us-gaap:CommitmentsAndContingencies",
        value=None,
        unit="iso4217:USD",
        period_start=None,
        period_end=None,
        period_instant="2026-06-30",
        decimals=None,
        context_id=INSTANT,
        dimensions=None,
        is_nil=True,
    ),
    Fact(
        concept="dei:DocumentType",
        value="10-Q",
        unit=None,
        period_start="2026-04-01",
        period_end="2026-06-30",
        period_instant=None,
        decimals=None,
        context_id=DURATION,
        dimensions=EUROPE,
        is_nil=False,
    ),
    Fact(
        concept="us-gaap:CommonStockParOrStatedValuePerShare",
        value="0.01",
        unit="iso4217:USD/shares",
        period_start=None,
        period_end=None,
        period_instant="2026-06-30",
        decimals="2",
        context_id=INSTANT,
        dimensions=None,
        is_nil=False,
    ),
    Fact(
        concept=REVENUE,
        value="16214000",
        unit="iso4217:USD",
        period_start="2026-04-01",
        period_end="2026-06-30",
        period_instant=None,
        decimals="-3",
        context_id=DURATION,
        dimensions=EUROPE,
        is_nil=False,
    ),
]

INSTANCE_NAMESPACE = "http://www.xbrl.org/2003/instance"
# The elements of the instance namespace that the fixture uses.
XBRLI_TAGS = (
    "context",
    "entity",
    "identifier",
    "segment",
    "period",
    "startDate",
    "endDate",
    "instant",
    "unit",
    "divide",
    "unitNumerator",
    "unitDenominator",
    "measure",
)


def instance(body: str) -> bytes:
    """A small instance: the XBRL namespace is the default one, `a:` and `b:` are concept prefixes."""
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<xbrl xmlns="{INSTANCE_NAMESPACE}" xmlns:a="urn:a" xmlns:b="urn:b"'
        ' xmlns:xbrldi="http://xbrl.org/2006/xbrldi"'
        ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
        f"{body}\n</xbrl>"
    ).encode()


def context(
    context_id: str, *, instant: str | None = "2026-06-30", period: str = "", members: str = ""
) -> str:
    period = period or f"<instant>{instant}</instant>"
    segment = f"<segment>{members}</segment>" if members else ""
    return (
        f'<context id="{context_id}"><entity><identifier scheme="s">1</identifier>{segment}'
        f"</entity><period>{period}</period></context>"
    )


def facts_of(body: str) -> list[Fact]:
    return parse_instance(instance(body))


class FixtureTests(unittest.TestCase):
    def test_parses_numeric_text_and_nil_facts(self):
        facts = parse_instance(FIXTURE_BYTES)

        self.assertEqual(
            [(f.concept, f.value, f.decimals, f.is_nil) for f in facts],
            [
                ("us-gaap:CommitmentsAndContingencies", None, None, True),
                ("dei:DocumentType", "10-Q", None, False),
                ("us-gaap:CommonStockParOrStatedValuePerShare", "0.01", "2", False),
                (REVENUE, "16214000", "-3", False),
            ],
        )

    def test_periods_and_dimensions(self):
        facts = parse_instance(FIXTURE_BYTES)

        self.assertEqual(
            [
                (f.context_id, f.period_start, f.period_end, f.period_instant, f.dimensions)
                for f in facts
            ],
            [
                (INSTANT, None, None, "2026-06-30", None),
                (DURATION, "2026-04-01", "2026-06-30", None, EUROPE),
                (INSTANT, None, None, "2026-06-30", None),
                (DURATION, "2026-04-01", "2026-06-30", None, EUROPE),
            ],
        )

    def test_units_including_divide(self):
        facts = parse_instance(FIXTURE_BYTES)

        self.assertEqual(
            [f.unit for f in facts],
            ["iso4217:USD", None, "iso4217:USD/shares", "iso4217:USD"],
        )

    def test_instance_with_default_namespace(self):
        # The pilot instances declare the XBRL namespace as the default namespace.
        self.assertIn(f'xmlns="{INSTANCE_NAMESPACE}"'.encode(), FIXTURE_BYTES)
        prefixed = FIXTURE_BYTES.replace(
            f'xmlns="{INSTANCE_NAMESPACE}"'.encode(),
            f'xmlns:xbrli="{INSTANCE_NAMESPACE}"'.encode(),
        )
        prefixed = prefixed.replace(b"<xbrl\n", b"<xbrli:xbrl\n").replace(
            b"</xbrl>", b"</xbrli:xbrl>"
        )
        for tag in XBRLI_TAGS:
            for opening in (f"<{tag}>", f"<{tag} "):
                prefixed = prefixed.replace(
                    opening.encode(), opening.replace("<", "<xbrli:").encode()
                )
            prefixed = prefixed.replace(f"</{tag}>".encode(), f"</xbrli:{tag}>".encode())
        self.assertNotIn(b"<context", prefixed)
        self.assertNotIn(b"<unit", prefixed)
        self.assertIn(b"<xbrli:context id=", prefixed)

        self.assertEqual(parse_instance(prefixed), parse_instance(FIXTURE_BYTES))
        self.assertEqual(parse_instance(prefixed), FIXTURE_FACTS)

    def test_doctype_refused(self):
        entity = FIXTURE_BYTES.replace(b"<xbrl\n", b'<!DOCTYPE xbrl [<!ENTITY x "y">]>\n<xbrl\n', 1)
        self.assertIn(b"<!DOCTYPE", entity)

        with self.assertRaisesRegex(XbrlError, "DOCTYPE"):
            parse_instance(entity)


class ParseRuleTests(unittest.TestCase):
    def test_concept_prefix_is_the_documents_own(self):
        # Two prefixes for one namespace: the first declaration wins. A namespace declared
        # only as the default one gives `{namespace}local`. A fact with no namespace is bare.
        raw = (
            b'<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:first="urn:a"'
            b' xmlns:second="urn:a">'
            b'<second:One contextRef="c">1</second:One>'
            b'<Two xmlns="urn:only-default" contextRef="c">2</Two>'
            b'<Three xmlns="" contextRef="c">3</Three>'
            b'<other:Four xmlns:other="urn:late" contextRef="c">4</other:Four>'
            b"</xbrl>"
        )

        self.assertEqual(
            [f.concept for f in parse_instance(raw)],
            ["first:One", "{urn:only-default}Two", "Three", "other:Four"],
        )

    def test_value_is_the_text_as_filed(self):
        facts = facts_of(
            '<a:Padded contextRef="c"> 12\n</a:Padded>'
            '<a:Empty contextRef="c"/>'
            '<a:EmptyPair contextRef="c"></a:EmptyPair>'
            '<a:Nil contextRef="c" xsi:nil="true"/>'
            '<a:NilWithText contextRef="c" xsi:nil="true">5</a:NilWithText>'
            '<a:NotNil contextRef="c" xsi:nil="false">6</a:NotNil>'
            '<a:Entity contextRef="c">A &amp; B</a:Entity>'
        )

        self.assertEqual(
            [(f.concept, f.value, f.is_nil) for f in facts],
            [
                ("a:Padded", " 12\n", False),
                ("a:Empty", "", False),
                ("a:EmptyPair", "", False),
                ("a:Nil", None, True),
                ("a:NilWithText", None, True),
                ("a:NotNil", "6", False),
                ("a:Entity", "A & B", False),
            ],
        )

    def test_nil_is_matched_by_namespace_not_prefix(self):
        raw = (
            b'<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:a="urn:a"'
            b' xmlns:i="http://www.w3.org/2001/XMLSchema-instance" xmlns:x="urn:not-xsi">'
            b'<a:Renamed contextRef="c" i:nil="true"/>'
            b'<a:Foreign contextRef="c" x:nil="true">7</a:Foreign>'
            b"</xbrl>"
        )

        self.assertEqual(
            [(f.concept, f.value, f.is_nil) for f in parse_instance(raw)],
            [("a:Renamed", None, True), ("a:Foreign", "7", False)],
        )

    def test_only_direct_children_with_a_context_ref_and_no_children_are_facts(self):
        facts = facts_of(
            context("c") + "<a:NoContext>1</a:NoContext>"
            '<a:Tuple contextRef="c"><a:inner contextRef="c">2</a:inner></a:Tuple>'
            '<a:Kept contextRef="c">3</a:Kept>'
        )

        self.assertEqual([(f.concept, f.value) for f in facts], [("a:Kept", "3")])

    def test_facts_may_come_before_their_contexts_and_units(self):
        facts = facts_of(
            '<a:Early contextRef="c" unitRef="u" decimals="0">1</a:Early>'
            + context("c")
            + '<unit id="u"><measure>iso4217:USD</measure></unit>'
        )

        self.assertEqual(
            [(f.unit, f.period_instant, f.decimals) for f in facts],
            [("iso4217:USD", "2026-06-30", "0")],
        )

    def test_period_forms(self):
        facts = facts_of(
            context("instant")
            + context(
                "duration", period="<startDate>2026-01-01</startDate><endDate>2026-03-31</endDate>"
            )
            + context("forever", period="<forever/>")
            + "".join(
                f'<a:F contextRef="{name}">1</a:F>' for name in ("instant", "duration", "forever")
            )
        )

        self.assertEqual(
            [(f.context_id, f.period_start, f.period_end, f.period_instant) for f in facts],
            [
                ("instant", None, None, "2026-06-30"),
                ("duration", "2026-01-01", "2026-03-31", None),
                ("forever", None, None, None),
            ],
        )

    def test_dimensions_are_sorted_and_joined(self):
        members = (
            '<xbrldi:explicitMember dimension="z:Axis">z:Member</xbrldi:explicitMember>'
            '<xbrldi:typedMember dimension="b:Axis"><b:id>42</b:id></xbrldi:typedMember>'
            '<xbrldi:explicitMember dimension="a:Axis">a:Member</xbrldi:explicitMember>'
        )
        facts = facts_of(
            context("c", members=members)
            + context("plain")
            + '<a:F contextRef="c">1</a:F><a:G contextRef="plain">2</a:G>'
        )

        self.assertEqual(
            [f.dimensions for f in facts],
            ["a:Axis=a:Member;b:Axis=42;z:Axis=z:Member", None],
        )

    def test_unit_forms(self):
        facts = facts_of(
            context("c") + '<unit id="one"><measure>iso4217:USD</measure></unit>'
            '<unit id="product"><measure>a</measure><measure>b</measure></unit>'
            '<unit id="ratio"><divide><unitNumerator><measure>iso4217:USD</measure>'
            "</unitNumerator><unitDenominator><measure>shares</measure></unitDenominator>"
            "</divide></unit>"
            '<unit id="wide"><divide><unitNumerator><measure>a</measure><measure>b</measure>'
            "</unitNumerator><unitDenominator><measure>c</measure><measure>d</measure>"
            "</unitDenominator></divide></unit>"
            + "".join(
                f'<a:F contextRef="c" unitRef="{unit}">1</a:F>'
                for unit in ("one", "product", "ratio", "wide")
            )
        )

        self.assertEqual(
            [f.unit for f in facts],
            ["iso4217:USD", "a*b", "iso4217:USD/shares", "a*b/c*d"],
        )

    def test_a_dangling_reference_keeps_the_fact_with_null_columns(self):
        facts = facts_of(
            '<a:NoContext contextRef="missing" unitRef="gone">1</a:NoContext>'
            + context("c")
            + '<a:NoUnit contextRef="c" unitRef="gone">2</a:NoUnit>'
            '<a:Unitless contextRef="c">3</a:Unitless>'
        )

        self.assertEqual(
            [(f.concept, f.context_id, f.unit, f.period_instant, f.dimensions) for f in facts],
            [
                ("a:NoContext", "missing", None, None, None),
                ("a:NoUnit", "c", None, "2026-06-30", None),
                ("a:Unitless", "c", None, "2026-06-30", None),
            ],
        )

    def test_text_that_is_not_xml_is_refused(self):
        for raw in (b"", b"not xml", instance("<a:F contextRef='c'>1")[:-8]):
            with (
                self.subTest(raw=raw[:20]),
                self.assertRaisesRegex(XbrlError, "not well-formed XML"),
            ):
                parse_instance(raw)

    def test_fact_is_frozen(self):
        with self.assertRaises(AttributeError):
            FIXTURE_FACTS[0].value = "changed"


def document(type_: str, filename: str | None = "doc.xml") -> Document:
    return Document(
        sequence=1, type=type_, filename=filename, description=None, text_offset=0, text_length=0
    )


class FindInstanceTests(unittest.TestCase):
    def test_find_instance_prefers_ex101_ins(self):
        htm = document("XML", "acme-20260630_htm.xml")
        ins = document("EX-101.INS", "acme-20260630.xml")
        other_ins = document("EX-101.INS", "second.xml")
        other_htm = document("XML", "second_htm.xml")
        primary = document("10-Q", "acme-20260630.htm")

        self.assertIs(find_instance([primary, htm, ins, other_ins]), ins)
        self.assertIs(find_instance([primary, htm, other_htm]), htm)
        self.assertIs(find_instance([primary, other_htm, htm]), other_htm)
        self.assertIsNone(find_instance([primary, document("XML", "R1.htm")]))
        self.assertIsNone(find_instance([document("XML", None)]))
        self.assertIsNone(find_instance([]))


def wrapped(text: bytes, tag: str) -> str:
    return f"<{tag}>\n{text.decode()}\n</{tag}>\n"


def submission_with(*documents: tuple[str, str, str], form: str = "10-Q") -> bytes:
    """A submission in the Task 4 grammar. A document is `(type, filename, text)`."""
    return build_submission(
        header=f"CONFORMED SUBMISSION TYPE:\t{form}\n",
        documents=tuple(
            build_document(
                text,
                type_line=f"<TYPE>{type_}\n",
                extra=f"<SEQUENCE>{number}\n<FILENAME>{filename}\n",
            )
            for number, (type_, filename, text) in enumerate(documents, start=1)
        ),
    )


PRIMARY = ("10-Q", "acme-20260630.htm", "<html>body</html>\n")
INS_NAME = "acme-20260630.xml"
HTM_NAME = "acme-20260630_htm.xml"
EMPTY_INSTANCE = instance("")


class FactsRootTestCase(unittest.TestCase):
    """A temporary root with a `sample`, a `fetches` table and the submission bytes."""

    def setUp(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.layout = Layout(Path(folder.name) / "root")
        self.layout.root.mkdir()
        self.sampled: list[dict] = []
        self.fetched: list[dict] = []

    def add(self, form_type: str, raw: bytes | None = None, outcome: str = "ok") -> str:
        """Sample one filing. Bytes of `raw` go on disk, as the fetch would leave them."""
        draw = len(self.sampled) + 1
        accession = f"0000000001-26-{draw:06d}"
        self.sampled.append(
            {
                "draw": draw,
                "stratum": "quota",
                "accession_number": accession,
                "form_type": form_type,
                "cik": 1000,
                "company_name": "ACME CORP",
                "date_filed": datetime.date(2026, 8, 14),
                "filename": f"edgar/data/1000/{accession}.txt",
                "url": f"https://www.sec.gov/Archives/edgar/data/1000/{accession}.txt",
            }
        )
        self.fetched.append(
            {
                "accession_number": accession,
                "form_type": form_type,
                "outcome": outcome,
                "reason": None if outcome == "ok" else outcome,
            }
        )
        if raw is not None:
            self.layout.bytes_dir.mkdir(exist_ok=True)
            self.layout.submission(accession).write_bytes(raw)
        return accession

    def write_tables(self, *, fetches: bool = True) -> None:
        # The sample is written out of draw order: the commands sort it themselves.
        write_table(self.layout, "sample", list(reversed(self.sampled)))
        if fetches:
            write_table(self.layout, "fetches", self.fetched)

    def run_facts(self, **kwargs) -> tuple[list[dict], list[dict]]:
        self.write_tables(**kwargs)
        self.assertEqual(run_facts(self.layout), 0)
        facts = read_table(self.layout, "facts")
        status = read_table(self.layout, "facts_status")
        self.assertEqual(facts.schema, SCHEMAS["facts"])
        self.assertEqual(status.schema, SCHEMAS["facts_status"])
        return facts.to_pylist(), status.to_pylist()


def fact_row(accession: str, source: str, fact: Fact) -> dict:
    return {
        "accession_number": accession,
        "source_document": source,
        "concept": fact.concept,
        "value": fact.value,
        "unit": fact.unit,
        "period_start": fact.period_start,
        "period_end": fact.period_end,
        "period_instant": fact.period_instant,
        "decimals": fact.decimals,
        "context_id": fact.context_id,
        "dimensions": fact.dimensions,
        "is_nil": fact.is_nil,
    }


class RunFactsTests(FactsRootTestCase):
    def test_no_instance_gives_reason(self):
        accession = self.add("10-Q", submission_with(PRIMARY, ("XML", "R1.htm", "<html/>\n")))

        facts, status = self.run_facts()

        self.assertEqual(facts, [])
        self.assertEqual(
            status,
            [
                {
                    "accession_number": accession,
                    "form_type": "10-Q",
                    "source_document": None,
                    "fact_count": None,
                    "reason": "no XBRL instance in the submission",
                }
            ],
        )

    def test_xbrl_wrapped_instance(self):
        accession = self.add(
            "10-K",
            submission_with(
                ("10-K", "acme-20251231.htm", "<html/>\n"),
                ("EX-101.INS", INS_NAME, wrapped(FIXTURE_BYTES, "XBRL")),
                form="10-K",
            ),
        )

        facts, status = self.run_facts()

        self.assertEqual(facts, [fact_row(accession, INS_NAME, fact) for fact in FIXTURE_FACTS])
        self.assertEqual(
            status,
            [
                {
                    "accession_number": accession,
                    "form_type": "10-K",
                    "source_document": INS_NAME,
                    "fact_count": 4,
                    "reason": None,
                }
            ],
        )

    def test_instance_counted_once(self):
        accession = self.add(
            "10-Q",
            submission_with(
                PRIMARY,
                ("XML", HTM_NAME, wrapped(FIXTURE_BYTES, "XML")),
                ("EX-101.INS", INS_NAME, wrapped(FIXTURE_BYTES, "XBRL")),
            ),
        )

        facts, status = self.run_facts()

        self.assertEqual(facts, [fact_row(accession, INS_NAME, fact) for fact in FIXTURE_FACTS])
        self.assertEqual([row["source_document"] for row in status], [INS_NAME])
        self.assertEqual([row["fact_count"] for row in status], [4])

    def test_sec_extracted_instance_is_the_source_when_there_is_no_ex101_ins(self):
        accession = self.add(
            "10-Q",
            submission_with(PRIMARY, ("XML", HTM_NAME, wrapped(FIXTURE_BYTES, "XML"))),
        )

        facts, status = self.run_facts()

        self.assertEqual(facts, [fact_row(accession, HTM_NAME, fact) for fact in FIXTURE_FACTS])
        self.assertEqual(status[0]["source_document"], HTM_NAME)
        self.assertIsNone(status[0]["reason"])

    def test_reasons_follow_the_order_of_the_checks(self):
        good = self.add(
            "10-K",
            submission_with(PRIMARY, ("EX-101.INS", INS_NAME, wrapped(FIXTURE_BYTES, "XBRL"))),
        )
        not_found = self.add("10-Q", None, outcome="not_found")
        corrupt = self.add("10-Q", b"not a submission\n")
        no_instance = self.add("10-Q", submission_with(PRIMARY))
        doctype = self.add(
            "10-K/A",
            submission_with(
                PRIMARY, ("XML", HTM_NAME, wrapped(b"<!DOCTYPE xbrl []><xbrl/>", "XML"))
            ),
        )
        no_facts = self.add(
            "10-Q/A", submission_with(PRIMARY, ("XML", HTM_NAME, wrapped(EMPTY_INSTANCE, "XML")))
        )
        repeated = self.add(
            "10-Q;8-K",
            submission_with(PRIMARY, ("XML", HTM_NAME, wrapped(FIXTURE_BYTES, "XML"))),
        )
        self.add("8-K", submission_with(PRIMARY))
        self.add("4;SC 13D", submission_with(PRIMARY))
        self.add("10-K", None, outcome="failed")

        facts, status = self.run_facts()

        self.assertEqual(
            [(row["accession_number"], row["form_type"]) for row in status],
            [
                (good, "10-K"),
                (not_found, "10-Q"),
                (corrupt, "10-Q"),
                (no_instance, "10-Q"),
                (doctype, "10-K/A"),
                (no_facts, "10-Q/A"),
                (repeated, "10-Q;8-K"),
                ("0000000001-26-000010", "10-K"),
            ],
        )
        self.assertEqual(
            [(row["source_document"], row["fact_count"], row["reason"]) for row in status],
            [
                (INS_NAME, 4, None),
                (None, None, "not_found"),
                (None, None, "submission parse error: no <SEC-HEADER> ... </SEC-HEADER> block"),
                (None, None, "no XBRL instance in the submission"),
                (HTM_NAME, None, "instance parse error: the document has a DOCTYPE declaration"),
                (HTM_NAME, None, "no facts in the instance"),
                (HTM_NAME, 4, None),
                (None, None, "failed"),
            ],
        )
        self.assertEqual(
            sorted({row["accession_number"] for row in facts}), sorted([good, repeated])
        )
        self.assertEqual(len(facts), 8)

    def test_a_not_well_formed_instance_gives_its_parse_message(self):
        self.add("10-Q", submission_with(PRIMARY, ("XML", HTM_NAME, "<xbrl><unclosed>\n")))

        facts, status = self.run_facts()

        self.assertEqual(facts, [])
        self.assertTrue(
            status[0]["reason"].startswith("instance parse error: not well-formed XML: "),
            status[0]["reason"],
        )
        self.assertEqual(status[0]["source_document"], HTM_NAME)

    def test_fetches_are_built_from_the_ledger_when_the_table_is_missing(self):
        self.add("10-Q", submission_with(PRIMARY, ("XML", HTM_NAME, wrapped(FIXTURE_BYTES, "XML"))))
        self.add("10-K", None, outcome="not_attempted")

        facts, status = self.run_facts(fetches=False)

        self.assertFalse(self.layout.table("fetches").exists())
        self.assertEqual(len(facts), 4)
        self.assertEqual([row["reason"] for row in status], [None, "not_attempted"])

    def test_fact_forms(self):
        self.assertEqual(FACT_FORMS, {"10-K", "10-K/A", "10-Q", "10-Q/A"})


class FactsCommandTests(FactsRootTestCase):
    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = cli.main([*argv, "--out", str(self.layout.root)])
        return code, stdout.getvalue(), stderr.getvalue()

    def build_root(self) -> list[str]:
        accessions = [
            self.add(
                "10-K",
                submission_with(PRIMARY, ("EX-101.INS", INS_NAME, wrapped(FIXTURE_BYTES, "XBRL"))),
            ),
            self.add(
                "10-Q", submission_with(PRIMARY, ("XML", HTM_NAME, wrapped(FIXTURE_BYTES, "XML")))
            ),
            self.add("10-Q", submission_with(PRIMARY)),
            self.add("10-Q", None, outcome="not_found"),
            self.add("10-K", None, outcome="not_found"),
        ]
        self.write_tables()
        return accessions

    def test_facts_prints_fact_rows_and_status_per_reason(self):
        self.build_root()

        code, stdout, stderr = self.run_cli("facts")

        self.assertEqual((code, stderr), (0, ""))
        self.assertEqual(
            stdout,
            "facts: 8\n"
            "status ok: 2\n"
            "status no XBRL instance in the submission: 1\n"
            "status not_found: 2\n",
        )
        steps = [
            json.loads(line)["step"]
            for line in self.layout.runs.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(steps, ["facts"])

    def test_report_has_a_facts_section_before_the_platform_checks(self):
        self.build_root()
        self.run_cli("facts")

        report = run_report(self.layout)

        titles = [line for line in report.split("\n") if line.startswith("## ")]
        self.assertEqual(titles[-3:], ["## Facts", "## Ownership", "## Platform checks"])
        self.assertEqual(
            section(report, "Facts"),
            [
                "- filings in the fact forms: 5",
                "- fact rows: 8",
                "- filings with facts: 2",
                "  - EX-101.INS: 1",
                "  - *_htm.xml: 1",
                "- filings with no facts: 3",
                "  - no XBRL instance in the submission: 1",
                "  - not_found: 2",
            ],
        )

    def test_report_says_when_the_facts_status_table_is_missing(self):
        self.build_root()

        report = run_report(self.layout)

        self.assertEqual(section(report, "Facts"), ["- no `facts_status` table yet"])


if __name__ == "__main__":
    unittest.main()
