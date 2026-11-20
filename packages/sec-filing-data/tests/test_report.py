import datetime
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pyarrow.parquet as pq
from sec_filing_data import index, version
from sec_filing_data.facts import run_facts
from sec_filing_data.fetch import run_refetch
from sec_filing_data.index import run_index
from sec_filing_data.layout import Layout
from sec_filing_data.ledger import ledger_usage
from sec_filing_data.ownership import run_ownership
from sec_filing_data.partners import RULES
from sec_filing_data.refetches import run_compare_refetches
from sec_filing_data.report import run_report
from sec_filing_data.sample import run_sample
from sec_filing_data.submissions import run_envelopes
from sec_filing_data.tables import (
    SCHEMAS,
    STAGE3_TABLES,
    STAGE4_TABLES,
    TABLE_FORMATS,
    read_table,
    write_table,
)

from tests.stage4_root import (
    PARTNER_4,
    PARTNER_13D_A1,
    PARTNER_13D_A2,
    PARTNER_13F_A,
    PARTNER_D,
    SAMPLED_4_A,
    SAMPLED_13D,
    SAMPLED_13F,
    SAMPLED_D_A,
    Stage4RootTestCase,
    build_stage4_root,
)
from tests.test_client import USER_AGENT
from tests.test_commands import (
    CommandTestCase,
    FixtureSession,
    accession_of,
    section,
    utc,
)
from tests.test_index import FIXTURE, fingerprint, write_zip

SOURCE_AND_TIMES = "a null source_url or source_sha256"
NULL_TIMES = "a null accepted_at or fetched_at"
TABLES = ("index", "filings", "parties", "documents", "facts", "ownership")


def build_fixture_root(case: CommandTestCase) -> Path:
    """Run every offline step and one refetch over the index fixture. Return its zip path.

    `index.INDEX_SHA256` and `INDEX_SIZE` name the fixture zip until the test ends.
    """
    folder = tempfile.TemporaryDirectory()
    case.addCleanup(folder.cleanup)
    zip_path = write_zip(Path(folder.name), FIXTURE.read_text(encoding="utf-8"))
    sha256, size = fingerprint(zip_path)
    case.enterContext(mock.patch.object(index, "INDEX_SHA256", sha256))
    case.enterContext(mock.patch.object(index, "INDEX_SIZE", size))
    run_index(case.layout, zip_path)
    sampled = run_sample(case.layout)
    case.assertEqual(case.fetch(FixtureSession()), 0)
    for step in (run_envelopes, run_facts, run_ownership):
        case.assertEqual(step(case.layout), 0)
    refetched = run_refetch(
        case.layout,
        user_agent=USER_AGENT,
        accessions=[sampled[0]["accession_number"]],
        session=FixtureSession(),
        monotonic=case.clock.monotonic,
        sleep=case.clock.sleep,
    )
    case.assertEqual(refetched, 0)
    case.assertEqual(run_compare_refetches(case.layout), 0)
    return zip_path


def filing_row(number: int, **values) -> dict:
    """A `filings` row with every column, null unless `values` sets it."""
    row = dict.fromkeys(SCHEMAS["filings"].names)
    row.update(accession_number=accession_of(number), outcome="ok", **values)
    return row


def times_row(number: int, rule: str, *, accepted, public, modified) -> dict:
    return filing_row(
        number, accepted_at=accepted, public_at=public, public_rule=rule, last_modified_at=modified
    )


def read_rows(layout: Layout, name: str) -> list[dict]:
    return read_table(layout, name).to_pylist()


