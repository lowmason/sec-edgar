# Task 7 report — real process, retained specimens and installed ETL proof

Status: **DONE_WITH_CONCERNS**. Native capability proof passes. Stage 3 source
acceptance remains blocked by the approved-policy conflict in retained receipts;
no COMPLETE receipt, roadmap tick, retirement, integration or cleanup was made.
`all22_stage7_checks: reserved`.

Base: `63c327390f76d466e04fb8285f7c95f39e4f4937`. Worktree:
`/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar`, branch
`codex/sec-edgar-stage-3`. The parent controller provides Task 7 and whole-branch
reviews. No subagents/reviewers were spawned. No production module or dependency
pin changed. All network, live SEC/Azure/authentication, compute, provisioning,
deployment and image-build authorizations remained closed.

## Owned delivery and actual interfaces

Created `packages/sec-edgar-ingest/tests/etl_proof.py` with the exact
`main(argv: Sequence[str] | None = None) -> int` interface, required `--output`, and
`specimens`, `sequence`, `installed` modes. Output directories are exclusive;
failures remain distinct. Each result records actual argv, cwd, native executable,
Python/platform/dependency versions, duration and exit. SHA inventories use safe
relative names, sizes and actual bytes, excluding themselves.

Created `test_etl_processes.py`: actual multiprocessing spawn proof, separate
process stores, one-use first-publication barrier, finite join deadlines, owned
hung-child termination, retained child stdout/stderr and all four command help
contracts. The full-suite runner includes it through existing guarded discovery;
`scripts/check-sec-edgar-ingest.sh` received a clarifying comment only. Added the
reader/replay/gate runbook and verification report; updated both READMEs to explain
transform/publish/capture/recovery contracts and the separate acceptance blocker.

The proof consumes real `seed_snapshot` Source/Binding/workset codecs,
`seed_observation`/`transform_member`, `cli.main`, `publish_quarter`,
`capture_quarter`, `read_quarter`, `read_manifest`, `EtlState`, `store_bundle`,
`Settings`, `pin_context`, `RunContext`, `ObservationRef`, and actual local CAS.
The specimen scan calls `iter_observations`, `_seen_database` and
`_remember_observation` so its duplicate decision is the production decision.
No independent transform, publication, generation, reader or recovery algorithm
was added. The full receipt scan deliberately continues gathering evidence after
a conflict but marks the whole source blocked; it never emits accepted transformed
output for that source.

Per execution-notes ownership, copied exact primary `owner-approval.json`,
`planning-reconciliation.json` and approved `versions/*` bytes. Archived prior SDD
briefs, interfaces, reports, reviews, progress/ledger, baseline/red/green, full
artifacts, hashes, preservation/preflight and retained-source blocker findings to
`specs/evidence/sec-filing-index-ingestion/stage-3/verification/sdd-history/`.
Historical failure/pending statements remain unchanged. Final controller review
receipts remain to be added by the controller.

## TDD and failures preserved

1. Guarded `test_etl_processes.py` first ran before the driver existed. Exit 1:
   explicit missing-driver assertion failure plus the corresponding missing-import
   error, two tests in 0.001s. Full stdout/stderr in `sdd-history/task7-evidence/red/`.
2. Implemented real-process proof with no production patch. Focused same command
   passed two tests in 4.273s (`process-1/`). That early test used temporary child
   directories; later sequence and full-check runs retain all actual child traces.
   The early wrapper elapsed time was not measured. Supplementary metadata says
   null rather than inventing it; unittest timing comes from the actual logs.
3. `sequence-1/` passed actual CLI raw transform, publication, repeated saved result,
   no-op, forced parser-v2 replay, cross-quarter source, open omission and closed
   withdrawal gate, plus all real process proofs. Its full intermediate report and
   objects remain archived.
4. `installed-1/` failed actual offline resolution because charset-normalizer's
   registry wheel was unavailable. `installed-2/` failed because Stage 2 retained
   wheels alone do not contain PyArrow. `installed-3/` documented that combining
   find-links and registry cache still selected unavailable registry charset-normalizer.
   The final installer splits only the exact exported PyArrow lock entry for cached
   offline installation; all remaining exact hash-bearing entries install from
   retained Stage 2 wheels with `--offline --no-index --require-hashes`. No pin,
   dependency wheel or interpreter was replaced, reconstructed or fetched.
