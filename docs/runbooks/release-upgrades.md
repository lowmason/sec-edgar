# Immutable release upgrades and reconstruction

Prepare dependencies and artifacts explicitly as in [native setup](native-setup.md). Build reviewed clean committed code into a new `releases/sha256=<release-id>` environment; never install into an existing accepted venv or sync it during ingestion. Keep original manifests, receipts, wheels/sdists, lock/export, exact runtime wheels and setup evidence. Release identity is not a container image digest and has no compatibility alias.

Before selecting B, stop/confirm old writers and child drain, retain A and its invocation/config/result evidence, and take a consistent backup if required. Review the exact new release, accepted harness, effective config and run budget at the later activation gates. Selecting B in a new config changes its `runtime.release_manifest`; storage root/mode/issuer/policies/storage contract stay bound. Old range/IDs/parser/release are not part of the root binding. New code can read validated historical producer records; old execution still requires A. Verify B with the copied offline harness and a new evidence directory before using it.

A later new-ID invocation under B may continue compatible A-origin pending work and repair A-origin publication evidence through the original checked child authority. A completed exact A attempt replays with A and its unchanged argv/config/IDs/deadline. Do not rewrite retained producer release metadata to B. Captured reads remain bound to exact original manifests even when current pointers change. Unsupported parser/schema transitions must refuse; no old-state import, relocation, force bypass or automatic cleanup is provided.

Selecting the 2a release `e49d3ba87f7d4eb3082c5bfbfce44bb02ade6a4acd8dfc1a595d3dc424c67eec` changes three config values together: `runtime.release_manifest`, `etl.parser_version` and `etl.schema_version`. The parser and schema move from `sec-index-parser-v1` / `sec-index-v1` to `sec-index-parser-v2` / `sec-index-v2`. Retained v1 objects stay as written, and the 2a release reads v1 generations as v1 rows. It continues 1c-origin pending work on a store that the 1c release wrote, as tested on fixture stores. The transition is one-way. The 1c release refuses a v2 config, and after a v2 run writes to a store, selecting the 1c release for that store is unsupported. (Stage 2a, plan 7, 2026-11-02; [parent spec](../../specs/completed/sec-filing-index-ingestion-spec.md) §§4.8–4.9.)

Selecting the 2a1 release `f414caf89eaac416f8b6a27330773eb0d398cc5caedb881a37cf228379f7fa18` changes `runtime.release_manifest`. Stage 2a1 also raised `execution.dispatch_reserve_seconds` from 1800 to 1824, because the longest measured member wall is above the 1,056 s limit of the Stage 1b rule. The parser and schema stay `sec-index-parser-v2` / `sec-index-v2`, and the release changes no format. It continues 2a-origin pending work, and the 2a release continues work that the 2a1 release left pending. So selecting the 2a release again is supported, as tested on fixture stores. But on the live store the 2a release needs about 3,200 s to select work, which is above the cutoff, so it can dispatch no member there. (Stage 2a1, plan 9, 2026-11-15; [parent spec](../../specs/completed/sec-filing-index-ingestion-spec.md) §§4.8–4.9.)

If an original environment is missing but all retained artifacts remain valid, reconstruct it at its final new release address using the exact matching supported interpreter. This is explicit setup, offline and outside ingestion. Do not copy or move a venv:

```sh
project=$(pwd -P)
manifest=/absolute/retained/releases/sha256=RELEASE_ID/release.json
new_releases=/absolute/recovery/releases
uv run --offline --locked --package sec-edgar-ingest python - "$manifest" "$new_releases" <<'PY'
from pathlib import Path
import sys
from sec_edgar_ingest.release import reconstruct_release
print(reconstruct_release(Path(sys.argv[1]), Path(sys.argv[2]), python=Path(sys.executable)))
PY
```

The source manifest's sibling artifacts must be intact. Reconstruction validates hashes and complete inventories independently of the missing old executable/receipt, requires matching interpreter identity, creates the final content-addressed destination exclusively, then installs from retained artifacts and issues a new installation receipt. Missing artifacts/interpreter mismatch are explicit failures. Preserve the unavailable original location/evidence; a new location does not rewrite saved attempt config or authorize silently redirecting an exact replay. Resolve original-runtime availability through reviewed recovery rather than substituting B or editing retained invocation records.

Rolling back a release selection means choosing a retained verified release for a new invocation/config, subject to compatibility and operating gates. Rolling back quarter data is the separate audited `rollback` operator command in [local ingestion](local-ingestion.md), with exact from/to generations, reason and operator label. Never edit a publication pointer manually.

L01–L11/L13 have [renewed passing offline evidence](../../specs/evidence/local-port/offline-renewal-task15.md), including two-release pending/repair/read authority and a disposable real urllib3 version tamper while direct pins remain intact. The separate [genuine SEC acceptance record](../../specs/evidence/local-port/sec-acceptance.md) records an L12 pass established by a reviewed supplemental offline adjudication of the preserved genuine attempt; the original run and verification remain incomplete with exit 12. This bounded result establishes no historical coverage. The preserved generated default config still references the old `900952a8…` release and was not selected for this case; further live operation requires explicit reviewed release/config selection, budgets and operating gates.