class ReportTimesTests(CommandTestCase):
    def times_section(self, rows: list[dict]) -> list[str]:
        write_table(self.layout, "filings", rows)
        return section(run_report(self.layout), "Times")

    def test_report_times_section(self):
        noon = utc(2026, 8, 14, 16, 0, 0)
        second = datetime.timedelta(seconds=1)
        rows = [
            times_row(1, "acceptance", accepted=noon, public=noon, modified=noon + 12 * second),
            times_row(2, "next_opening", accepted=noon, public=noon, modified=noon + 186 * second),
            times_row(
                3, "acceptance", accepted=noon, public=noon, modified=noon + 1_102_799 * second
            ),
            times_row(4, "next_opening", accepted=noon, public=noon + 5 * second, modified=noon),
            times_row(5, "acceptance", accepted=noon, public=noon - second, modified=None),
        ]

        lines = self.times_section(rows)

        self.assertEqual(
            lines,
            [
                "- acceptance: 3",
                "- next_opening: 2",
                "- private_to_public: 0",
                "- no_acceptance: 0",
                "- filings with a null last_modified_at: 1",
                (
                    "- gap from public_at to last_modified_at: least -5 s, median 12 s,"
                    " largest 1102799 s"
                ),
                "- filings with a gap above 1 hour: 1",
                f"  - {accession_of(3)}: 1102799 s",
                "- filings with public_at after last_modified_at: 1",
                f"  - {accession_of(4)}",
                "- filings with public_at before accepted_at: 1",
                f"  - {accession_of(5)}",
                "- filings with an unreadable filed_as_of_date: 0",
            ],
        )

    def test_report_times_edges(self):
        noon = utc(2026, 8, 14, 16, 0, 0)
        second = datetime.timedelta(seconds=1)
        rows = [
            # A gap of exactly 1 hour is not above it. One more second is.
            times_row(1, "acceptance", accepted=noon, public=noon, modified=noon + 3600 * second),
            times_row(2, "acceptance", accepted=noon, public=noon, modified=noon + 3601 * second),
            # Equal times are neither after nor before.
            times_row(3, "acceptance", accepted=noon, public=noon, modified=noon),
        ]

        lines = self.times_section(rows)

        self.assertIn(
            "- gap from public_at to last_modified_at: least 0 s, median 3600 s, largest 3601 s",
            lines,
        )
        self.assertEqual(
            lines[lines.index("- filings with a gap above 1 hour: 1") :],
            [
                "- filings with a gap above 1 hour: 1",
                f"  - {accession_of(2)}: 3601 s",
                "- filings with public_at after last_modified_at: 0",
                "- filings with public_at before accepted_at: 0",
                "- filings with an unreadable filed_as_of_date: 0",
            ],
        )

    def test_report_times_use_only_parsed_ok_filings(self):
        noon = utc(2026, 8, 14, 16, 0, 0)
        late = noon + datetime.timedelta(days=2)
        early = noon - datetime.timedelta(days=2)
        rows = [
            times_row(1, "acceptance", accepted=noon, public=noon, modified=noon),
            # Neither of these is a parsed `ok` filing, so none of its times counts.
            {**times_row(2, "acceptance", accepted=noon, public=early, modified=late)}
            | {"outcome": "failed"},
            {**times_row(3, "acceptance", accepted=noon, public=late, modified=early)}
            | {"parse_error": "no header"},
        ]

        lines = self.times_section(rows)

        self.assertEqual(
            lines,
            [
                "- acceptance: 1",
                "- next_opening: 0",
                "- private_to_public: 0",
                "- no_acceptance: 0",
                "- filings with a null last_modified_at: 0",
                "- gap from public_at to last_modified_at: least 0 s, median 0 s, largest 0 s",
                "- filings with a gap above 1 hour: 0",
                "- filings with public_at after last_modified_at: 0",
                "- filings with public_at before accepted_at: 0",
                "- filings with an unreadable filed_as_of_date: 0",
            ],
        )

    def test_report_times_show_an_unreadable_filed_as_of_date(self):
        noon = utc(2026, 8, 14, 16, 0, 0)
        rows = [
            {**times_row(n, "acceptance", accepted=noon, public=noon, modified=noon)}
            | {"filed_as_of_date": filed}
            for n, filed in ((1, "2026-08-14"), (2, None), (3, "20260814"))
        ] + [
            # Not a parsed `ok` filing, so its date does not count.
            {**times_row(4, "acceptance", accepted=noon, public=noon, modified=noon)}
            | {"filed_as_of_date": "14/08/2026", "outcome": "failed"},
        ]

        lines = self.times_section(rows)

        self.assertEqual(
            lines[-2:],
            ["- filings with an unreadable filed_as_of_date: 1", f"  - {accession_of(1)}"],
        )

    def test_report_times_with_no_gap_to_measure(self):
        noon = utc(2026, 8, 14, 16, 0, 0)

        lines = self.times_section(
            [times_row(1, "no_acceptance", accepted=None, public=None, modified=None)]
        )

        self.assertEqual(
            lines[0:4],
            [
                "- acceptance: 0",
                "- next_opening: 0",
                "- private_to_public: 0",
                "- no_acceptance: 1",
            ],
        )
        self.assertEqual(lines[4], "- filings with a null last_modified_at: 1")
        self.assertEqual(
            lines[5], "- gap from public_at to last_modified_at: no filing has both times"
        )
        self.assertNotIn(noon, lines)

    def test_report_times_without_filings(self):
        self.assertEqual(section(run_report(self.layout), "Times"), ["- no `filings` table yet"])