5. `installed-4/` successfully installed dependencies but reproduced a proof-only
   spawn-main error: generated runner top-level code tried to recreate the parent
   output in each child. Preserved full traceback and partial durable evidence;
   guarded runner execution under `if __name__ == '__main__'`. `installed-5/`
   then passed the entire isolated sequence/process proof. No library fix needed.
6. An archival-verifier first run mistakenly treated explicit `absent:true` entries
   as required files. Actual required absences and file hashes remained correct.
   Retained the failed verifier and failure record, then respected absent sentinels
   and verified all 19,088 inventory records. This was evidence-tool logic only.

All intermediate proof directories and generated command/results remain retained;
no failure was overwritten by a success-looking summary. Clean-code naming and
cohesion guided functions such as `capture_evidence`, `prove_race`, `prove_death`,
`join_children`, `run_logged` and `inventory` (N1/F2/G30/G25). Verification was run
before claiming passing proof or committing.

## Final commands and checks

Exact command arrays, cwd, full stdout/stderr, exits and environment appear in
adjacent verification subdirectories. All Python commands used
`uv run --offline --frozen --package sec-edgar-ingest python` unless their actual
isolated venv command records specify its executable.

- `scripts/check-sec-edgar-ingest.sh`: **exit 0**, **439 tests in 160.832s**,
  wall duration 161.84262608317658s. Wheel and sdist build exit 0; main help lists all
  four commands, tests exercise each help; module version 0.1.0; compileall and
  `git -c core.whitespace=cr-at-eol diff --check` pass. Run once after final Python,
  tests and check-script implementation changes. Full logs and child directories:
  `verification/final-check/`.
- `packages/sec-edgar-ingest/tests/etl_proof.py specimens --output specs/evidence/sec-filing-index-ingestion/stage-3/verification/specimens`:
  **exit 1**, actual scan duration 125.7240011668764s. Correct retained acceptance
  gate; all ten complete originals parsed and inspected, details below.
- `packages/sec-edgar-ingest/tests/etl_proof.py sequence --output specs/evidence/sec-filing-index-ingestion/stage-3/verification/sequence`:
  **exit 0**; full wrapper record `sequence-command/`, full inner report and 279
  durable objects/files in `sequence/` (final inventory is authoritative).
- `packages/sec-edgar-ingest/tests/etl_proof.py installed --output specs/evidence/sec-filing-index-ingestion/stage-3/verification/installed`:
  **exit 0**. Exact final wheel installed and all raw/process proofs rerun outside
  the checkout. Full wrapper `installed-command/`, each installer subprocess's
  complete inline stdout/stderr and actual exits, child-native metadata in
  `installed/installed-sequence/report.json`.
- Documented saved-capture/read and post-CAS repair example: **exit 0** in
  `runbook-command/`; pointer unchanged and saved capture rows retained in
  `runbook-proof.json`. Rechecked sequence hashes afterward: no changed payload.
- Final artifact inspection: **exit 0**, verified **7,884 inventory records**, read
  **169 command/result records**, exact final wheel/README and **28 Python source
  files** equal the reviewed tree; details in `artifact-inspection.json` and
  `artifact-inspection-command/`.
- Final documentation whitespace check: **exit 0**, `final-whitespace/`.

After the complete check, a README-only correction removed an obsolete
acquisition-only installation example that excluded PyArrow. Since README is
wheel metadata, `readme-wheel-build/` records a fresh successful offline build,
and final installed mode was rerun against it. Prior successful artifacts remain
under `installed-before-readme-correction/` and its command directory. No Python,
test or check-script change occurred after the full check.

## Actual process and recovery findings

All process targets install `network_guard` before package imports. Spawn uses
independent actual local stores. The observer blocks only the first
`publication.before_pointer`; rebuilds never reuse that barrier. Actual
`EtlState.commit_pointer` is wrapped only to record its real input/version and
exception/result, not to fabricate conflict or implement alternate commit logic.

