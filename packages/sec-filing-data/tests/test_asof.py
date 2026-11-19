"""The as-of query: each record of the sample and of its partners that was public by a time."""

import contextlib
import io
import json
import shutil
import subprocess
import sys
import unittest
from collections import Counter
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from unittest import mock

import pyarrow as pa

from sec_filing_data import cli, manifest, version
from sec_filing_data.asof import (
    ASOF_TABLES,
    HELD_IN,
    AsOfRefused,
    ManifestUsed,
    answer,
    known_from,
    parse_at,
)
from sec_filing_data.index import INDEX_LAST_MODIFIED_AT
from sec_filing_data.tables import SCHEMAS, read_table, write_table
from tests import TEST_COMMIT
from tests.stage4_root import (
    INDEX_FILINGS,
    LAST_MODIFIED,
    PARTNER_13D_A1,
    PARTNER_13D_A2,
    PARTNER_D,
    PARTNERS,
    SAMPLED,
    SAMPLED_13D,
    SAMPLED_13F,
    SAMPLED_D_A,
    UNRELATED_10K,
    Stage4RootTestCase,
    build_stage4_root,
    write_both_manifests,
)
from tests.test_commands import CommandTestCase
from tests.test_rebuild import file_digests, line_count

ONE_MICROSECOND = timedelta(microseconds=1)
OTHER_COMMIT = "b" * 40
# After every `known_from` of the root, so every held record answers.
LATE = "2026-11-19"
# The tables that each set gives to the answer: `index` and `facts` come from `tables/` only,
# and `links` from `stage4/tables/` only.
FROM_TABLES = ("index", "filings", "parties", "documents", "facts", "ownership")
FROM_STAGE4 = ("filings", "parties", "documents", "ownership", "links")


def known(accession: str) -> datetime:
    """The `known_from` of a fetched filing of the root: its `Last-Modified` time."""
    return parsedate_to_datetime(LAST_MODIFIED[accession])


def index_rows(accessions) -> int:
    """The number of `index` rows of `accessions`: one for each CIK."""
    return sum(len(INDEX_FILINGS[accession][2]) for accession in accessions)


def accessions_of(table: pa.Table) -> list[str]:
    return table["accession_number"].to_pylist()


def added_columns(name: str) -> list[str]:
    """The columns that the answer adds to table `name`. `links` stores its `held_in` (C9)."""
    return ["known_from"] if name == "links" else ["known_from", "held_in"]