class ReportProvenanceTests(CommandTestCase):
    def provenance(self) -> list[str]:
        return section(run_report(self.layout), "Provenance")

    def line(self, table: str, source: int, times: int) -> str:
        return f"- {table}: {source} rows with {SOURCE_AND_TIMES}, {times} rows of ok filings with {NULL_TIMES}"

    def rewrite(self, name: str, change) -> None:
        rows = read_rows(self.layout, name)
        change(rows)
        write_table(self.layout, name, rows)

    def test_report_provenance_section(self):
        build_fixture_root(self)
        # The fixture gives no fact and no ownership record: only these three have rows.
        for name in ("filings", "parties", "documents"):
            self.assertGreater(len(read_rows(self.layout, name)), 0, name)

        self.assertEqual(
            self.provenance(),
            [*(self.line(table, 0, 0) for table in TABLES), "- index rows with filing times: 6"],
        )

        # An unreadable acceptance shows as an ok filing with a null accepted_at.
        def unreadable(rows):
            rows[0]["accepted_at"] = None

        self.rewrite("filings", unreadable)

        def no_source(rows):
            rows[0]["source_url"] = None

        self.rewrite("parties", no_source)

        lines = self.provenance()
        self.assertIn(self.line("filings", 0, 1), lines)
        self.assertIn(self.line("parties", 1, 0), lines)
        self.assertEqual(len(lines), 7)

    def test_index_rerun_after_envelopes_shows_in_provenance(self):
        zip_path = build_fixture_root(self)

        run_index(self.layout, zip_path)

        lines = self.provenance()
        self.assertIn(self.line("index", 0, 6), lines)
        self.assertEqual(lines[-1], "- index rows with filing times: 0")

    def test_a_row_counts_once_whichever_source_column_is_null(self):
        build_fixture_root(self)

        def three(rows):
            rows[0]["source_url"] = None
            rows[1]["source_sha256"] = None
            rows[2]["source_url"] = rows[2]["source_sha256"] = None

        self.rewrite("documents", three)

        self.assertIn(self.line("documents", 3, 0), self.provenance())

    def test_a_row_counts_once_whichever_time_is_null(self):
        build_fixture_root(self)

        def three(rows):
            rows[0]["accepted_at"] = None
            rows[1]["fetched_at"] = None
            rows[2]["accepted_at"] = rows[2]["fetched_at"] = None

        self.rewrite("parties", three)

        self.assertIn(self.line("parties", 0, 3), self.provenance())

    def test_facts_and_ownership_are_counted_by_their_own_columns(self):
        build_fixture_root(self)
        ok = read_rows(self.layout, "filings")[0]["accession_number"]
        stamp = utc(2026, 8, 14, 16, 0, 0)
        whole = {"source_url": "u", "source_sha256": "s", "accepted_at": stamp, "fetched_at": stamp}
        rows = [
            {"accession_number": ok, **whole},
            {"accession_number": ok, **whole, "source_url": None},
            {"accession_number": ok, **whole, "fetched_at": None},
        ]
        write_table(self.layout, "facts", rows)
        write_table(self.layout, "ownership", rows)

        lines = self.provenance()

        self.assertIn(self.line("facts", 1, 1), lines)
        self.assertIn(self.line("ownership", 1, 1), lines)

    def test_filings_sha256_is_its_source_checksum(self):
        build_fixture_root(self)

        def no_checksum(rows):
            rows[0]["sha256"] = None

        self.rewrite("filings", no_checksum)

        self.assertIn(self.line("filings", 1, 0), self.provenance())

    def test_only_rows_of_ok_filings_count_for_null_times(self):
        build_fixture_root(self)
        (accession,) = {row["accession_number"] for row in read_rows(self.layout, "parties")[:1]}

        def fail(rows):
            for row in rows:
                if row["accession_number"] == accession:
                    row["outcome"] = "failed"

        def no_times(rows):
            for row in rows:
                if row["accession_number"] == accession:
                    row["accepted_at"] = None

        self.rewrite("filings", fail)
        self.rewrite("parties", no_times)

        self.assertIn(self.line("parties", 0, 0), self.provenance())

    def test_provenance_reads_only_the_columns_it_counts(self):
        build_fixture_root(self)
        calls: list[tuple[str, list[str] | None]] = []
        real = pq.read_table

        def recording(source, *args, columns=None, **kwargs):
            calls.append((Path(source).stem, columns))
            return real(source, *args, columns=columns, **kwargs)

        with mock.patch.object(pq, "read_table", recording):
            self.provenance()

        # `facts` is read by the Provenance section alone, and `index` also for its row count.
        self.assertEqual([columns for name, columns in calls if name == "facts"], [mock.ANY])
        allowed = {
            "accession_number",
            "source_url",
            "source_sha256",
            "sha256",
            "accepted_at",
            "fetched_at",
        }
        for name, columns in calls:
            if name in ("facts", "ownership", "index") and columns is not None:
                self.assertLessEqual(set(columns), allowed, name)
        counted = {name for name, columns in calls if columns is not None}
        self.assertEqual(counted, set(TABLES))
        self.assertTrue(all(columns is not None for name, columns in calls if name == "facts"))

    def test_provenance_without_tables(self):
        lines = self.provenance()

        self.assertEqual(
            lines,
            [
                *(f"- {table}: no `{table}` table yet" for table in TABLES),
                "- index rows with filing times: no `index` table yet",
            ],
        )


