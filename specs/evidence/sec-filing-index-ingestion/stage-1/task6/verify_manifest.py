"""Verify the exact Task 6 capture and its separate draft-freeze receipt offline."""

import hashlib
import json
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[5]
TASK = Path(__file__).resolve().parent


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest_path = TASK / "evidence-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    assert manifest["acceptance"] == "pending"
    records = manifest["records"]
    assert len({record["path"] for record in records}) == len(records)
    for record in records:
        path = REPOSITORY / record["path"]
        assert path.is_file(), record
        assert path.stat().st_size == record["bytes"], record
        assert sha256(path) == record["sha256"], record
    assert str(manifest_path.relative_to(REPOSITORY)) not in {record["path"] for record in records}
    freeze = json.loads((TASK / "draft-freeze.json").read_text())
    assert freeze["acceptance"] == "pending"
    assert freeze["evidence_manifest_sha256"] == sha256(manifest_path)
    finding = REPOSITORY / freeze["finding_path"]
    retained = REPOSITORY / freeze["immutable_finding_path"]
    assert sha256(finding) == sha256(retained) == freeze["finding_sha256"]
    versions = json.loads((TASK / "draft-artifact-versions.json").read_text())["records"]
    for record in versions:
        original = REPOSITORY / record["source_path"]
        immutable = REPOSITORY / record["immutable_path"]
        assert original.read_bytes() == immutable.read_bytes(), record
        assert immutable.stat().st_size == record["bytes"] and sha256(immutable) == record["sha256"], record
    print(json.dumps({"result": "PASS", "manifest_files_verified": len(records),
                      "draft_versions_verified": len(versions),
                      "finding_sha256": freeze["finding_sha256"],
                      "evidence_manifest_sha256": freeze["evidence_manifest_sha256"],
                      "acceptance": "pending", "capture_exclusions": manifest["exclusions"]}, indent=2))


if __name__ == "__main__":
    main()
