import contextlib
import datetime
import io
import json
import random
import tempfile
import unittest
from pathlib import Path

import pyarrow as pa

from sec_filing_data import cli
from sec_filing_data.layout import Layout
from sec_filing_data.sample import QUOTA_FORMS, draw_sample
from sec_filing_data.tables import SCHEMAS, read_table, write_table


def accession_of(number: int) -> str:
    return f"0000000001-26-{number:06d}"


def index_row(
    line_number: int,
    accession: str,
    form_type: str,
    *,
    cik: int = 1000,
    company_name: str = "ACME CORP",
    date_filed: datetime.date = datetime.date(2026, 7, 1),
) -> dict:
    return {
        "line_number": line_number,
        "cik": cik,
        "company_name": company_name,
        "form_type": form_type,
        "date_filed": date_filed,
        "filename": f"edgar/data/{cik}/{accession}.txt",
        "accession_number": accession,
    }


def build_index(spec: list[tuple[str, int]]) -> list[dict]:
    """One row per accession: `spec` is a list of (form type, number of accessions)."""
    rows = []
    for form_type, count in spec:
        for _ in range(count):
            number = len(rows) + 1
            rows.append(index_row(number, accession_of(number), form_type))
    return rows


def mixed_index() -> list[dict]:
    """3 10-K, 1 Form 5, one accession under two form types, and 30 8-K."""
    rows = build_index([("10-K", 3), ("5", 1)])
    shared = accession_of(100)
    rows.append(index_row(100, shared, "SC 13D/A"))
    rows.append(index_row(101, shared, "SC TO-T/A"))
    for number in range(102, 132):
        rows.append(index_row(number, accession_of(number), "8-K"))
    return rows


class DrawSampleTests(unittest.TestCase):
    def test_quota_then_repeated_then_uniform(self):
        rows = draw_sample(mixed_index(), size=10, quota=2)

        self.assertEqual(
            [row["stratum"] for row in rows],
            ["quota"] * 3 + ["repeated"] + ["uniform"] * 6,
        )
        self.assertEqual([row["draw"] for row in rows], list(range(1, 11)))
        accessions = [row["accession_number"] for row in rows]
        self.assertEqual(len(set(accessions)), 10)
        self.assertEqual(
            [row["form_type"] for row in rows[:3]], ["10-K", "10-K", "5"]
        )
        self.assertEqual(rows[3]["form_type"], "SC 13D/A;SC TO-T/A")
        self.assertEqual(rows[3]["accession_number"], accession_of(100))

    def test_one_row_per_accession(self):
        shared = accession_of(7)
        rows = [
            # Listed out of line order: the smaller line_number still wins.
            index_row(
                9, shared, "10-K", cik=222, company_name="SECOND LINE",
                date_filed=datetime.date(2026, 7, 9),
            ),
            index_row(
                8, shared, "10-K", cik=111, company_name="FIRST LINE",
                date_filed=datetime.date(2026, 7, 8),
            ),
            index_row(10, accession_of(8), "8-K"),
        ]

        sample = draw_sample(rows, size=10, quota=5)

        drawn = [row for row in sample if row["accession_number"] == shared]
        self.assertEqual(len(drawn), 1)
        self.assertEqual(drawn[0]["stratum"], "quota")
        self.assertEqual(drawn[0]["form_type"], "10-K")
        self.assertEqual(drawn[0]["cik"], 111)
        self.assertEqual(drawn[0]["company_name"], "FIRST LINE")
        self.assertEqual(drawn[0]["date_filed"], datetime.date(2026, 7, 8))
        self.assertEqual(drawn[0]["filename"], f"edgar/data/111/{shared}.txt")
        self.assertEqual(
            drawn[0]["url"], f"https://www.sec.gov/Archives/edgar/data/111/{shared}.txt"
        )

    def test_one_form_type_under_two_ciks_is_not_repeated(self):
        shared = accession_of(1)
        rows = [
            index_row(1, shared, "8-K", cik=1),
            index_row(2, shared, "8-K", cik=2),
        ]

        sample = draw_sample(rows, size=10, quota=5)

        self.assertEqual([row["stratum"] for row in sample], ["uniform"])
        self.assertEqual(sample[0]["form_type"], "8-K")

    def test_seed_is_deterministic(self):
        rows = mixed_index()

        first = draw_sample(rows, size=10, quota=2, seed=1)
        again = draw_sample(rows, size=10, quota=2, seed=1)
        other = draw_sample(rows, size=10, quota=2, seed=2)

        self.assertEqual(first, again)
        self.assertNotEqual(first, other)

    def test_input_order_does_not_change_the_draw(self):
        rows = mixed_index()
        shuffled = list(rows)
        random.Random(0).shuffle(shuffled)

        self.assertEqual(
            draw_sample(rows, size=10, quota=2), draw_sample(shuffled, size=10, quota=2)
        )

    def test_quota_draws_from_sorted_accessions_in_sample_order(self):
        rows = build_index([("10-K", 12)])
        rows.reverse()  # input order must not matter
        candidates = sorted(row["accession_number"] for row in rows)

        sample = draw_sample(rows, size=3, quota=3, seed=7)

        expected = random.Random(7).sample(candidates, 3)
        self.assertEqual([row["accession_number"] for row in sample], expected)
        self.assertEqual({row["stratum"] for row in sample}, {"quota"})

    def test_quota_stops_at_the_candidates_there_are(self):
        rows = build_index([("10-K", 3), ("8-K", 5)])

        sample = draw_sample(rows, size=100, quota=20)

        self.assertEqual(
            [row["stratum"] for row in sample], ["quota"] * 3 + ["uniform"] * 5
        )

    def test_quota_forms_run_in_order_and_skip_an_accession_already_drawn(self):
        both = accession_of(1)
        rows = [
            index_row(1, both, "10-K"),
            index_row(2, both, "10-Q"),
            index_row(3, accession_of(2), "10-Q"),
            index_row(4, accession_of(3), "13F-HR"),
        ]

        sample = draw_sample(rows, size=10, quota=5)

        self.assertEqual(
            [(row["stratum"], row["form_type"], row["accession_number"]) for row in sample],
            [
                ("quota", "10-K", both),
                ("quota", "10-Q", accession_of(2)),
                ("quota", "13F-HR", accession_of(3)),
            ],
        )

    def test_quota_forms_are_the_original_types_only(self):
        self.assertEqual(
            QUOTA_FORMS,
            ("10-K", "10-Q", "3", "4", "5", "SCHEDULE 13D", "SCHEDULE 13G", "13F-HR"),
        )
        rows = build_index([("10-K/A", 2), ("13F-NT", 2), ("SC 13D/A", 2)])

        sample = draw_sample(rows, size=10, quota=5)

        self.assertEqual({row["stratum"] for row in sample}, {"uniform"})

    def test_uniform_never_asks_for_a_negative_count(self):
        sample = draw_sample(mixed_index(), size=2, quota=2)

        self.assertEqual(
            [row["stratum"] for row in sample], ["quota"] * 3 + ["repeated"]
        )

    def test_sample_rows_match_the_sample_schema(self):
        rows = draw_sample(mixed_index(), size=10, quota=2)

        table = pa.Table.from_pylist(rows, schema=SCHEMAS["sample"])

        self.assertEqual(table.num_rows, 10)
        for row in rows:
            self.assertEqual(set(row), set(SCHEMAS["sample"].names))