class ReportRefetchesTests(CommandTestCase):
    def test_report_refetches_section(self):
        build_fixture_root(self)
        (row,) = read_table(self.layout, "refetches").to_pylist()

        lines = section(run_report(self.layout), "Refetches")

        self.assertEqual(
            lines,
            [
                (
                    f"- {row['accession_number']}: outcome ok,"
                    f" stage1_sha256 {row['stage1_sha256']},"
                    f" refetch_sha256 {row['refetch_sha256']}, sha256_equal True,"
                    " stage1_last_modified_at null, refetch_last_modified_at null,"
                    f" refetched_at {row['refetched_at'].isoformat()},"
                    " changed_header_fields null, changed_documents null"
                ),
                "- Stage 2 requests: 1 of 20",
                f"- Stage 2 wire bytes: {ledger_usage(self.layout.stage2_ledger).wire_bytes} of 50000000",
            ],
        )

    def test_report_refetches_without_a_table(self):
        lines = section(run_report(self.layout), "Refetches")

        self.assertEqual(
            lines,
            [
                "- no `refetches` table yet",
                "- Stage 2 requests: 0 of 20",
                "- Stage 2 wire bytes: 0 of 50000000",
            ],
        )

    def test_the_four_sections_follow_platform_checks(self):
        titles = [line for line in run_report(self.layout).split("\n") if line.startswith("## ")]

        self.assertEqual(
            titles[-6:],
            [
                "## Platform checks",
                "## Times",
                "## Provenance",
                "## Refetches",
                "## Stage 4",
                "## Versions",
            ],
        )


def row_of(layout: Layout, name: str, accession: str) -> dict:
    """The one row of `accession` in table `name`."""
    (row,) = [row for row in read_rows(layout, name) if row["accession_number"] == accession]
    return row


def update_row(layout: Layout, name: str, accession: str, **values) -> None:
    """Write table `name` again with `values` set on the one row of `accession`."""
    rows = read_rows(layout, name)
    (row,) = [row for row in rows if row["accession_number"] == accession]
    row.update(values)
    write_table(layout, name, rows)


def pair_lines(lines: list[str]) -> list[str]:
    """The lines of a Stage 4 section from its forward pairs to the end of its other pairs."""
    start = lines.index(next(line for line in lines if line.startswith("- forward pairs: ")))
    end = lines.index(next(line for line in lines if line.startswith("- pairs whose amendment")))
    return lines[start:end]


