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

### Task 7: Real process, retained-specimen and installed-wheel proof; delivery documentation

**Files:** Create `packages/sec-edgar-ingest/tests/test_etl_processes.py`, `packages/sec-edgar-ingest/tests/etl_proof.py`, `docs/runbooks/sec-edgar-etl-publication.md`, `specs/evidence/sec-filing-index-ingestion/stage-3/verification.md` and proof artifacts under its adjacent `verification/`. Modify `scripts/check-sec-edgar-ingest.sh`, `packages/sec-edgar-ingest/README.md`, `README.md` for new command/read contracts only. Retain planning-reconciliation.json; do not rewrite earlier evidence to remove failures or pending historical statements.

**Interfaces:** Consumes installed commands and public transform/publish/read APIs. Produces test proof driver `main(argv: Sequence[str] | None = None) -> int` with required `--output` and modes `specimens`, `sequence`, `installed`; reports actual paths/versions/platform/argv/exits/hashes. No alternate ETL/commit algorithm. Test process targets import actual modules and independent real local stores.

- [ ] **Step 1: Add real adversarial process tests, capture the first uncovered failure.** Use multiprocessing spawn/barriers and existing network guard; two real publishers independently read the same absent/current pointer before either CAS, add distinct daily sources, then race. A shared observer barrier at publication.before_pointer aligns the first builds, releases exactly once, and does not block the losing publisher's rebuild. Record PIDs, exact base versions/candidate hashes, actual local insert/replace conflict, loser rebuild source set and final capture. Assert final keys equal the union and both updates remain, not merely that both processes exit. Each child has a finite join deadline and retained stdout/stderr; terminate only its own hung test process and report failure.

Additional real forced-exit children die at candidate.after_data, publication.before_pointer, publication.after_pointer and etl_result.after_object. Parent reopens independent stores, asserts old/new complete readable capture, resumes same frozen intent and verifies repair with no extra commit. Gate-race fixture has winner add a key that the loser's closed quarterly replacement omits; loser must rebuild and become awaiting_approval. Retain unreferenced losing candidate files and actual reader hashes. Never infer a real process race from a scripted conflict alone. Run test_etl_processes.py guarded and retain red for missing proof/boundary behavior before fixes.

- [ ] **Step 2: Implement retained-receipt and raw-only sequence proofs.** `specimens` reads the retained Stage 1 matrix, each inspection JSON's original_path relative to its stage root, verifies original hash/byte count and selected family, then invokes the actual parser on all ten complete receipts. Compare source-row counts, filing-date min/max, selected inspected rows, duplicate-key outcomes and quarter counts. A failing specimen blocks range claims; preserve its row/reason and do not patch retained bytes or weaken the parser to pass. Compact synthetic legacy goldens remain clearly separate from observed legacy evidence.

`sequence` seeds canonical stored inputs using actual fixture Source/Binding/workset codecs; it then executes actual transform, publish, read, repeat/no-op, fixture parser-v2 raw replay, cross-quarter daily addition, open absence and closed withdrawal gate against durable stores. Verify no collector constructors/transport requests and unchanged raw/pins; inspect complete manifests and per-quarter state. Exact acquisition-provenance config remains origin; separate transform configs use row-parser aliases. Record logical identity/output determinism separately from original ZIP receipt bytes and worker-image provenance. No download, SEC collection sequence or Azure auth is required.

Proof SHA inventory is computed from actual final files with relative safe paths, byte lengths and SHA256; exclude itself to avoid circularity. Retain failed/intermediate runs under distinct output directories, not overwriting success-looking summaries. Every command's output includes actual exit/platform/runtime/dependency versions and explicit `all22_stage7_checks: reserved`.

- [ ] **Step 3: Build and prove the installed wheel entirely offline.** Run the prescribed check once after final implementation change, with full output retained:

```bash
scripts/check-sec-edgar-ingest.sh
```

Expected: acquisition and ETL tests/process fixtures OK, wheel/sdist build exit0, four-command help, module version, compileall and whitespace exit0. The script already invokes the guarded runner; expand CLI help assertions in tests instead of adding a network-capable test path. Preserve accepted CRLF fixture handling with `git -c core.whitespace=cr-at-eol diff --check`.

The installed mode builds/uses the produced wheel, creates a temporary isolated uv venv using the already selected native Python, installs that exact wheel and cached lock pins with `uv pip install --offline`, runs commands with cwd outside the repository and PYTHONPATH removed, and imports sec_edgar_ingest from site-packages. Fail if source checkout import leaks in. Reuse the Stage 2 proof's cached-wheel install/readback pattern; do not copy its old approval-pending status as current. Compare installed wheel source bytes/version and retained wheel hash to the reviewed tree.

Concrete driver commands once it exists:

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/etl_proof.py specimens --output specs/evidence/sec-filing-index-ingestion/stage-3/verification/specimens
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/etl_proof.py sequence --output specs/evidence/sec-filing-index-ingestion/stage-3/verification/sequence
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/etl_proof.py installed --output specs/evidence/sec-filing-index-ingestion/stage-3/verification/installed
```

Expected all exit0; actual row counts and native runtime come from inspected output, not invented future numbers. Full Linux worker/ADLS/HNS/identity/ETag behavior and memory/runtime/scratch stay Stage 7. Extend the guard into every proof child; cache/build tooling is offline and Python sockets/auth remain denied.

- [ ] **Step 4: Write and exercise the reader/replay/gate runbook.** Include exact storage reference shapes and commands, pinned origin vs transform context, null accession/date-to-quarter behavior, no-op/force semantics, pointer-capture Python example, files/checksums validation, per-quarter atomicity, safe post-CAS repair, partial progress and awaiting_approval exit10. Show replay selecting an exact retained snapshot workset and configuring a supported current parser without recollection. Show capture/read:

```python
from sec_edgar_ingest.etl.reader import capture_quarter, read_quarter
from sec_edgar_ingest.etl.state import EtlState
capture = capture_quarter('2026Q4', objects, EtlState(store))
if capture is None:
    raise RuntimeError('quarter has no published generation')
for row in read_quarter(capture, objects):
    print(row.cik, row.archive_path)
```

`objects` and `store` are the selected open_stores outputs established in the runbook's configuration example; saved capture refs are sufficient for subsequent reproducible reads. Explain gate inspection using candidate ref and exact source hash; Stage 3 supplies no approval mutation, pointer rollback command or success claim for a gated run. Reserve those operations for later stages. Update README from acquisition-only scope to completed transform/publish capabilities only after proof passes. Verification report links full commands/logs/fixtures/file manifests/process outcomes/reviews, explicitly preserving historical failures and reserved integrated checks.

- [ ] **Step 5: Inspect proof artifacts and commit owned files.** Parse every retained command exit/full log, inspect real CAS and process kill/repair traces, verify every proof SHA record and installed source equality. Recheck primary preservation receipt and planned source scope. Fix implementation failures with a new covering test; rerun covering checks only when changes justify it. Then explicitly add this task's files/artifacts and commit:

```bash
git add packages/sec-edgar-ingest/tests/test_etl_processes.py packages/sec-edgar-ingest/tests/etl_proof.py scripts/check-sec-edgar-ingest.sh docs/runbooks/sec-edgar-etl-publication.md packages/sec-edgar-ingest/README.md README.md specs/evidence/sec-filing-index-ingestion/stage-3/verification.md specs/evidence/sec-filing-index-ingestion/stage-3/verification
git commit -m 'test: prove replay publication races and installed ETL recovery offline'
```
