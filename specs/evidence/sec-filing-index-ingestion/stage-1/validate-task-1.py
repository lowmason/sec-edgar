from pathlib import Path
import csv, hashlib, json, re, subprocess
p = Path(__file__).resolve().parent
repo = p.parents[3]
m = json.loads((p / "protected-before-state.json").read_text())
for v in m["original_worktree"]:
    f = repo / v["path"]
    assert (not f.exists()) if v["before_status"] == "deleted" else hashlib.sha256(f.read_bytes()).hexdigest() == v["sha256"], v["path"]
for v in m["protected_documents"]:
    assert hashlib.sha256((repo / v["path"]).read_bytes()).hexdigest() == v["sha256"], v["path"]
assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo).decode().strip() == m["actual_head"]
assert all(c["exit_code"] == 0 for c in json.loads((p / "baseline-commands.json").read_text()))
index = list(csv.DictReader((p / "index.csv").open()))
assert len(index) == 13
assert len({r["evidence_id"] for r in index}) == len(index)
for r in index:
    assert r["category"] in ["Verified documentation", "Source/probe observation", "Owner decision", "Assumption", "Reserved Stage 7 check"]
    artifact = Path(r["url_or_artifact"])
    if not artifact.is_absolute():
        artifact = repo / artifact
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == r["sha256"]
d = list(csv.DictReader((p / "discrepancies.csv").open()))
assert len(d) == 13
assert all(r["status"] in ["open", "resolved", "reserved_stage_7"] for r in d)
assert sum(r["blocking"] == "true" and r["status"] == "open" for r in d) == 9
for r in d:
    assert set(r["evidence_ids"].split(";")) <= {r["evidence_id"] for r in index}
b = (p / "baseline.md").read_text()
assert len(re.findall(r"^\| \d+ \| \d{4} Q[1-4] \|", b, re.M)) == 68
assert len(re.findall(r"^\| \d+ \| \d{4} Q[1-4] \| \d+ \|", b, re.M)) == 48
assert "AUTHORIZED — NOT ACTIVATED" in (p / "access-window.md").read_text()
assert hashlib.sha256((p / "probe-setup-proposal.md").read_bytes()).hexdigest() == "5946673f1cdd8fc3a346ae61b4a2d711cccb3fa660031060a412f1b8e5ffeb84"
print("PASS: original hashes/deletions and HEAD preserved; 7 baseline commands exit 0; 13 evidence IDs/hashes/categories valid; 13 discrepancies (9 open/blocking); 68 requested quarters / 48 dev; access window authorized, not activated.")

