"""Append immutable Task 5 evidence and update only current decision dispositions."""

import csv
import hashlib
import io
from datetime import datetime, timezone
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[6]
EVIDENCE = REPOSITORY / "specs/evidence/sec-filing-index-ingestion/stage-1"
MUTABLE = {"decisions.md", "discrepancies.csv", "provider-review.md", "azure-contracts.md",
           "schedules.md", "stage-7-checks.md", "owner-decision-proposal.md", "task-5-report.md"}


def preserve(path):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    destination = EVIDENCE / "versions" / f"task5-{path.stem}-{digest}{path.suffix}"
    if destination.exists():
        assert destination.read_bytes() == path.read_bytes()
    else:
        destination.write_bytes(path.read_bytes())
    return destination, digest


def update_discrepancies():
    path = EVIDENCE / "discrepancies.csv"
    preserve(path)
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rows = list(reader)
    for row in rows:
        if row["id"] in {"D-01", "D-02", "D-03", "D-04"}:
            row.update({"blocking": "false", "status": "resolved_owner_selection; effective_stage7_reserved",
                        "accepted_revision": "Task5 owner proposal revision3 038cb2ddcd2ca444d7a3855a4686cb457aa13bd373c767bee854ed657d59f944",
                        "accepted_date": "root receipt 2026-10-06T01:26:57.382291+00:00; owner timestamp not supplied",
                        "proposed_resolution": "Explicit owner accepted D01–04 exact R3 selections; no deployment/action authority or effective assignment proof",
                        "evidence_ids": row["evidence_ids"] + ";E-T5-OWNER-PART1"})
    if not any(row["id"] == "D-18" for row in rows):
        rows.append(dict(zip(fields, ["D-18", "New 30s/4200s application observation policy requires owner decision",
            "E-T5-PROPOSAL", "Task5 Step2; parent4.8–4.9", "true",
            "Accept exact R3 D18 policy or record replacement; no deadline/unknown launch retry",
            "Lowell Mason", "", "", "open"])))
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def append_index():
    index = EVIDENCE / "index.csv"
    before = index.read_bytes()
    with index.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rows = list(reader)
    existing = {(row["url_or_artifact"], row["sha256"]) for row in rows}
    candidates = [EVIDENCE / name for name in MUTABLE if (EVIDENCE / name).is_file()]
    candidates += list(EVIDENCE.glob("owner-decision-*.json"))
    candidates += list((EVIDENCE / "versions").glob("owner-decision-proposal-r*.md"))
    candidates += [path for path in (EVIDENCE / "provider").glob("task5-*/**/*") if path.is_file()]
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields)
    added = 0
    for path in sorted(set(candidates)):
        immutable, digest = preserve(path) if path.name in MUTABLE else (path, hashlib.sha256(path.read_bytes()).hexdigest())
        reference = str(immutable.relative_to(REPOSITORY))
        if (reference, digest) in existing:
            continue
        special = {"owner-decision-response-r3-part1.json": "E-T5-OWNER-PART1",
                   "owner-decision-proposal-r3-038cb2ddcd2ca444d7a3855a4686cb457aa13bd373c767bee854ed657d59f944.md": "E-T5-PROPOSAL"}
        evidence_id = special.get(path.name, "E-T5-" + digest[:16].upper())
        is_acceptance = "owner-decision-response" in path.name
        row = dict.fromkeys(fields, "")
        row.update({"evidence_id": evidence_id, "claim": "Task5 retained " + path.name,
                    "category": "Owner decision" if is_acceptance else "Source/probe observation",
                    "method": "Retained exact bytes; public-source claim mapping and limits in associated metadata/notes",
                    "url_or_artifact": reference,
                    "accessed_or_received_at_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                    "versions": "Task5 selected version/policy recorded in artifact; retention time is not exact HTTP access time",
                    "result": "Retained sha256 verified bytes" if not is_acceptance else "Exact scoped owner answer retained",
                    "limitation": "Documentation/selection/local checks only; effective Azure/worker behavior reserved Stage7; source failures preserved",
                    "sha256": digest})
        writer.writerow(row)
        existing.add((reference, digest))
        added += 1
    with index.open("ab") as handle:
        handle.write(buffer.getvalue().encode())
    assert index.read_bytes().startswith(before)
    print(f"Appended {added} immutable Task5 references; prior index bytes preserved")


if __name__ == "__main__":
    update_discrepancies()
    append_index()