class ReportStage4Tests(Stage4RootTestCase):
    def stage4(self) -> list[str]:
        return section(run_report(self.layout), "Stage 4")

    def test_report_stage4_section(self):
        usage = ledger_usage(self.layout.stage4_ledger)

        self.assertEqual(
            self.stage4(),
            [
                "- partners: 5 distinct, 5 rows",
                "- partners by original_previous_accession: 1",
                "- partners by original_date_issuer_owner: 1",
                "- partners by candidate_amendment: 3",
                "- fetch ok: 5",
                "- Stage 4 requests: 5 of 30",
                f"- Stage 4 wire bytes: {usage.wire_bytes} of 50000000",
                "- links: 6",
                "- links by previous_accession: 3",
                "- links by original_date_issuer_owner: 1",
                "- links by filer_period: 1",
                "- links by none_declared: 1",
                "- original held in sample: 2",
                "- original held in partner: 3",
                "- original not held: 1",
                "- forward pairs: 3",
                f"  - {PARTNER_13D_A1} amends {SAMPLED_13D}",
                f"  - {PARTNER_13D_A2} amends {PARTNER_13D_A1}",
                f"  - {PARTNER_13F_A} amends {SAMPLED_13F}",
                "- reverse pairs: 2",
                f"  - {SAMPLED_D_A} amends {PARTNER_D}",
                f"  - {SAMPLED_4_A} amends {PARTNER_4}",
                "- other pairs: 0",
                "- pairs whose amendment answers first: 1",
                (
                    f"  - {SAMPLED_D_A} (2026-07-20T15:00:30+00:00)"
                    f" before {PARTNER_D} (2026-07-21T09:00:00+00:00)"
                ),
                "- pairs with equal known_from: 0",
                "- held filings: 10",
                "- known_from before public_at: 0",
                "- no public_at: 0",
            ],
        )
        self.assertEqual(usage.requests, 5)

    def test_pairs_that_fit_neither_direction_are_other(self):
        stage4 = self.layout.stage4_view
        # Both are partners, and PARTNER_D is no candidate amendment of the same sampled filing.
        partner_original = {"original_accession": PARTNER_D, "original_held_in": "partner"}
        update_row(stage4, "links", PARTNER_13D_A1, **partner_original)
        # Both are sampled.
        sampled_original = {"original_accession": SAMPLED_13D, "original_held_in": "sample"}
        update_row(stage4, "links", SAMPLED_D_A, **sampled_original)

        self.assertEqual(
            pair_lines(self.stage4()),
            [
                "- forward pairs: 2",
                f"  - {PARTNER_13D_A2} amends {PARTNER_13D_A1}",
                f"  - {PARTNER_13F_A} amends {SAMPLED_13F}",
                "- reverse pairs: 1",
                f"  - {SAMPLED_4_A} amends {PARTNER_4}",
                "- other pairs: 2",
                f"  - {SAMPLED_D_A} amends {SAMPLED_13D}",
                f"  - {PARTNER_13D_A1} amends {PARTNER_D}",
            ],
        )

    def test_a_partner_amendment_of_another_sampled_filing_is_not_forward(self):
        update_row(
            self.layout.stage4_view, "partners", PARTNER_13D_A1, sampled_accession=SAMPLED_13F
        )

        self.assertEqual(
            pair_lines(self.stage4()),
            [
                "- forward pairs: 2",
                f"  - {PARTNER_13D_A1} amends {SAMPLED_13D}",
                f"  - {PARTNER_13F_A} amends {SAMPLED_13F}",
                "- reverse pairs: 2",
                f"  - {SAMPLED_D_A} amends {PARTNER_D}",
                f"  - {SAMPLED_4_A} amends {PARTNER_4}",
                "- other pairs: 1",
                f"  - {PARTNER_13D_A2} amends {PARTNER_13D_A1}",
            ],
        )

    def test_a_pair_with_equal_known_from_is_listed_apart(self):
        moment = row_of(self.layout, "filings", SAMPLED_13D)["last_modified_at"]
        update_row(self.layout.stage4_view, "filings", PARTNER_13D_A1, last_modified_at=moment)

        lines = self.stage4()

        self.assertIn("- pairs whose amendment answers first: 1", lines)
        at = lines.index("- pairs with equal known_from: 1")
        at_moment = moment.isoformat()
        self.assertEqual(
            lines[at + 1], f"  - {PARTNER_13D_A1} ({at_moment}) before {SAMPLED_13D} ({at_moment})"
        )

    def test_a_copy_with_no_last_modified_time_is_known_from_its_fetch_time(self):
        # PARTNER_D's copy was last modified on 2026-07-21 at 09:00:00 UTC.
        update_row(
            self.layout,
            "filings",
            SAMPLED_D_A,
            last_modified_at=None,
            fetched_at=utc(2026, 7, 22, 0, 0, 0),
        )

        lines = self.stage4()

        self.assertIn("- pairs whose amendment answers first: 0", lines)
        self.assertIn("- held filings: 10", lines)

    def test_known_from_before_public_at_and_a_null_public_at_are_named(self):
        stage4 = self.layout.stage4_view
        modified = row_of(stage4, "filings", PARTNER_4)["last_modified_at"]
        update_row(stage4, "filings", PARTNER_4, public_at=modified + datetime.timedelta(seconds=1))
        update_row(stage4, "filings", PARTNER_13F_A, public_at=None)

        lines = self.stage4()

        at = lines.index("- held filings: 10")
        self.assertEqual(
            lines[at:],
            [
                "- held filings: 10",
                "- known_from before public_at: 1",
                f"  - {PARTNER_4}",
                "- no public_at: 1",
            ],
        )

    def test_a_filing_that_is_not_ok_is_not_held(self):
        update_row(self.layout.stage4_view, "filings", PARTNER_D, outcome="failed")

        self.assertIn("- held filings: 9", self.stage4())

    def test_versions_cover_the_stage4_set(self):
        lines = section(run_report(self.layout), "Versions")

        self.assertEqual(len(lines), len(STAGE3_TABLES) + 1 + len(STAGE4_TABLES) + 1)
        self.assertEqual(lines[11], "- tables made at 5ca1ab1e5ca1: 11")
        self.assertEqual(
            lines[12:],
            [
                *(
                    f"- stage4 {name}: code 5ca1ab1e5ca1, format {TABLE_FORMATS[name]},"
                    f" {read_table(self.layout.stage4_view, name).num_rows} rows"
                    for name in STAGE4_TABLES
                ),
                "- stage4 tables made at 5ca1ab1e5ca1: 8",
            ],
        )


