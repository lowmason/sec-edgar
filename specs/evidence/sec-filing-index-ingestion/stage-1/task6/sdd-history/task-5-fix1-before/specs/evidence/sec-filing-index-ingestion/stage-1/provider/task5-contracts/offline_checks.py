"""Retain local DST observations and verify Stage 1 indexed artifact bytes."""

import csv
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import TZPATH, ZoneInfo

REPOSITORY = Path(__file__).resolve().parents[6]
EVIDENCE = REPOSITORY / "specs/evidence/sec-filing-index-ingestion/stage-1"
OUTPUT = EVIDENCE / "provider/task5-contracts"
DATES = (
    ("2026-03-01", 10, 11),
    ("2026-03-07", 10, 11),
    ("2026-03-08", 9, 10),
    ("2026-03-15", 9, 10),
    ("2026-10-25", 9, 10),
    ("2026-10-31", 9, 10),
    ("2026-11-01", 10, 11),
    ("2026-11-08", 10, 11),
)


def write_json(name, value):
    (OUTPUT / name).write_text(json.dumps(value, indent=2) + "\n")


def observe_dst():
    zone = ZoneInfo("America/New_York")
    observations = []
    for date, daily_hour, reconciliation_hour in DATES:
        for local_hour, expected_hour, kind in (
            (5, daily_hour, "daily"),
            (6, reconciliation_hour, "Sunday reconciliation offset expectation"),
        ):
            local = datetime.fromisoformat(f"{date}T{local_hour:02}:00:00").replace(tzinfo=zone)
            utc = local.astimezone(timezone.utc)
            assert utc.hour == expected_hour, (local, utc, expected_hour)
            observations.append({"local": local.isoformat(), "utc": utc.isoformat(),
                                 "weekday": local.strftime("%A"), "kind": kind,
                                 "reconciliation_due": local.weekday() == 6,
                                 "expected_utc_hour": expected_hour, "passed": True})
    zone_files = [Path(path) / "America/New_York" for path in TZPATH]
    retained_zone_files = [
        {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        for path in zone_files if path.is_file()
    ]
    version_files = [Path(path) / "tzdata.zi" for path in TZPATH]
    zone_versions = [path.read_text().splitlines()[0] for path in version_files if path.is_file()]
    write_json("dst-observation.json", {
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(), "zone": str(zone), "tzpath": list(TZPATH),
        "zone_versions": zone_versions, "zone_files": retained_zone_files,
        "observations": observations,
        "limitation": "Local zoneinfo conversion only; no ADF Windows-zone execution proof.",
    })
    return len(observations)


def verify_index():
    failures = []
    checked = 0
    with (EVIDENCE / "index.csv").open(newline="") as handle:
        for row in csv.DictReader(handle):
            local_reference = row["url_or_artifact"].split("; ")[-1]
            path = REPOSITORY / local_reference
            expected_hash = row["sha256"]
            if not expected_hash:
                continue
            checked += 1
            if not path.is_file():
                failures.append({"id": row["evidence_id"], "reason": "missing", "path": str(path)})
            elif hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
                failures.append({"id": row["evidence_id"], "reason": "hash mismatch", "path": str(path)})
    assert not failures, failures
    return checked


def main():
    dst_count = observe_dst()
    index_count = verify_index()
    result = {"verified_at_utc": datetime.now(timezone.utc).isoformat(),
              "dst_assertions": dst_count, "indexed_hashes_checked": index_count,
              "failures": [], "exit_code": 0}
    write_json("offline-verification.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
