# SEC filing-index ingestion — Stage 3: Replayable ETL and safe publication

**Status:** PROPOSED (2026-10-07 America/New_York) — implementing spec and plan await owner approval; implementation has not started.
**Owner:** Lowell Mason.
**Implementing plan:** [Plan 3](plans/3-sec-filing-index-ingestion-stage-3-spec.md).
**Authority:** [Accepted parent design](sec-filing-index-ingestion-spec.md), [accepted ADR](sec-filing-index-ingestion-adr.md), [local roadmap](sec-filing-index-ingestion-roadmap.md), [accepted F1](sec-filing-index-ingestion-stage-1-findings.md#10-final-owner-acceptance--f1), and authoritative [Stage 1](completed/sec-filing-index-ingestion-stage-1-spec.md#9-rollout-note) / [Stage 2](completed/sec-filing-index-ingestion-stage-2-spec.md#5-completion-gates-and-rollout-reference) completion stamps. This document implements only the roadmap's Stage 3, R3/R6/R9; it does not replace the parent contract.

## 1. Offline resume/reconciliation

`derive-roadmap` reconciliation on 2026-10-07 found local `HEAD` and local `origin/main` equal to `5f90a2116eab21525e88a02d0988567e71d95967`, the merged PR #2 revision. No fetch, remote query, SEC request, Azure operation, authentication, compute or deployment was performed. Local remote-tracking equality establishes only the locally available merged baseline.

Stage 1's authoritative stamp is **COMPLETE (2026-10-06), plan 1**. Its owner-accepted READY finding F1 was accepted 2026-10-05 America/New_York, exact pre-appendix finding SHA-256 `939a724eccf22147015a59d5940ed57f02cc4e9fe9d942a9cd78ae73c34615ff`, evidence manifest SHA-256 `124e96041548daba8216aa495fc69021751555b0f0e4c890ac85e934f512a131`. Fresh offline inspection verified all 1,584 manifest records: 1,583 direct matches plus the manifest's declared immutable alias for the finding before its acceptance appendix. Capture-time pending statements cannot overrule final acceptance or the completed stamp.

Stage 2's authoritative stamp is **COMPLETE (2026-10-06), plan 2**. Its [completion receipt](evidence/sec-filing-index-ingestion/stage-2/verification/completion-checkpoint/completion-receipt.json) names reviewed revision `e458010ead6709c16e992fa22a33997d3aa36ef0`, 302 tests and completed build/CLI/whitespace checks. These are retained execution results, not a new test run during planning. Fresh reconciliation matched all 88 tested/reviewed file hashes against the current merged tree; both final proof manifests and their 78/96 payload records matched. The installed-wheel manifest is `126a1c3c666e1e41f63d37f68ec95ec145f55a28ec6a1ea97676fa9941caff47`; the combined fixture manifest is `beee194e1a67f1870c2b1d948c9ea29044f6ba0b6d9da0008443ccb13a8d4ab7`. See the [planning reconciliation receipt](evidence/sec-filing-index-ingestion/stage-3/planning-reconciliation.json).

The ignored local roadmap already ticks Stages 1 and 2. Preserve its current **15,853 bytes**, SHA-256 `25cc4f40a9ddb34679fc5f226f4cc32a7be6739f75ea463e4dfde499d72aceab`, including its historical derivation table and older Stage 1 consistency note. The current stamp/checklist outranks that note's historical “Stages 2–8 remain unticked.” Do not substitute the older Stage 2 planning-time roadmap hash. Preserve the four original absent files under `packages/sec-edgar-index-ingest/`: `README.md`, `pyproject.toml`, `src/sec_edgar_index_ingest/__init__.py`, `src/sec_edgar_index_ingest/py.typed`. Capture and preserve any edits made after this receipt; hash equality is a preflight check, not authorization to overwrite drift. Planning modifies none of these files, stages nothing and opens no worktree.

Every unticked stage was revalidated against the merged Stage 2 package and accepted parent:

| Stage | Current gap and disposition |
|---|---|
| 3 — Replayable ETL and safe publication | Immutable raw snapshots, source/snapshot worksets and state adapters now exist. Row parsing, normalized observations, catalog construction, change reports, generation commit/reader and raw-only replay proof remain missing. Route only this stage to `writing-plans`. |
| 4 — Backfill and daily catch-up workflows | Acquisition primitives exist; historical/daily composition with publication, complete/pending/failed run coverage and outage/overlap acceptance remain required. No workflow is planned here. |
| 5 — Reconciliation and withdrawal approval | Stage 3 must gate removals immediately. Scheduled reconciliation, approval creation/consumption, stale replay after approved withdrawal, reintroduction history and complete shared-workflow R5/R7/R10 exits remain Stage 5. |
| 6 — Azure orchestration and deployment definitions | Acquisition adapters are code, not deployed services. Complete-worker image, Bicep, ADF polling/correlation/results, schedules, disabled triggers and observability remain required. |
| 7 — Deployment checkpoint and recovery evidence | All [22 integrated checks](evidence/sec-filing-index-ingestion/stage-1/stage-7-checks.md) remain reserved, including actual HNS/identities/CAS/network, memory/runtime/scratch, SEC smoke, approval/rollback and runbooks. Local/mock proofs cannot close them. |
| 8 — Baseline and scheduled-operation acceptance | Fixtures establish no production coverage or observed schedules. Accepted baseline/catch-up/reconciliation, controlled enablement and durable scheduled evidence remain required. |

No deferred backlog exists. The accepted partition remains unchanged. This is resume reconciliation, not a new roadmap derivation or completion audit.

## 2. Stage outcome and boundary

Produce independently testable transformation and publication commands in the existing ingest package. Given an exact immutable snapshot workset, transformation validates every row and retains immutable versioned observations. Publication combines those exact inputs with the active quarter's explicitly retained source set, builds a complete candidate with change history, applies the withdrawal gate and conditionally changes one quarter pointer. Readers resolve that pointer and explicit manifest file list. Replay uses retained original bytes and cannot construct an SEC sender.

Include parser/schema/provenance contracts, processing checkpoints, transformed worksets, deterministic source selection, bounded disk-backed canonical construction, Azure/local adapter extensions needed by these outputs, safe candidate staging, pointer readers, post-commit repair, named CLI outcomes and offline evidence. Include the removal gate and hash-bound candidate record from the first publication. Provide no approval mutation or bypass flag in Stage 3; gated candidates remain inactive until the separately implemented Stage 5 operation.

Historical/daily workflow composition, reconciliation orchestration, approval operation, rollback mutation, resource provisioning, image build/deployment, schedule activation, live smoke and global multi-quarter atomicity remain their existing later-stage obligations. Stage 3 does not declare either range globally supported merely because retained specimens or synthetic legacy rows pass.

## 3. Constraints copied into Plan 3

The following project-wide contract sentences are copied verbatim; plan tasks inherit them:

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

Carry accepted exact acquisition pins and API versions unchanged: Requests **2.34.2**, Identity **1.26.0**, Blob **12.31.0** / **2026-04-06**, Tables **12.7.0** / **2020-12-06**. Add only the accepted ETL candidate **PyArrow 25.0.1**. Python remains **>=3.14**. The accepted Linux amd64/Python **3.14.8** compatibility probe is separate from this checkout's native runtime and any future worker image. Do not reselect versions or add Spark, Polars, pandas, DuckDB or a warehouse.

Preserve accepted guards: one exchange **90 seconds**, received bytes **67,108,864**, expanded IDX **536,870,912**. Source processing is sequential; use batches of **8,192 rows** and SQLite scratch for key resolution/sorting instead of collecting a quarter's rows in Python memory. These batch choices are proposed implementation parameters, not measured worker-fit guarantees. Indefinite development retention applies to raw, observations, generations, manifests, candidates, quarantine and reports; scratch is temporary and released on both success and failure.

All live-access authorizations remain closed. Read retained provider/SDK/runtime evidence and exact locally installed code; network fetching, credential activity, Azure/SEC access, temporary compute and deployment require their own later authorization. An unavailable cached dependency is an execution preflight blocker, not permission to fetch or change the accepted pin.

## 4. Pinned inputs, versions and storage

Reuse `decode_snapshot_workset`, the referenced source-workset decoder and matching immutable member bindings. Verify workset IDs, exact membership, raw SHA/length, source-kind/period/representation/envelope and source URL. Do not consult `latest_downloaded_snapshot` to select inputs. Workset ID hashes its canonical payload excluding its own ID; it is distinct from the full object's byte SHA. Both must be checked according to their own contract.

Retain acquisition origin `RunContext` unchanged. A separate transform context pins the current parser/schema/image/config. Register production parser `sec-index-parser-v1` and explicit local-only aliases `fixture-index-parser-v1` / `fixture-index-parser-v2`; the second fixture alias exercises a changed processing identity with equivalent parsing semantics and is forbidden for Azure. Original `fixture-envelope-v1` provenance continues to decode; it never masquerades as a row parser. Validate a transform parser before opening adapters.

Preserve `Settings` serialization, origin config hashes, accepted raw/workset IDs and the immutable `sec-owner-binding-v1` registry. New fixed accepted container/table names are adapter constants, not injected defaults that change old config hashes. Test an existing Stage 2 root and retained snapshot worksets without rewriting the registry or inputs.

Processing identity is `(source_id, snapshot_sha256, parser_version, schema_version)`. Its state retains output manifest/reference, source-row count, distinct-key count and per-output-quarter counts. Immutable observation address refines the parent's illustrative path to include both versions:

```text
observations/sec/indexes/source=<id>/sha256=<hash>/parser=<version>/schema=<version>/rows.parquet
observations/sec/indexes/source=<id>/sha256=<hash>/parser=<version>/schema=<version>/manifest.json
worksets/sec/transformed/sha256=<id>/workset.json
curated/sec/filing_index/year=<yyyy>/quarter=<q>/generation=<id>/part-00000.parquet
curated/sec/filing_index/year=<yyyy>/quarter=<q>/generation=<id>/changes.parquet
curated/sec/filing_index/year=<yyyy>/quarter=<q>/generation=<id>/manifest.json
runs/sec/<run-id>/<transform|publish>/<attempt-id>/result.json
```

Logical paths are public application references. Azure physical routing uses only accepted Stage 1 bindings: `observations/*` to container `generations` under its unchanged logical suffix; curated data/change files to `generations`, curated/observation manifests to `manifests`; `runs/*` to `results`; `staging/*` to `raw`. Existing direct `raw/worksets/quarantine/locks` references keep their bytes and addresses. Local storage retains the same logical references. Add streamed `ObjectStore.materialize(path, target)` and use existing `stage(path, Path)` for immutable Parquet writes; `promote` remains raw-only. Verify all output bytes before a referring manifest is created.

Use existing `SourceState` for Processing/Candidate indexes, `Attempts` for attempt records, and accepted **ActivePointers** for `QuarterPublication`. Extend Azure state/factory routing without adding or provisioning tables. **Approvals** remains reserved for Stage 5. Preserve the `open_stores(...) -> (state, objects, leases)` interface and existing large-record content-first Table descriptors/actual ETags.

## 5. Parse and observation contract

Support exactly F1's two bounded families: single-DEFLATE-member `master.idx` quarterly ZIP, strict ASCII/CRLF/`Filename`/ISO dates; plain daily IDX, strict ASCII/LF/`File Name`/compact dates. Reuse acquisition validation over materialized original bytes before parsing. Archive originals remain archives; CRC/member/expanded-size validation remains mandatory. Unsupported envelopes and codecs fail closed.

Recognize the exact header and separator, then require five pipe-separated nonempty fields on every row. Preserve all original five field strings and physical line number. Normalize decimal CIK to 10 digits, trim field padding, retain company/form text and amendment suffixes, validate calendar date, and use filing date for output quarter regardless of source period. An archive path is a safe relative path under SEC Archives and preserves case; reject absolute paths, traversal, empty segments, backslashes, control characters and query/fragment/percent escapes. For the recognized `edgar/data/<decimal CIK>/...` family, reject CIK mismatch. A safe unrecognized legacy path remains usable without inventing accession metadata. A synthetically tested safe legacy filename yields null accession; it is not evidence of a globally observed legacy family. Recognized `<10>-<2>-<6>.txt` filenames yield accession. Normalize only contract fields; no enrichment or name-based identity.

Canonical schema is exactly parent **sec-index-v1**: non-null string `cik/company_name/form_type/archive_path/source_id/source_sha256/parser_version/schema_version`, non-null date32 `filing_date`, nullable string `accession_number`. Observations add `original_fields` (five non-null strings) and `line_number` (non-null int64); preserve duplicate observations. Identical normalized keys/fields collapse only in the canonical output. Conflicting duplicates within one source invalidate that entire source. Do not publish a partial source because earlier batches were valid. Retain line/reason/raw reference in quarantine; an invalid source can never produce an accepted transformed reference or empty replacement.

Compact golden fixtures cover both families, amendments, null accession, identical/conflicting duplicates, unsafe paths/dates, final-line/newline boundaries and cross-quarter daily dates. A separate offline retained-specimen proof parses all ten F1 receipts, compares full row counts/date bounds and selected expected rows to their retained inspections, records original hashes and clearly limits coverage to those receipts.

## 6. Catalog, change reports and withdrawal gate

Each quarter rebuild consumes the active manifest's exact contributing inputs plus incoming transformed references. Preserve unaffected sources. Select at most one snapshot per source: identical hash is the same input; otherwise later receipt wins, earlier receipt is stale; different hashes at the same receipt time are refused as ambiguous. Receipt ordering is a deterministic revision-selection policy, not a claim of SEC coverage. Parser replay reprocesses all selected contributing raw inputs under the new versions; mixed-version active observations are never silently combined into a new canonical schema.

Within a quarter, quarterly values take precedence for keys they contain. Daily-only keys use later source-period date, then later receipt, then source ID as a deterministic tie-break. Identical duplicate rows preserve a deterministic selected provenance. A path change remains a different logical key.

Open/closed classification uses the **publication attempt's pinned date**, never the old acquisition date. A quarter after that endpoint is refused. For an open quarter, retain active keys absent from newer quarterly input, preserve their provenance and report unresolved absences. For a closed quarter with a selected quarterly membership source, its validated membership supplies the proposed replacement: daily observations cannot introduce keys absent from that membership. A closed quarter without quarterly authority may receive conservative daily additions/updates but cannot infer withdrawals. Carry the membership-source hash/reference in the committed manifest so daily replay cannot silently discard that authority.

Report added, updated, withdrawn and unresolved-absence keys with full before/after rows and provenance. Classify updates by canonical business fields, not a mere provenance/parser change; record provenance/version refreshes separately in manifest counts. Complete contributing source set and all versions enter the fingerprint, including membership authority and retained-open-key basis. The parent active generation ID and current quarter mode enter candidate identity, avoiding reuse across different diffs/approval gates. Fingerprints exclude run IDs, build timestamps and incidental scratch names.

If a closed-quarter candidate would remove any active key, write complete candidate files and a content-addressed candidate record naming quarter, candidate ID, base generation, full source-set fingerprint, exact quarterly source hash, manifest and change report. Return `awaiting_approval`; do not change the pointer or mark sources published. An empty or malformed quarterly replacement is refused before candidacy. The Stage 3 publisher always refuses gated candidates, even if a caller supplies a forged approval field; no approval CLI or force bypass is exposed. Stage 5 adds approval validation and mutation against these interfaces.

## 7. Publication, reading and repair

Read the current pointer plus opaque conditional version before candidate construction. Write deterministic sorted Parquet data/change files, then a canonical immutable manifest containing quarter/generation/base, versions/image, exact source set and source fingerprint, membership basis, row/key/change counts, explicit file refs/hashes/lengths and candidate gate. Verify checksums, schemas, counts, filing quarters and unique keys by reading outputs back. Never select files by globbing. Only after complete validation and gate evaluation may an absent pointer be inserted or an existing pointer be replaced using its actual ETag.

On a CAS loss, leave the losing candidate retained, reread the winner, combine its exact source set with the original incoming pins and rebuild both catalog and change report. Re-evaluate the gate against the new base. Bound retries to existing `CAS_ATTEMPTS = 5` and the attempt deadline; persistent races return `publication_conflict`, retaining current readable output and candidates. A candidate made against an old base never becomes current by unconditional write.

An identical source/version/mode/membership fingerprint returns `unchanged` with the existing generation; no pointer advance, new logical rows or second change event. `--force` verifies/recomputes the same immutable transform outputs and may construct an unreferenced equivalent candidate, but cannot overwrite committed output or bypass removal approval.

Reader API resolves one pointer snapshot to its manifest and exact Parquet files, validates identity/checksums/schema/counts/keys and returns generation plus rows. A saved generation capture stays readable after the pointer advances. Missing/corrupt referenced files fail closed without an older-generation or glob fallback. Multi-quarter consumers capture their own generation list.

Crash before file completion or before CAS leaves the prior pointer untouched. Crash immediately after CAS leaves a committed complete manifest; retries inspect the pointer/manifest and repair Processing/PublicationReceipt/Attempt indexes without a second advance. Published flags are per processing identity **and quarter/generation**, so a daily source with multiple output quarters is not fully published after only one succeeds. Reports expose partial quarter advancement, unresolved gaps and gated quarters; it is not cross-quarter transactional success.

## 8. Verification and delivery gates

Plan 3 implements the following matrix; no assertion here means those new tests have already run:

| Contract | Required offline evidence | Plan tasks |
|---|---|---|
| R3 / parent §§4.4–4.6 | Both golden families, synthetic legacy null, amendments, duplicate conflicts, safe paths/dates, full retained-receipt parsing and quarter partitioning | 1–3, 7 |
| R6 / parent §§4.1, 4.5–4.6 | Exact immutable source/snapshot inputs; repeat/no-op; parser-version change on raw storage; no SEC sender/credential path; partial-source resume | 3, 6–7 |
| R9 / parent §§4.5–4.6 | Complete manifests/checksums/unique keys; pointer reader/capture; crashes at three commit boundaries; actual competing processes with CAS loss/rebuild and post-commit repair | 4–7 |
| First-publication §4.4 safeguards | Add/update deltas, open absence, closed replacement gate including concurrent-base gate changes, empty/invalid refusal and daily membership authority | 4–7 |
| Applicable §§5–6 | Named nonzero quarantine/conflict/approval outcomes, result/Attempt crash repair, versioned outputs and durable per-quarter progress | 3, 5–7 |
| Accepted bindings and compatibility | Mocked pinned-SDK paths/ETags; existing v1 config/workset/registry byte identity; streaming outputs and Table size checks; full acquisition regressions | 1, 5, 7 |

Exit requires covering red/green tests, prescribed offline full build/test/CLI check, fresh installed-wheel transform/publish/read proof, retained source/proof hashes and resolved task/whole-branch reviews. Documentation explains replay, pointer readers, gates and repair. All Stage 7 integrated checks remain reserved. Invalid retained rows or cached dependency absence are reported blockers and cannot be bypassed to stamp completion.

## 9. Rollout note

> Roadmap: specs/sec-filing-index-ingestion-roadmap.md, Stage 3 — on plan completion, tick the
> stage and re-validate later stages against what shipped.

Stage 3 remains **unticked**. Approval is pending; no Stage 3 implementation, COMPLETE stamp, retirement, staging, commit, PR, deployment or later-stage routing occurred in this planning session. Stop after presenting Plan 3 for approval. Execution, if approved, starts in a fresh session, rechecks current protected changes and carries only the approved implementing documents into its chosen isolation. At actual plan completion follow `writing-plans`' completion protocol before integration/cleanup; its authoritative stamp must precede any narrowly authorized roadmap checkbox change. Stage 4 still requires a separate owner-initiated roadmap resume.