class SampleCommandTests(unittest.TestCase):
    def make_folder(self) -> Path:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        return Path(folder.name)

    def test_sample_command(self):
        # 25 10-K, 2 Form 4, 1 repeated accession and 30 8-K.
        index_rows = build_index([("10-K", 25), ("4", 2)])
        shared = accession_of(900)
        index_rows.append(index_row(900, shared, "SC 13D/A"))
        index_rows.append(index_row(901, shared, "SC TO-T/A"))
        for number in range(902, 932):
            index_rows.append(index_row(number, accession_of(number), "8-K"))
        root = self.make_folder() / "root"
        write_table(Layout(root), "index", index_rows)

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            status = cli.main(["sample", "--out", str(root)])

        self.assertEqual(status, 0)
        self.assertEqual(
            stdout.getvalue().splitlines(),
            [
                "quota: 22",
                "repeated: 1",
                "uniform: 35",
                "10-K: 20",
                "10-Q: 0",
                "3: 0",
                "4: 2",
                "5: 0",
                "SCHEDULE 13D: 0",
                "SCHEDULE 13G: 0",
                "13F-HR: 0",
            ],
        )
        table = read_table(Layout(root), "sample")
        self.assertEqual(table.schema, SCHEMAS["sample"])
        self.assertEqual(table.num_rows, 58)
        self.assertEqual(table["draw"].to_pylist(), list(range(1, 59)))
        self.assertEqual(table.to_pylist(), draw_sample(index_rows))
        written = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
        self.assertEqual(written, ["runs.jsonl", "tables/index.parquet", "tables/sample.parquet"])
        steps = [
            json.loads(line)["step"]
            for line in (root / "runs.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(steps, ["sample"])

    def test_sample_command_needs_the_index_table(self):
        root = self.make_folder() / "root"

        with self.assertRaises(FileNotFoundError):
            cli.main(["sample", "--out", str(root)])
        self.assertFalse((root / "tables" / "sample.parquet").exists())


if __name__ == "__main__":
    unittest.main()
