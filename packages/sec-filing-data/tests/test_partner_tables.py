"""The partner tables: the Stage 4 rows of the partner filings, from the Stage 3 parse code."""

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from sec_filing_data.index import INDEX_LAST_MODIFIED_AT
from sec_filing_data.ledger import last_ok, read_ledger
from sec_filing_data.partner_tables import partner_records
from sec_filing_data.partners import distinct_partners, read_partners
from sec_filing_data.rebuild import run_rebuild
from sec_filing_data.tables import (
    FILING_TIME_COLUMNS,
    SCHEMAS,
    STAGE4_TABLES,
    TABLE_FORMATS,
    as_table_rows,
    read_stamp,
    read_table,
)
from sec_filing_data.times import last_modified_at

from tests.stage4_root import (
    LAST_MODIFIED,
    PARTNER_4,
    PARTNER_13D_A1,
    PARTNER_13D_A2,
    PARTNER_13F_A,
    PARTNER_D,
    PARTNERS,
    SAMPLED,
    SAMPLED_4_A,
    SAMPLED_13D,
    SAMPLED_13F,
    SAMPLED_D_A,
    SUBMISSIONS,
    Stage4RootTestCase,
    build_stage4_root,
    url,
)
from tests.test_commands import CommandTestCase
from tests.test_rebuild import ALL_EQUAL, file_digests, line_count

# The tables that `partner-tables` writes from the partner bytes, in the order it writes them.
PARTNER_TABLES = ("fetches", "filings", "parties", "documents", "ownership", "ownership_status")

# (original, amendment) of each pair on the root.
PAIRS = (
    (PARTNER_D, SAMPLED_D_A),
    (PARTNER_4, SAMPLED_4_A),
    (SAMPLED_13D, PARTNER_13D_A1),
    (PARTNER_13D_A1, PARTNER_13D_A2),
    (SAMPLED_13F, PARTNER_13F_A),
)
# The one pair whose amendment's copy is last modified before its original's.
REVERSE_ORDER_PAIR = (PARTNER_D, SAMPLED_D_A)


def rows_of(rows: list[dict], accession: str) -> list[dict]:
    return [row for row in rows if row["accession_number"] == accession]


