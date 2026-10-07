## Global Constraints

The following are copied verbatim from Stage 3 spec §3; every task inherits them:

- The implementation will live in **`packages/sec-edgar-ingest/`**, with `sec-edgar-ingest` as the distribution and CLI name and `sec_edgar_ingest` as the Python import package.
- ETL reads those bytes from ADLS and makes no SEC requests.
- ETL never silently follows a mutable “latest”.
- Original bytes are retained.
- Downloaded, transformed and published are different states.
- Refuse malformed rows rather than silently dropping them; quarantine the source and report the line and reason.
- An unrecognized legacy format does not by itself invalidate a usable index row.
- Never deduplicate on company name and filing date alone.
- An identical input fingerprint and unchanged versions are a no-op.
- A forced replay may rebuild output, but cannot create a second logical filing.
- A gated candidate is `awaiting_approval`, not current.
- A conflict requires rereading the active generation and rebuilding; never overwrite a newer pointer with stale work.
- The pointer update is the publication boundary.
- There is no assumed transaction spanning Blob Storage and Table Storage.
- Per-source published flags are recoverable indexes, not a second commit authority.
- Atomicity is **per quarter**, not across the entire historical dataset.
- CI runs on committed fixtures and mocked SEC responses; it downloads nothing from the SEC.

Exact values: Python >=3.14; PyArrow 25.0.1; Requests 2.34.2; Identity 1.26.0; Blob 12.31.0/API 2026-04-06; Tables 12.7.0/API 2020-12-06; canonical schema `sec-index-v1`; received-byte guard 67,108,864; expanded-byte guard 536,870,912; exchange deadline 90 seconds; batches 8,192 rows; CAS_ATTEMPTS 5. Retain accepted settings and pins, one ingest package and indefinite development evidence retention. Stage 7 measures actual Linux amd64/Python 3.14.8 worker memory, runtime and scratch; native proofs establish no deployed capacity.

Live SEC, Azure, authentication, compute, provisioning and deployment authorizations remain closed. Use cached libraries and retained evidence only. No auto-fetch fallback, optional codec selection, approval bypass, image build, workflow/schedule activation or later-stage routing belongs to this plan.


---

# Owner-authorized Stage 3 acceptance amendment

BASE: 3898502d7920d285f72f8f41057b706d8a85a64e. Worktree: /Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar. You are not alone in the codebase. Do not revert others' changes; accommodate them. Primary /Users/lowell/Projects/sec-edgar remains read-only. Controller owns plan markup, retirement, roadmap copy/update, backlog completion, completion-checkpoint and final inventories.

Owner's exact new instruction (2026-10-07 America/New_York; no owner-supplied time of day): “explicitly amend Stage 3 acceptance to allow these documented quarantines while retaining strict refusal”. This is approval of a narrow documentary acceptance exception, not approval of any source, winning duplicate, parser tolerance, bytes normalization, policy change, live access, or later stage.

Ownership: amend only specs/sec-filing-index-ingestion-stage-3-spec.md §8/current acceptance wording; current specs/evidence/sec-filing-index-ingestion/stage-3/verification.md status; create NEW specs/evidence/sec-filing-index-ingestion/stage-3/acceptance-amendment/ evidence/verifier. Do not mark spec COMPLETE (controller will do that after review). Do not modify production or test code, package README/wheel metadata, dependencies, original owner-approval.json, planning-reconciliation.json, frozen verification/, final-review-fix1/, review-checkpoint/, delivery-sha256.json, plan or roadmap. Avoid runbook changes unless an actual incorrect acceptance status requires it; ask controller about scope.

Acceptance is permitted ONLY for the exact retained bytes of SEC-0141 (2010Q1, 300561 rows,21 conflicts, first6580), SEC-0142 (2015Q1,318647 rows,24 conflicts, first87808), SEC-0143 (2026Q3,302315 rows,6 conflicts, first40292). Bind complete raw SHA256/length from actual retained reports. Full scan970622 rows,51 conflicts (45 form_type-only,6 company_name-only), original specimen exit1 remains exact historical failure. Strict canonical (cik,archive_path) conflicting duplicate invalidates WHOLE SOURCE. Actual transform proof must still show quarantined outcome and no accepted Processing/ObservationRef/pointer mutation. Other invalid retained rows and offline cached dependency absence remain blockers. These sources establish observed syntax/family/refusal coverage; they do not establish successful catalog/range or deployed capacity. All22Stage7checks reserved.

Required evidence sources (read targeted parsed facts, no huge dumps):
- verification/specimens/report.json and its per-receipt records/sha256.json (actual complete scan)
- verification/sdd-history/retained-parser-preflight/report.json and conflict-classification.json
- verification/sdd-history/retained-parser-preflight/transform-refusal/report.json (+ actual source/storage proof artifacts)
- final-review-fix1/audit.json, report.md, full-check/command.json, installed/report.json as current unchanged implementation proof
- original retained Stage1 source paths are resolved by the above reports against primary's read-only retained bytes.

Before modifying current verification.md, retain its exact old bytes at acceptance-amendment/originals/verification.md. Keep existing delivery-sha256.json bytes intact; record an explicit historical resolution map for verification.md -> acceptance-amendment/originals/verification.md (every other original path still resolves directly), so the old delivery snapshot stays independently verifiable. Controller will create a new full completion inventory.

Create a narrow machine-readable owner amendment receipt, human explanation, and a guarded fresh offline acceptance verifier/report with actual argv/runtime/exit/stdout/stderr/hash observations. Verification should bind exact allowlisted sources/row counts/conflicts/first lines/refusal states and old immutable inventory hashes; verify original source bytes and frozen artifact manifests and no production/parser/transform changes since reviewed2343f39f0e21adc2ad401a9346a8c9ffa0509040. It may reuse full-scan/refusal immutable evidence; do not spend125seconds rescanning unchanged parsers. Clearly distinguish this new acceptance exit0 from original specimen exit1. Install packages/sec-edgar-ingest/tests/network_guard.py before package imports for every Python child. Use cached selected Python3.14/uv --offline --frozen only. No downloads/auth/sockets. Evidence contains actual results rather than invented future success. Exclude self from each new inventory, no circular hashes.

Validate the new exception is exact and refusal remains strict; narrow fresh verifier is needed, no full452test rerun for unchanged implementation. Preserve all prior failed receipts/logs. Inspect complete outputs and self-review, then commit only owned explicit paths. All worktree mutations/Git need exec_command sandbox_permissions=require_escalated, with clear local offline justification. Never git add -A, stash/reset/restore/clean. Return DONE with HEAD, changed paths, actual acceptance result/hash, strict refusal facts and any concern.
