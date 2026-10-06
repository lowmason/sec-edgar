"""Read-only offline checks for the Stage 1 documentation assembly."""

import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[5]
EVIDENCE = REPOSITORY / "specs/evidence/sec-filing-index-ingestion/stage-1"
TASK = EVIDENCE / "task6"
APPROVAL = "321c93af78b54c7e63efbb0e69252c69a238fec6"
R3_HASH = "038cb2ddcd2ca444d7a3855a4686cb457aa13bd373c767bee854ed657d59f944"


def read_json(path):
    return json.loads(path.read_text())


def read_csv(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*arguments):
    result = subprocess.run(["git", *arguments], cwd=REPOSITORY, capture_output=True, check=True)
    return result.stdout


def check_retention():
    preexisting = read_json(TASK / "pre-task6-artifact-hashes.json")["records"]
    allowed = {"decisions.md", "discrepancies.csv", "index.csv"}
    for record in preexisting:
        path = REPOSITORY / record["path"]
        if path.parent == EVIDENCE and path.name in allowed:
            continue
        assert path.is_file(), record
        assert len(path.read_bytes()) == record["bytes"], record
        assert sha256(path) == record["sha256"], record
    counts = {}
    for name in ("sdd-retention-map.json", "contract-retention-map.json"):
        records = read_json(TASK / name)["records"]
        for record in records:
            durable = REPOSITORY / record["durable_path"]
            assert durable.is_file(), record
            assert len(durable.read_bytes()) == record["bytes"], record
            assert sha256(durable) == record["sha256"], record
        counts[name] = len(records)
    before = (TASK / "sdd-history/task-6-before-index.csv").read_bytes()
    normalization = read_json(TASK / "index-id-normalization.json")
    corrected_lines = before.splitlines(keepends=True)
    for correction in normalization["changed_cells"]:
        offset = correction["csv_line"] - 1
        old = correction["old_id"].encode()
        new = correction["new_id"].encode()
        assert corrected_lines[offset].startswith(old + b",")
        corrected_lines[offset] = new + corrected_lines[offset][len(old):]
    assert (EVIDENCE / "index.csv").read_bytes().startswith(b"".join(corrected_lines))
    return {"preexisting_files": len(preexisting), "unchanged_except_named_live_registers": True,
            "index_exact_prior_bytes_except_four_documented_alias_ID_cells": True,
            "retention_maps": counts}


def check_protection():
    baseline = read_json(EVIDENCE / "protected-before-state.json")
    assert git("rev-parse", "HEAD").decode().strip() == APPROVAL
    for record in baseline["original_worktree"]:
        path = REPOSITORY / record["path"]
        if record["before_status"] == "deleted":
            assert not path.exists(), record
        else:
            assert len(path.read_bytes()) == record["bytes"], record
            assert sha256(path) == record["sha256"], record
    for record in baseline["protected_documents"]:
        assert sha256(REPOSITORY / record["path"]) == record["sha256"], record
    spec_path = "specs/sec-filing-index-ingestion-stage-1-spec.md"
    assert git("show", f"{APPROVAL}:{spec_path}") == (REPOSITORY / spec_path).read_bytes()
    assert git("diff", "--cached") == b""
    assert not (REPOSITORY / ".venv").exists()
    assert not (REPOSITORY / "uv.lock").exists()
    return {"approval_and_head": APPROVAL, "original_worktree": baseline["original_worktree"],
            "protected_documents_verified": len(baseline["protected_documents"]),
            "approval_spec_exact": True, "staged_diff_empty": True,
            "root_venv_and_lock_absent": True}


def check_accounting():
    quarterly = read_csv(EVIDENCE / "quarterly.csv")
    summaries = [row for row in quarterly if row["representation"] == "quarter_summary"]
    expected = {f"{year}Q{quarter}" for year in range(2010, 2027) for quarter in range(1, 5)}
    assert len(quarterly) == 372 and len(summaries) == len(expected) == 68
    assert {row["quarter"] for row in summaries} == expected
    assert all(row["source_status"] == "available" for row in summaries)
    assert sum(row["development_subset"] == "true" for row in summaries) == 48
    daily = read_csv(EVIDENCE / "daily.csv")
    directories = [row for row in daily if row["representation"] == "directory_summary"]
    assert len(daily) == 2176 and len(directories) == 69
    assert Counter(row["outcome"] for row in directories) == {"available": 36, "listed_uninspected": 33}
    ledger = read_csv(EVIDENCE / "requests.csv")
    state = read_json(EVIDENCE / "sec-window-state.json")
    assert len(ledger) == state["attempts"] == 150
    assert sum(int(row["received_bytes"]) for row in ledger) == state["received_bytes"] == 15293779
    assert all(row["exit_code"] == "0" and row["outcome"] == "success" for row in ledger)
    starts = [datetime.fromisoformat(row["start_utc"]) for row in ledger]
    assert all((later - earlier).total_seconds() >= 1 / 3 for earlier, later in zip(starts, starts[1:]))
    assert datetime.fromisoformat(state["closed_utc"]) < datetime.fromisoformat(state["deadline_utc"])
    return {"quarterly_rows": len(quarterly), "requested_quarters": len(summaries),
            "development_quarters": 48, "daily_rows": len(daily),
            "daily_quarter_directories_inspected": 35, "daily_quarters_listed_uninspected": 33,
            "SEC_attempts": len(ledger), "SEC_received_bytes": state["received_bytes"],
            "start_spacing_at_least_one_third_second": True, "SEC_closed_before_deadline": True}