class PartnerTablesTests(Stage4RootTestCase):
    def stage4_rows(self, name: str) -> list[dict]:
        return read_table(self.layout.stage4_view, name).to_pylist()

    def test_fixture_partners(self):
        sample = read_table(self.layout, "sample").to_pylist()
        self.assertEqual(sorted(row["accession_number"] for row in sample), list(SAMPLED))
        self.assertEqual([row["draw"] for row in sample], [1, 2, 3, 4, 5])

        partners = read_partners(self.layout)

        self.assertEqual(
            [(row["accession_number"], row["rule"], row["sampled_accession"]) for row in partners],
            [
                (PARTNER_D, "original_previous_accession", SAMPLED_D_A),
                (PARTNER_4, "original_date_issuer_owner", SAMPLED_4_A),
                (PARTNER_13D_A1, "candidate_amendment", SAMPLED_13D),
                (PARTNER_13D_A2, "candidate_amendment", SAMPLED_13D),
                (PARTNER_13F_A, "candidate_amendment", SAMPLED_13F),
            ],
        )
        self.assertEqual([row["url"] for row in partners], [url(partner) for partner in PARTNERS])
        fetches = self.stage4_rows("fetches")
        self.assertEqual(
            [(row["accession_number"], row["outcome"]) for row in fetches],
            [(partner, "ok") for partner in PARTNERS],
        )

    def test_fixture_times_order_each_pair(self):
        filings = {
            row["accession_number"]: row
            for layout in (self.layout, self.layout.stage4_view)
            for row in read_table(layout, "filings").to_pylist()
        }
        self.assertEqual(sorted(filings), sorted(SAMPLED + PARTNERS))
        modified = {accession: row["last_modified_at"] for accession, row in filings.items()}
        self.assertEqual(len(set(modified.values())), 10)
        for accession, row in filings.items():
            with self.subTest(accession=accession):
                self.assertEqual(row["public_rule"], "acceptance")
                self.assertEqual(row["public_at"], row["accepted_at"])
                self.assertLessEqual(row["public_at"], modified[accession])
                self.assertLess(datetime(2026, 1, 1, tzinfo=UTC), modified[accession])
                self.assertLess(modified[accession], INDEX_LAST_MODIFIED_AT)
        for original, amendment in PAIRS:
            with self.subTest(original=original, amendment=amendment):
                accepted = filings[original]["accepted_at"], filings[amendment]["accepted_at"]
                self.assertLess(*accepted)
                if (original, amendment) == REVERSE_ORDER_PAIR:
                    self.assertLess(modified[amendment], modified[original])
                else:
                    self.assertLess(modified[original], modified[amendment])

    def test_partner_tables_match_their_namesakes(self):
        stage4 = self.layout.stage4_view
        for name in PARTNER_TABLES:
            with self.subTest(table=name):
                self.assertEqual(read_table(stage4, name).schema, SCHEMAS[name])
                stamp = read_stamp(stage4.table(name))
                self.assertEqual(stamp["table_format"], str(TABLE_FORMATS[name]))
        urls = {row["accession_number"]: row["url"] for row in read_partners(self.layout)}

        filings = self.stage4_rows("filings")

        self.assertEqual([row["accession_number"] for row in filings], list(PARTNERS))
        for row in filings:
            accession = row["accession_number"]
            with self.subTest(accession=accession):
                data = self.layout.partner_submission(accession).read_bytes()
                self.assertEqual(data, SUBMISSIONS[accession])
                self.assertEqual((row["outcome"], row["reason"]), ("ok", None))
                for column in ("accepted_at", "public_at", "fetched_at"):
                    self.assertIsNotNone(row[column], column)
                self.assertEqual(row["source_url"], urls[accession])
                self.assertEqual(row["sha256"], hashlib.sha256(data).hexdigest())
                self.assertEqual(
                    row["last_modified_at"], last_modified_at(LAST_MODIFIED[accession])
                )

    def test_partner_ownership_by_form(self):
        filings = {row["accession_number"]: row for row in self.stage4_rows("filings")}
        holders = [PARTNER_4, PARTNER_13D_A1, PARTNER_13D_A2, PARTNER_13F_A]

        ownership = self.stage4_rows("ownership")
        statuses = self.stage4_rows("ownership_status")

        self.assertEqual(sorted({row["accession_number"] for row in ownership}), holders)
        self.assertEqual([row["accession_number"] for row in statuses], holders)
        for status in statuses:
            records = rows_of(ownership, status["accession_number"])
            self.assertEqual((status["record_count"], status["reason"]), (len(records), None))
        self.assertEqual(rows_of(ownership, PARTNER_D), [])
        self.assertEqual(rows_of(statuses, PARTNER_D), [])
        for row in ownership:
            filing = filings[row["accession_number"]]
            with self.subTest(accession=row["accession_number"]):
                self.assertEqual(row["source_sha256"], filing["sha256"])
                self.assertEqual(
                    {column: row[column] for column in FILING_TIME_COLUMNS},
                    {column: filing[column] for column in FILING_TIME_COLUMNS},
                )

    def test_partner_records_give_the_table_rows(self):
        fetched = {row["accession_number"]: row for row in self.stage4_rows("fetches")}
        ok_records = last_ok(read_ledger(self.layout.stage4_ledger))
        stored = {name: self.stage4_rows(name) for name in PARTNER_TABLES[1:]}

        for partner in distinct_partners(read_partners(self.layout)):
            accession = partner["accession_number"]
            raw = self.layout.partner_submission(accession).read_bytes()
            records = partner_records(partner, fetched[accession], raw, ok_records.get(accession))
            status = records.ownership_status
            derived = {
                "filings": [records.filing],
                "parties": records.parties,
                "documents": records.documents,
                "ownership": records.ownership,
                "ownership_status": [] if status is None else [status],
            }
            for name, rows in derived.items():
                with self.subTest(accession=accession, table=name):
                    self.assertEqual(as_table_rows(name, rows), rows_of(stored[name], accession))

    def test_partner_tables_write_only_stage4(self):
        def outside_stage4() -> dict[str, str]:
            digests = file_digests(self.layout.root)
            return {
                path: sha256 for path, sha256 in digests.items() if Path(path).parts[0] != "stage4"
            }

        before, lines_before = outside_stage4(), line_count(self.layout.runs)

        code, stdout, stderr = self.run_cli("partner-tables")

        self.assertEqual(code, 0, stderr)
        self.assertEqual(stderr, "")
        # `partner-tables` writes every Stage 4 table except `partners`.
        stage4 = self.layout.stage4_view
        written = [
            name for name in STAGE4_TABLES if name != "partners" and stage4.table(name).exists()
        ]
        self.assertEqual(written[: len(PARTNER_TABLES)], list(PARTNER_TABLES))
        self.assertEqual(
            stdout.splitlines(),
            [f"{name}: {read_table(stage4, name).num_rows}" for name in written],
        )
        self.assertEqual(outside_stage4(), before)
        runs = self.layout.runs.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(runs), lines_before + 1)
        self.assertEqual(json.loads(runs[-1])["step"], "partner-tables")

    def test_partner_tables_need_the_partner_list(self):
        # A root that has run Stage 3 and not `partners`.
        shutil.rmtree(self.layout.stage4)

        code, stdout, stderr = self.run_cli("partner-tables")

        path = self.layout.stage4_tables / "partners.parquet"
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, f"error: {path} is missing: run partners first\n")
        self.assertFalse(self.layout.stage4.exists())

    def test_the_stage4_root_still_rebuilds_stage3(self):
        code, lines = run_rebuild(self.layout, self.zip_path)

        self.assertEqual(code, 0, lines)
        self.assertEqual(lines[:11], ALL_EQUAL)


class FailedPartnerTests(CommandTestCase):
    def test_a_failed_partner_is_not_held(self):
        build_stage4_root(self, failing=frozenset({PARTNER_13D_A2}))
        stage4 = self.layout.stage4_view

        def rows(name: str) -> list[dict]:
            return rows_of(read_table(stage4, name).to_pylist(), PARTNER_13D_A2)

        self.assertFalse(self.layout.partner_submission(PARTNER_13D_A2).exists())
        ((fetch,), (filing,)) = rows("fetches"), rows("filings")
        self.assertEqual(fetch["outcome"], "not_found")
        self.assertEqual((filing["outcome"], filing["reason"]), ("not_found", "not_found"))
        for name in ("parties", "documents", "ownership"):
            with self.subTest(table=name):
                self.assertEqual(rows(name), [])
        (status,) = rows("ownership_status")
        self.assertEqual((status["record_count"], status["reason"]), (0, "not_found"))
        others = [row["outcome"] for row in read_table(stage4, "fetches").to_pylist()]
        self.assertEqual(others.count("ok"), len(PARTNERS) - 1)