class ReportStage4PartialTests(CommandTestCase):
    def test_a_failed_partner_fetch_shows_in_the_outcomes_and_the_held_count(self):
        build_stage4_root(self, failing=frozenset({PARTNER_13D_A2}))

        lines = section(run_report(self.layout), "Stage 4")

        self.assertEqual(lines[0], "- partners: 5 distinct, 5 rows")
        self.assertEqual(lines[4:6], ["- fetch ok: 4", "- fetch not_found: 1"])
        self.assertIn("- links: 5", lines)
        self.assertIn("- held filings: 9", lines)
        self.assertIn("- forward pairs: 2", lines)
        self.assertNotIn(f"  - {PARTNER_13D_A2} amends {PARTNER_13D_A1}", lines)

    def test_a_link_to_an_original_that_is_not_held_is_no_pair(self):
        build_stage4_root(self, failing=frozenset({PARTNER_13D_A1}))
        # PARTNER_13D_A2 is held, and it names PARTNER_13D_A1, which the index lists but we do
        # not hold: the link names its original, and `original_held_in` is null.
        link = row_of(self.layout.stage4_view, "links", PARTNER_13D_A2)
        self.assertEqual(link["original_accession"], PARTNER_13D_A1)
        self.assertIsNone(link["original_held_in"])

        lines = section(run_report(self.layout), "Stage 4")

        self.assertIn("- original not held: 2", lines)
        self.assertEqual(
            pair_lines(lines),
            [
                "- forward pairs: 1",
                f"  - {PARTNER_13F_A} amends {SAMPLED_13F}",
                "- reverse pairs: 2",
                f"  - {SAMPLED_D_A} amends {PARTNER_D}",
                f"  - {SAMPLED_4_A} amends {PARTNER_4}",
                "- other pairs: 0",
            ],
        )

    def test_report_without_stage4(self):
        build_fixture_root(self)

        report = run_report(self.layout)

        self.assertEqual(section(report, "Stage 4"), ["- no Stage 4 tables yet"])
        self.assertNotIn("stage4", "\n".join(section(report, "Versions")))

    def test_an_empty_stage4_tables_folder_names_each_missing_table_once(self):
        build_fixture_root(self)
        self.layout.stage4_tables.mkdir(parents=True)

        report = run_report(self.layout)

        self.assertEqual(
            section(report, "Stage 4"),
            [
                "- no Stage 4 `partners` table yet",
                "- no Stage 4 `fetches` table yet",
                "- Stage 4 requests: 0 of 30",
                "- Stage 4 wire bytes: 0 of 50000000",
                "- no Stage 4 `links` table yet",
                "- no Stage 4 `filings` table yet",
            ],
        )
        self.assertEqual(
            section(report, "Versions")[-8:],
            [f"- stage4 {name}: no `{name}` table yet" for name in STAGE4_TABLES],
        )

    def test_the_tables_that_each_step_has_written_so_far(self):
        build_stage4_root(self)
        for name in ("fetches", "filings", "links"):
            self.layout.stage4_view.table(name).unlink()

        lines = section(run_report(self.layout), "Stage 4")

        by_rule = dict(zip(RULES, (1, 1, 3), strict=True))
        wire_bytes = ledger_usage(self.layout.stage4_ledger).wire_bytes
        self.assertEqual(
            lines,
            [
                "- partners: 5 distinct, 5 rows",
                *(f"- partners by {rule}: {count}" for rule, count in by_rule.items()),
                "- no Stage 4 `fetches` table yet",
                "- Stage 4 requests: 5 of 30",
                f"- Stage 4 wire bytes: {wire_bytes} of 50000000",
                "- no Stage 4 `links` table yet",
                "- no Stage 4 `filings` table yet",
            ],
        )


