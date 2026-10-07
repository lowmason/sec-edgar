from pathlib import Path
import csv
import hashlib
import importlib.metadata as metadata
import json
import platform
import re
import sys
import tomllib
import urllib.request
import zipfile

root = Path.cwd()
evidence = root / ".sdd/2-sec-filing-index-ingestion-stage-2-spec/task1-evidence"
lock = tomllib.loads((root / "uv.lock").read_text())
normalize = lambda name: re.sub(r"[-_.]+", "-", name).lower()
accepted = {normalize(row["distribution"]): row for row in csv.DictReader(
    (root / "specs/evidence/sec-filing-index-ingestion/stage-1/runtime/dependency-matrix.csv").open())}
packages = {package["name"]: package for package in lock["package"] if "registry" in package["source"]}
assert set(packages) == set(accepted) - {"pyarrow"}
rows = []
for name, package in sorted(packages.items()):
    distribution = metadata.distribution(name)
    assert distribution.version == package["version"] == accepted[name]["version"]
    tags = [line.removeprefix("Tag: ") for line in distribution.read_text("WHEEL").splitlines() if line.startswith("Tag: ")]
    candidates = []
    for wheel in package["wheels"]:
        filename = wheel["url"].rsplit("/", 1)[-1]
        python_tag, abi_tag, platform_tag = filename[:-4].rsplit("-", 3)[1:]
        expanded = {f"{py}-{abi}-{system}" for py in python_tag.split(".") for abi in abi_tag.split(".") for system in platform_tag.split(".")}
        if set(tags) <= expanded:
            candidates.append(wheel)
    assert len(candidates) == 1, (name, tags, candidates)
    selected = candidates[0]
    destination = evidence / "wheels" / selected["url"].rsplit("/", 1)[-1]
    destination.parent.mkdir(exist_ok=True)
    with urllib.request.urlopen(selected["url"], timeout=30) as response:
        destination.write_bytes(response.read())
    actual_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
    assert selected["hash"] == "sha256:" + actual_hash
    compared_files = 0
    with zipfile.ZipFile(destination) as archive:
        for member in archive.namelist():
            if member.endswith("/") or member.endswith(".dist-info/RECORD"):
                continue
            assert distribution.locate_file(member).read_bytes() == archive.read(member), (name, member)
            compared_files += 1
    rows.append({"distribution": name, "version": distribution.version,
                 "installed_wheel_tags": tags, "local_artifact": str(destination.relative_to(root)),
                 "local_archive_sha256": actual_hash, "locked_archive_sha256": selected["hash"],
                 "accepted_linux_artifact": accepted[name]["artifact_filename"],
                 "accepted_linux_sha256": accepted[name]["sha256"],
                 "hash_matches_linux": actual_hash == accepted[name]["sha256"],
                 "installed_files_match_downloaded_archive": compared_files})
result = {"python": sys.version, "platform": platform.platform(), "machine": platform.machine(),
          "accepted_distributions": len(accepted), "acquisition_distributions": len(rows),
          "excluded": ["pyarrow"], "version_differences": [],
          "hash_differences": [row["distribution"] for row in rows if not row["hash_matches_linux"]],
          "distributions": rows,
          "installed_distributions": sorted((dist.metadata["Name"], dist.version) for dist in metadata.distributions())}
(evidence / "resolution-inspection.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({key: value for key, value in result.items() if key not in ("distributions", "installed_distributions")}, indent=2))