def check_decisions_provider_runtime():
    discrepancies = read_csv(EVIDENCE / "discrepancies.csv")
    assert len(discrepancies) == 18
    assert all(row["status"] in {"open", "resolved", "reserved_stage_7"} for row in discrepancies)
    assert all(row["blocking"].lower() == "false" for row in discrepancies)
    dispositions = {row["id"]: row["status"] for row in discrepancies}
    assert dispositions["D-10"] == "open" and dispositions["D-11"] == "reserved_stage_7"
    for number in [1, 2, 3, 4, 5, 6, 7, 8, 14, 18]:
        assert dispositions[f"D-{number:02}"] == "resolved"
    proposal = EVIDENCE / f"versions/owner-decision-proposal-r3-{R3_HASH}.md"
    assert sha256(proposal) == R3_HASH
    for name in ("owner-decision-response-r3-part1.json", "owner-decision-response-r3-pending.json"):
        assert read_json(EVIDENCE / name)["accepted_proposal_sha256"] == R3_HASH
    stage7 = (EVIDENCE / "stage-7-checks.md").read_text()
    rows = [line for line in stage7.splitlines() if line.startswith("| S7-")]
    assert len(rows) == 22 and all(line.endswith("reserved/not_run |") for line in rows)
    provider = EVIDENCE / "provider/task5-contracts"
    hashes = read_json(provider / "sha256-manifest.json")
    for name, expected in hashes.items():
        assert sha256(provider / name) == expected, name
    regional = read_json(EVIDENCE / "provider/task5-fix1/regional-rows.json")
    assert len(regional["selected_rows"]) == 27
    assert all(row["CurrentState"] == "GA" for row in regional["selected_rows"])
    regional_source = EVIDENCE / "provider/task5-fix1-root-region/regional-table.html"
    assert sha256(regional_source) == regional["source_sha256"]
    source_text = regional_source.read_text()
    array_offset = source_text.index("[", source_text.index("const data"))
    source_rows, _ = json.JSONDecoder().raw_decode(source_text[array_offset:])
    assert len(source_rows) == regional["source_row_count"] == 17703
    for selected in regional["selected_rows"]:
        ordinal = selected["source_array_ordinal"]
        assert {key: value for key, value in selected.items() if key != "source_array_ordinal"} == source_rows[ordinal]
    dst = read_json(provider / "dst-observation.json")
    assert len(dst["observations"]) == 16 and all(row["passed"] for row in dst["observations"])
    commands = []
    exports = 0
    for name in ("resolve-02-artifacts", "validate-01-artifacts", "validate-02-artifacts"):
        directory = EVIDENCE / "runtime/results" / name
        commands.extend(read_json(path) for path in directory.glob("*.command.json"))
        exports += len(read_json(directory / "export-receipt.json")["artifacts"])
    assert len(commands) == 34 and all(command["exit_code"] == 0 for command in commands)
    assert exports == 158
    return {"discrepancy_dispositions": dispositions, "blocking_discrepancies": 0,
            "owner_R3_exact": True, "Stage7_reserved_not_run": len(rows),
            "current_contract_manifest_hashes": len(hashes), "regional_GA_rows": 27,
            "regional_source_rows_parsed_without_execution": len(source_rows),
            "retained_local_DST_assertions": 16, "successful_probe_command_exits": 34,
            "exported_artifacts": exports}


def check_index_and_links():
    rows = read_csv(EVIDENCE / "index.csv")
    assert len({row["evidence_id"] for row in rows}) == len(rows)
    local_count = 0
    for row in rows:
        for reference in row["url_or_artifact"].split(";"):
            reference = reference.strip()
            if reference.startswith(("https://", "http://")):
                continue
            assert reference and ".sdd/" not in reference, row
            path = REPOSITORY / reference
            assert path.is_file() and sha256(path) == row["sha256"], row
            local_count += 1
    links = []
    for document in (REPOSITORY / "specs/sec-filing-index-ingestion-stage-1-findings.md",
                     EVIDENCE / "readiness-checklist.md"):
        for target in re.findall(r"\]\(([^)]+)\)", document.read_text()):
            if target.startswith(("https://", "http://", "#")):
                continue
            path = (document.parent / target.split("#")[0]).resolve()
            assert path.exists(), (str(document), target)
            links.append(str(path.relative_to(REPOSITORY)))
    finding = (REPOSITORY / "specs/sec-filing-index-ingestion-stage-1-findings.md").read_text()
    assert len(re.findall(r"^## [1-9]\. ", finding, re.MULTILINE)) == 9
    assert "**PENDING — no final finding acceptance is recorded.**" in finding
    assert "accepted finding limitation" not in finding
    return {"index_rows": len(rows), "local_index_hashes": local_count,
            "finding_checklist_local_links": len(links), "nine_sections": True,
            "acceptance_pending": True,
            "claim_scan_limit": "Assertions check explicit acceptance boundary; material claims assessed against cited evidence, not proved by phrase matching."}


def main():
    results = {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
               "method": "Offline read-only byte/hash/CSV/retained-output/approval checks; no external requests",
               "preservation": check_retention(), "protection": check_protection(),
               "accounting": check_accounting(), "provider_decisions_runtime": check_decisions_provider_runtime(),
               "index_and_links": check_index_and_links(), "result": "PASS"}
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