class ReportVersionsTests(CommandTestCase):
    def versions(self) -> list[str]:
        return section(run_report(self.layout), "Versions")

    def table_line(self, table: str, code: str, form: str) -> str:
        rows = read_table(self.layout, table).num_rows
        return f"- {table}: code {code}, format {form}, {rows} rows"

    def test_report_versions_section(self):
        build_fixture_root(self)

        self.assertEqual(
            self.versions(),
            [
                *(
                    self.table_line(table, "5ca1ab1e5ca1", str(TABLE_FORMATS[table]))
                    for table in STAGE3_TABLES
                ),
                "- tables made at 5ca1ab1e5ca1: 11",
            ],
        )

    def test_versions_tell_two_commits_apart(self):
        build_fixture_root(self)
        sample_rows = read_rows(self.layout, "sample")
        other = version.Checkout("b" * 40, True, None)
        with mock.patch.object(version, "current_checkout", lambda: other):
            write_table(self.layout, "sample", sample_rows)
        # `pq.write_table` alone leaves no stamp, as in the files of `tables-stage1/`.
        unstamped = read_table(self.layout, "refetches").replace_schema_metadata(None)
        pq.write_table(unstamped, self.layout.table("refetches"))

        lines = self.versions()

        self.assertEqual(
            lines[1], self.table_line("sample", "bbbbbbbbbbbb", str(TABLE_FORMATS["sample"]))
        )
        self.assertEqual(lines[-4], self.table_line("refetches", "not recorded", "not recorded"))
        self.assertEqual(
            lines[-3:],
            [
                "- tables made at 5ca1ab1e5ca1: 9",
                "- tables made at bbbbbbbbbbbb: 1",
                "- tables made at not recorded: 1",
            ],
        )

    def test_versions_name_a_table_that_is_not_written_yet(self):
        write_table(self.layout, "sample", [dict.fromkeys(SCHEMAS["sample"].names)])

        lines = self.versions()

        self.assertEqual(
            lines,
            [
                *(
                    self.table_line("sample", "5ca1ab1e5ca1", str(TABLE_FORMATS["sample"]))
                    if table == "sample"
                    else f"- {table}: no `{table}` table yet"
                    for table in STAGE3_TABLES
                ),
                "- tables made at 5ca1ab1e5ca1: 1",
            ],
        )

    def test_versions_without_tables_give_no_count(self):
        self.assertEqual(
            self.versions(), [f"- {table}: no `{table}` table yet" for table in STAGE3_TABLES]
        )


if __name__ == "__main__":
    unittest.main()