class ParseAtTests(unittest.TestCase):
    def test_parse_at(self):
        cases = {
            # The end of the day in New York: EDT, then EST.
            "2026-08-14": datetime(2026, 8, 15, 3, 59, 59, 999999, tzinfo=UTC),
            "2026-01-15": datetime(2026, 1, 16, 4, 59, 59, 999999, tzinfo=UTC),
            # The two clock changes of 2026.
            "2026-03-08": datetime(2026, 3, 9, 3, 59, 59, 999999, tzinfo=UTC),
            "2026-11-01": datetime(2026, 11, 2, 4, 59, 59, 999999, tzinfo=UTC),
            "2026-08-14T12:00:00-04:00": datetime(2026, 8, 14, 16, tzinfo=UTC),
            "2026-08-14T16:00:00Z": datetime(2026, 8, 14, 16, tzinfo=UTC),
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                at = parse_at(text)
                self.assertEqual(at, expected)
                self.assertIs(at.tzinfo, UTC)

        for text in ("2026-08-14T12:00:00", "2026-02-30", "20260814", "soon"):
            with self.subTest(text=text), self.assertRaises(ValueError) as caught:
                parse_at(text)
            self.assertIn(text, str(caught.exception))

    def test_known_from(self):
        fetched = datetime(2026, 8, 14, 21, 0, 0, tzinfo=UTC)
        modified = datetime(2026, 8, 14, 20, 5, 40, tzinfo=UTC)

        self.assertEqual(
            known_from({"outcome": "ok", "last_modified_at": modified, "fetched_at": fetched}),
            modified,
        )
        self.assertEqual(
            known_from({"outcome": "ok", "last_modified_at": None, "fetched_at": fetched}),
            fetched,
        )
        failed = {"outcome": "not_found", "last_modified_at": modified, "fetched_at": fetched}
        self.assertIsNone(known_from(failed))


class AnswerTests(Stage4RootTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.tables_manifest, self.stage4_manifest = write_both_manifests(self)

    def answer_at(self, at: str | datetime):
        return answer(self.layout.root, parse_at(at) if isinstance(at, str) else at)

    def refusal(self) -> str:
        """The message of the `AsOfRefused` that the root gives at LATE."""
        with self.assertRaises(AsOfRefused) as caught:
            self.answer_at(LATE)
        return str(caught.exception)

    def test_answer_names_its_time_and_manifests(self):
        result = self.answer_at("2026-08-14T12:00:00-04:00")

        self.assertEqual(result.at, datetime(2026, 8, 14, 16, tzinfo=UTC))
        self.assertIs(result.at.tzinfo, UTC)
        self.assertEqual(
            result.manifests,
            tuple(
                ManifestUsed(set_name, path, manifest.sha256_of(path))
                for set_name, path in (
                    ("tables", self.tables_manifest),
                    ("stage4", self.stage4_manifest),
                )
            ),
        )
        self.assertEqual(list(result.tables), list(ASOF_TABLES))

    def test_answer_needs_an_offset(self):
        with self.assertRaises(ValueError):
            answer(self.layout.root, datetime(2026, 11, 19, 12, 0, 0))

    def test_index_rows_take_their_filings_known_from(self):
        before = self.answer_at(INDEX_LAST_MODIFIED_AT - ONE_MICROSECOND).tables["index"]
        at = self.answer_at(INDEX_LAST_MODIFIED_AT).tables["index"]

        counts = Counter(before["held_in"].to_pylist())
        self.assertEqual(
            {held_in: counts[held_in] for held_in in HELD_IN},
            {"sample": index_rows(SAMPLED), "partner": index_rows(PARTNERS), "index": 0},
        )
        for row in before.to_pylist():
            self.assertEqual(row["known_from"], known(row["accession_number"]))
        self.assertEqual(at.num_rows, read_table(self.layout, "index").num_rows)
        unheld = [row for row in at.to_pylist() if row["held_in"] == "index"]
        self.assertEqual(len(unheld), index_rows([UNRELATED_10K]))
        for row in unheld:
            self.assertEqual(row["accession_number"], UNRELATED_10K)
            self.assertEqual(row["known_from"], INDEX_LAST_MODIFIED_AT)

    def test_the_cutoff_is_inclusive(self):
        cutoff = known(SAMPLED_13F)

        at = self.answer_at(cutoff).tables["filings"]
        before = self.answer_at(cutoff - ONE_MICROSECOND).tables["filings"]

        (row,) = (row for row in at.to_pylist() if row["accession_number"] == SAMPLED_13F)
        self.assertEqual(row["known_from"], cutoff)
        self.assertNotIn(SAMPLED_13F, accessions_of(before))

    def test_an_answer_keeps_every_stored_value(self):
        result = self.answer_at(LATE)

        for name in ASOF_TABLES:
            with self.subTest(table=name):
                table = result.tables[name]
                stored = [
                    *(read_table(self.layout, name).to_pylist() if name in FROM_TABLES else []),
                    *(
                        read_table(self.layout.stage4_view, name).to_pylist()
                        if name in FROM_STAGE4
                        else []
                    ),
                ]
                added = added_columns(name)
                self.assertEqual(table.column_names, SCHEMAS[name].names + added)
                self.assertTrue(table.drop_columns(added).schema.equals(SCHEMAS[name]))
                self.assertEqual(table.schema.field("known_from").type, pa.timestamp("us", "UTC"))
                self.assertEqual(table.schema.field("held_in").type, pa.string())
                self.assertEqual(table.drop_columns(added).to_pylist(), stored)

    def test_records_are_held_in_their_set(self):
        result = self.answer_at(LATE)

        for name in ("filings", "parties", "documents", "ownership"):
            with self.subTest(table=name):
                expected = ["sample"] * read_table(self.layout, name).num_rows + ["partner"] * (
                    read_table(self.layout.stage4_view, name).num_rows
                )
                self.assertEqual(result.tables[name]["held_in"].to_pylist(), expected)
        stored = read_table(self.layout.stage4_view, "links")["held_in"].to_pylist()
        self.assertEqual(result.tables["links"]["held_in"].to_pylist(), stored)
        self.assertEqual(set(result.tables["facts"]["held_in"].to_pylist()) - {"sample"}, set())

    def test_the_pairs_answer_in_their_own_order(self):
        # (the filing known first, the filing known second): the forward pair is (original,
        # amendment), and the reverse pair is (amendment, original).
        for first, second in ((SAMPLED_13D, PARTNER_13D_A1), (SAMPLED_D_A, PARTNER_D)):
            earlier, later = known(first), known(second)
            self.assertLess(earlier, later)
            between = earlier + (later - earlier) / 2
            for at, expected in (
                (earlier - ONE_MICROSECOND, set()),
                (between, {first}),
                (later, {first, second}),
            ):
                result = self.answer_at(at)
                for name in ASOF_TABLES:
                    with self.subTest(pair=(first, second), at=at, table=name):
                        answered = set(accessions_of(result.tables[name])) & {first, second}
                        if name in ("index", "filings", "parties", "documents"):
                            self.assertEqual(answered, expected)
                        else:
                            self.assertLessEqual(answered, expected)

    def test_answer_refuses_a_changed_table_file(self):
        parties = self.layout.table("parties")
        original = parties.read_bytes()
        with self.subTest("one byte appended"):
            parties.write_bytes(original + b"\0")
            self.assertIn(str(parties), self.refusal())
        parties.write_bytes(original)

        with self.subTest("one value changed"):
            links = self.layout.stage4_view.table("links")
            before = links.read_bytes()
            rows = read_table(self.layout.stage4_view, "links").to_pylist()
            rows[0]["link_problem"] = "changed"
            write_table(self.layout.stage4_view, "links", rows)
            self.assertNotEqual(links.read_bytes(), before)
            self.assertIn(str(links), self.refusal())

    def test_answer_refuses_a_changed_stamp_entry(self):
        listed = json.loads(self.tables_manifest.read_text(encoding="utf-8"))
        (entry,) = (
            entry for entry in listed["outputs"] if entry["path"] == "tables/parties.parquet"
        )
        entry["python_version"] = "0.0.0"
        self.tables_manifest.write_text(json.dumps(listed, sort_keys=True, indent=2) + "\n")

        message = self.refusal()

        self.assertIn(str(self.layout.table("parties")), message)
        self.assertIn("0.0.0", message)

    def test_answer_refuses_a_missing_manifest(self):
        for path in (self.tables_manifest, self.stage4_manifest):
            with self.subTest(manifest=path.name):
                text = path.read_bytes()
                path.unlink()
                self.assertIn(str(path), self.refusal())
                path.write_bytes(text)

    def test_answer_refuses_a_root_without_stage4_tables(self):
        shutil.rmtree(self.layout.stage4_tables)

        self.assertIn(str(self.layout.stage4_tables), self.refusal())

    def test_answer_refuses_two_versions_in_a_set(self):
        rows = read_table(self.layout, "sample").to_pylist()
        other = version.Checkout(OTHER_COMMIT, True, None)
        with mock.patch.object(version, "current_checkout", return_value=other):
            write_table(self.layout, "sample", rows)

        message = self.refusal()

        self.assertIn(TEST_COMMIT, message)
        self.assertIn(OTHER_COMMIT, message)

    def test_answer_refuses_a_changed_builds_on(self):
        listed = json.loads(self.tables_manifest.read_text(encoding="utf-8"))
        listed["added"] = "a key that changes the file"
        self.tables_manifest.write_text(json.dumps(listed, sort_keys=True, indent=2) + "\n")

        self.assertIn(str(self.stage4_manifest), self.refusal())

    def test_an_answer_before_every_known_from_is_empty(self):
        result = self.answer_at("2026-01-01")

        for name in ASOF_TABLES:
            with self.subTest(table=name):
                table = result.tables[name]
                self.assertEqual(table.num_rows, 0)
                self.assertEqual(table.column_names, SCHEMAS[name].names + added_columns(name))
                self.assertIn("held_in", table.column_names)


class FailedPartnerTests(CommandTestCase):
    run_cli = Stage4RootTestCase.run_cli

    def test_a_failed_partner_never_answers(self):
        self.zip_path = build_stage4_root(self, failing=frozenset({PARTNER_13D_A2}))
        write_both_manifests(self)

        late = answer(self.layout.root, parse_at(LATE))
        before = answer(self.layout.root, INDEX_LAST_MODIFIED_AT - ONE_MICROSECOND)
        at = answer(self.layout.root, INDEX_LAST_MODIFIED_AT)

        for name in ASOF_TABLES[1:]:
            with self.subTest(table=name):
                self.assertNotIn(PARTNER_13D_A2, accessions_of(late.tables[name]))
        self.assertNotIn(PARTNER_13D_A2, accessions_of(before.tables["index"]))
        rows = [
            row
            for row in at.tables["index"].to_pylist()
            if row["accession_number"] == PARTNER_13D_A2
        ]
        self.assertEqual(len(rows), index_rows([PARTNER_13D_A2]))
        for row in rows:
            self.assertEqual((row["known_from"], row["held_in"]), (INDEX_LAST_MODIFIED_AT, "index"))


class AsOfUsageTests(CommandTestCase):
    def test_a_bad_at_is_a_usage_error(self):
        for text in ("2026-02-30", "2026-08-14T12:00", "soon"):
            with self.subTest(at=text):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
                    cli.main(["asof", "--out", str(self.layout.root), "--at", text])

                self.assertEqual(raised.exception.code, 2)
                self.assertIn(text, stderr.getvalue())
                self.assertFalse(self.layout.runs.exists())


class AsOfCommandTests(Stage4RootTestCase):
    def summary(self, tables_manifest: Path, stage4_manifest: Path) -> list[str]:
        """The summary of `asof` at LATE, when every row of the root answers."""
        stage4 = self.layout.stage4_view

        def count(view, name: str) -> int:
            return read_table(view, name).num_rows

        counts = {
            "index": {
                "sample": index_rows(SAMPLED),
                "partner": index_rows(PARTNERS),
                "index": index_rows([UNRELATED_10K]),
            },
            "facts": {"sample": count(self.layout, "facts")},
            "links": Counter(read_table(stage4, "links")["held_in"].to_pylist()),
        }
        for name in ("filings", "parties", "documents", "ownership"):
            counts[name] = {"sample": count(self.layout, name), "partner": count(stage4, name)}
        lines = [
            "at: 2026-11-20T04:59:59.999999+00:00",
            f"manifest tables: {tables_manifest} {manifest.sha256_of(tables_manifest)}",
            f"manifest stage4: {stage4_manifest} {manifest.sha256_of(stage4_manifest)}",
        ]
        for name in ASOF_TABLES:
            held = counts[name]
            total = sum(held.values())
            lines.append(
                f"{name}: {total} rows, sample {held.get('sample', 0)},"
                f" partner {held.get('partner', 0)}, index {held.get('index', 0)}"
            )
        return lines

    def test_asof_prints_counts_and_rows(self):
        summary = self.summary(*write_both_manifests(self))

        code, stdout, stderr = self.run_cli("asof", "--at", LATE)
        self.assertEqual((code, stderr), (0, ""))
        self.assertEqual(stdout.splitlines(), summary)

        code, stdout, stderr = self.run_cli("asof", "--at", LATE, "--table", "filings")
        self.assertEqual(code, 0)
        self.assertEqual(stderr.splitlines(), summary)
        rows = [json.loads(line) for line in stdout.splitlines()]
        self.assertEqual(len(rows), len(SAMPLED) + len(PARTNERS))
        for row in rows:
            self.assertEqual(list(row), SCHEMAS["filings"].names + ["known_from", "held_in"])
            self.assertEqual(
                datetime.fromisoformat(row["known_from"]), known(row["accession_number"])
            )

        code, stdout, _ = self.run_cli("asof", "--at", LATE, "--table", "index")
        self.assertEqual(code, 0)
        for row in map(json.loads, stdout.splitlines()):
            self.assertEqual(row["date_filed"], INDEX_FILINGS[row["accession_number"]][1])

    def test_asof_refuses_before_the_stage4_manifest(self):
        code, _, stderr = self.run_cli("manifest", "--set", "tables", "--zip", str(self.zip_path))
        self.assertEqual((code, stderr), (0, ""))
        stage4_manifest = manifest.manifest_path(self.layout, "stage4", TEST_COMMIT)

        code, stdout, stderr = self.run_cli("asof", "--at", LATE)

        self.assertEqual((code, stdout), (1, ""))
        self.assertTrue(stderr.startswith("error: "), stderr)
        self.assertIn(str(stage4_manifest), stderr)
        self.assertEqual(stderr.count("\n"), 1)

    def test_asof_runs_on_a_dirty_tree(self):
        write_both_manifests(self)
        dirty = version.Checkout(TEST_COMMIT, False, "uncommitted changes in uv.lock")

        with mock.patch.object(version, "current_checkout", lambda: dirty):
            code, _, stderr = self.run_cli("asof", "--at", LATE)

        self.assertEqual((code, stderr), (0, ""))
        last = json.loads(self.layout.runs.read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(last["step"], "asof")
        self.assertIs(last["tree_clean"], False)

    def test_asof_writes_only_its_run_line(self):
        write_both_manifests(self)
        digests = file_digests(self.layout.root)
        runs = self.layout.runs.read_text(encoding="utf-8").splitlines()

        code, _, _ = self.run_cli("asof", "--at", LATE)

        self.assertEqual(code, 0)
        self.assertEqual(file_digests(self.layout.root), digests)
        after = self.layout.runs.read_text(encoding="utf-8").splitlines()
        self.assertEqual(line_count(self.layout.runs), len(runs) + 1)
        self.assertEqual(after[: len(runs)], runs)
        self.assertEqual(json.loads(after[-1])["step"], "asof")

    def test_asof_never_loads_requests(self):
        write_both_manifests(self)
        code = (
            "import sys\n"
            "from sec_filing_data import cli\n"
            "code = cli.main(['asof', '--out', sys.argv[1], '--at', '2026-11-19'])\n"
            "print(code)\n"
            "print('requests' in sys.modules)\n"
        )

        result = subprocess.run(
            [sys.executable, "-c", code, str(self.layout.root)],
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertEqual(result.stdout.splitlines()[-2:], ["0", "False"])


if __name__ == "__main__":
    unittest.main()