Final sequence insert-race PIDs **20087/20088** both built on absence. PID 20087
actually received **AlreadyExists**, reread pointer version
`0d003a067b36480480b243265dd7d7f0`, rebuilt and published the union. Replace-race
PIDs **20094/20095** both built on version `f67a448a83f54b0894500a49070e7957`;
PID 20095 received **Conflict**, rebuilt from winner version
`b478d2e9e8f1437ebedd904f7228ce78`, and preserved both daily additions plus the
initial key. Proof asserts final logical keys, both source IDs, distinct process
PIDs, exactly one real conflict and matching initial base, not merely child exits.
Full manifest refs/hashes, candidate input, exact pointer records and per-child
observed transitions are retained in `sequence/processes/{insert,replace}/`.

Gate-race PIDs **20100/20101** both initially saw absence. Winner 20100 added the
key omitted by 20101's quarterly membership. The loser actually received
AlreadyExists and rebuilt to **awaiting_approval**, with conflict count 1. The
winner's two-key generation stayed current. Full gated candidate state is retained;
unreferenced first-build candidate files and checksums are not deleted.

Actual forced child exits **73** occurred at:

| Boundary | PID | Reopened readable capture |
| --- | ---: | --- |
| candidate.after_data | 20110 | complete old generation |
| publication.before_pointer | 20116 | complete old generation |
| publication.after_pointer | 20120 | complete new generation |
| etl_result.after_object | 20123 | complete new generation |

Each death writes an actual PID/boundary marker and flushes retained stdout/stderr
before `os._exit(73)`. Parent reopens fresh stores, validates capture and all reader
rows, resumes the **same frozen CLI arguments and command envelope**, then repeats
the completed command. Post-CAS pointer records remain exactly unchanged through
repair/replay; pre-CAS cases perform the one intended publication. Result-object
recovery uses existing CLI readback and Attempt repair. Full contexts, intent
hashes, state indexes, reader manifests/files and checksums are retained under each
boundary directory. Full-suite and isolated-installed runs produce independent
PID/trace sets in their own retained directories.

## Raw-only and installed identity

The sequence seeds actual Source/Binding/snapshot codecs and immutable original
IDX, invokes CLI transform and publish, repeats exact completed argv, then invokes
a new no-op attempt and proves no pointer change. Parser-v2 forced raw replay
uses a separate transform configuration with the same acquisition origin and
snapshot workset. Raw hashes/pins remain identical and business-field/logical-key
rows match before/after replay. A daily source spans Q3/Q4 and both captures are
validated. Open quarterly omission is unresolved absence with preserved keys;
closed omission gates without pointer change. Collector, sender and request-client
constructors are patched to fail if invoked; TransportAttempt remains empty.
All data is synthetic fixture data except the separately scanned complete receipts.
Original ZIP receipt hashes and worker-image provenance are not confused with
logical row/output identity.

Final wheel: `sec_edgar_ingest-0.1.0-py3-none-any.whl`, **110,438 bytes**, SHA256
`7d370cbe94d82254ae2095e8bcb8993ebef939651fc788181fc6b90906d1cfdc`.
It exactly matches retained wheel bytes and dist output. Every one of the 28
package Python source files matches both wheel and installed site-packages bytes;
version is 0.1.0 and PyArrow 25.0.1/Requests 2.34.2/Identity 1.26.0/Blob12.31.0/
Tables12.7.0 remain exact. The isolated child itself records its venv executable,
site-packages root and native metadata. PYTHONPATH is removed and cwd is outside
the repository; only copied test harness/helpers are outside the installed package.
The venv uses already selected native Python with `UV_PYTHON_DOWNLOADS=never`.

## All ten receipts and acceptance blocker

