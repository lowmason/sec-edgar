"""Derive honest retention metadata for public web-tool excerpts already on disk."""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def source_sections(path):
    body = path.read_text()
    sections = body.split("--------------------------------------------------------------------------------")
    records = []
    for ordinal, section in enumerate(sections, start=1):
        urls = re.findall(r'https://[^\s\"<>)}]+', section)
        official_urls = [url.rstrip(".,") for url in urls
                         if url.startswith(("https://learn.microsoft.com/", "https://raw.githubusercontent.com/Azure/",
                                            "https://github.com/Azure/"))]
        source_url = official_urls[0] if official_urls else None
        if source_url is None:
            continue
        failed = "Internal Error" in section or "Failed to fetch" in section
        unselected = "/answers/" in source_url or "/tr-tr/" in source_url or "/hu-hu/" in source_url
        records.append({
            "id": f"{path.stem}-{ordinal}", "source_url": source_url,
            "artifact": str(path.relative_to(ROOT)),
            "retained_at_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
            "access_time_semantics": "File retention immediately after web retrieval batch; not exact HTTP access timestamp.",
            "source_version": "Selected API/version/tag if explicit in URL; otherwise current rolling official page",
            "outcome": "failed retrieval" if failed else ("unselected search result" if unselected else "bounded rendered excerpt"),
            "method": "Public web.run open/find/search; no authenticated Azure or SEC calls",
            "section_ordinal": ordinal,
            "section_sha256": hashlib.sha256(section.encode()).hexdigest(),
            "artifact_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "limitation": "Tool-selected lines; no original HTTP bytes/headers or complete-page guarantee. Failure is not proof of API absence.",
        })
    return records


def main():
    records = [record for path in sorted(ROOT.glob("*.txt")) for record in source_sections(path)]
    (ROOT / "retrieval-metadata.json").write_text(json.dumps({
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "records": records, "records_count": len(records),
        "category": "Verified documentation / failed check; bounded by each retained section",
    }, indent=2) + "\n")
    manifest = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(ROOT.iterdir()) if path.is_file() and path.name != "sha256-manifest.json"}
    (ROOT / "sha256-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"records": len(records), "failed": sum(record["outcome"] == "failed retrieval"
                                                             for record in records),
                      "manifest_files": len(manifest)}))


if __name__ == "__main__":
    main()