| Receipt | Rows | Identical duplicate keys | Conflicting observations |
| --- | ---: | ---: | ---: |
| SEC-0141 | 300561 | 0 | 21 |
| SEC-0142 | 318647 | 0 | 24 |
| SEC-0143 | 302315 | 0 | 6 |
| SEC-0144 | 12479 | 0 | 0 |
| SEC-0145 | 12479 | 0 | 0 |
| SEC-0146 | 3594 | 51 | 0 |
| SEC-0147 | 5527 | 92 | 0 |
| SEC-0148 | 7159 | 69 | 0 |
| SEC-0149 | 3084 | 68 | 0 |
| SEC-0150 | 4777 | 46 | 0 |

Total **970622** parsed original rows. Seven receipts pass acceptance; three fail.
Complete scan preserves original hashes/bytes, source/family/context, date bounds,
quarter counts, selected inspected original rows, first conflicting payload and
physical conflicting fields/reason. Earliest conflict lines are **6580/87808/40292**.
The independently archived controller preflight classifies 45 differences in form
and 6 in company name, with same normalized identity/date/accession; no policy
exception is introduced. Actual complete-source transform refusal is archived in
`retained-parser-preflight/transform-refusal/report.json`. Per approved §8,
invalid retained rows block completion until owner policy reconciliation. Native
parse coverage and correct refusal cannot be substituted for range acceptance.

## Preservation, self-review and limits

`primary-preservation.json` confirms all **19088** protected records, required four
old-package absences and roadmap **15853 bytes** SHA256
`25cc4f40a9ddb34679fc5f226f4cc32a7be6739f75ea463e4dfde499d72aceab` unchanged.
Exact primary approval and historical approved versions were copied, not rewritten.
Archive and final inventories retain safe relative paths and exclude themselves;
failed runs, reports, reviews and original cached evidence stay separately labeled.

Self-review checked actual source scope, same-base barriers, real CAS exceptions,
loser source union, gate re-evaluation, forced deaths, exact frozen-intent repair,
reader hashes, cached installation, source/version equality, every Task 7 hash
manifest and known failed-command exit. No current pointer is inferred from a
candidate and no successful source acceptance is inferred from a full parse.
The final package/test implementations were covered by the one full check;
subsequent README metadata change received build/install and whitespace coverage.

Remaining concerns: unresolved retained-source acceptance policy; parent Task 7
and whole-branch review receipts still pending; native macOS arm64/Python3.14.0
provides no Linux amd64/Python3.14.8 worker memory/runtime/scratch evidence or actual
ADLS/HNS/identity/Azure concurrency proof. All 22 integrated checks remain reserved
for later roadmap Stage 7. No later-stage operation or cleanup was performed.


# Task 7 final staging addendum

Delivery commit: `d3d5859056916707dec0119b72bb3794cf762fb1`.

The full check passed **before historical evidence was staged**. Its whitespace
result and the later documentation-only whitespace check apply to those unstaged
changes; they are not an assertion that the entire final evidence diff is clean.
The final staged check detected exact historical evidence whitespace, and the
commit shell continued after that nonzero command. A retained postcommit check of
that same diff, `git -c core.whitespace=cr-at-eol diff HEAD^ HEAD --check`, exited
**2**. Full stdout/stderr and actual command metadata are retained in
`committed-history-whitespace/`. No archived bytes were normalized or removed.

A separate check over the committed Task 7 Python tests/driver, check script,
READMEs, runbook and verification prose exited **0**, with complete evidence in
`committed-owned-whitespace/`. Production source and tests are unchanged since the
439-test full check. This limitation concerns the complete historical evidence
diff, and remains explicitly visible to the controller/reviewers.

Affected historical paths, grouped by suffix: {".diff": 9, ".md": 1, ".txt": 4}.
The complete exact path list is in
`committed-history-whitespace/affected-paths.json`. Every affected path is under
`sdd-history/`: one Markdown interface document, nine review/owned unified
diff snapshots, and four text logs (one tracked-diff stdout and three red/green
stderr logs). These are copied archival contents, including blank context lines
in unified diffs; changing
them would violate the exact-byte history requirement. The filename categories
and exact paths in the JSON receipt are authoritative.

Stage 3 remains DONE_WITH_CONCERNS at task delivery, with the 51 retained-source
conflicts still blocking acceptance, historical whitespace explicitly retained,
and all 22 integrated checks reserved. No plan/roadmap completion or cleanup.
