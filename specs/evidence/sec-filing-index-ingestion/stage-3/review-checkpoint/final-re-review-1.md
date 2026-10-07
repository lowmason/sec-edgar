**Approved for the offline implementation in scoped repair round 1. I1, I2 and M1 are ADDRESSED. No new Critical, Important or Minor findings were identified. Stage 3 acceptance remains independently BLOCKED.**

The reviewed repair range is BASE `3c868351ea8c417d2a5edf88c6091ef0b72d519a` through delivery HEAD `78a1d3151c72fca586b261f7b33830505e0e77f6`. Production code and documentation remain at `2343f39f0e21adc2ad401a9346a8c9ffa0509040`; the final commit adds evidence. I used the supplied [complete repair package](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/.sdd/3-sec-filing-index-ingestion-stage-3-spec/review-3c868351..78a1d315.diff) and [evidence-only supplement](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/.sdd/3-sec-filing-index-ingestion-stage-3-spec/review-2343f39f..78a1d315-evidence.diff), without rereading unchanged repair code or documentation.

**Per-finding disposition**

- **I1 — ADDRESSED.** Affected-quarter discovery now uses validated authoritative publication captures, including when ancillary receipts are absent. The retained regression checkpoints establish an old committed Q3 with zero receipts followed by a newer source revision moving rows to Q4. The daily case reconciles both quarters, retaining Q3's row with one unresolved absence and zero withdrawals. The quarterly case reports Q3 `invalid_source`, preserves its exact pointer, and independently publishes Q4. Corrupt prior manifests, data and pointer fingerprints fail closed.
- **I2 — ADDRESSED.** Ordinary post-commit repair failures retain truthful committed quarter results and leave the invocation resumable instead of freezing a misleading failed terminal result. The five focused scenarios preserve generation/manifest references, omit a terminal result object, and retain retryable error details. Exact retries preserve the frozen context, repair both receipts and `Processing.published`, leave pointer versions unchanged, and subsequently replay identical output.
- **M1 — ADDRESSED.** The [runbook](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/docs/runbooks/sec-edgar-etl-publication.md) now uses the separate supported ETL configuration. The [actual documented sequence](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/specs/evidence/sec-filing-index-ingestion/stage-3/final-review-fix1/runbook/report.json) successfully transforms an explicitly seeded snapshot and passes its exact returned transformed reference to publish. Both commands exit 0 and produce the expected single Q4 filing. The original acquisition context remains exact, with `fixture-envelope-v1` provenance; the new ETL context selects `fixture-index-parser-v1`. Acquisition configuration and raw bytes remain unchanged.

**Spec compliance and strengths**

The repairs restore the approved distinction between authoritative pointer state and repairable indexes. They preserve per-quarter atomicity, strict source conflict refusal, complete captured-generation validation and exact command resumption. The regression coverage exercises the actual integration boundaries that produced the findings, including ordinary exceptions after successful commit.

The runbook proof explicitly identifies its guarded `cli.main` wrapper and synthetic preparation. It does not claim an unguarded console invocation or live acquisition. Current verification documentation clearly separates current repaired-code evidence from the historical `3c868351` proof.

**Evidence inspected**

I inspected the retained command logs, state checkpoints, workset and manifest payloads, child-process traces, timeout records and relevant new proof-script/report hunks.

- The [final full check](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/specs/evidence/sec-filing-index-ingestion/stage-3/final-review-fix1/full-check/command.json) exits 0: **452 successful test records in 163.537 seconds**, followed by successful wheel/sdist build and the recorded help, version, compilation and whitespace checks.
- Fresh sequence and isolated installed proof commands exit 0. Their independently retained child records show real same-base insert/replace CAS conflicts, loser rebuilds preserving the row union, and withdrawal-gate reevaluation. All four process-death boundaries exit 73; recovery preserves the appropriate old or new complete capture and does not advance an already committed publication.
- Timeout evidence records both owned children dead before emergency cleanup, bounded partial-start cleanup, and lossless 23-byte stdout/stderr captures with `exit: null`.
- I independently verified all **2,070 new inventory records / 15,471,496 bytes**, with safe paths, exact coverage and matching hashes. The prior **7,525 records / 72,546,066 bytes** remain exact against their frozen inventory. Copied focused code and documentation evidence matches the previously reviewed originals.
- The current wheel is **111,195 bytes**, SHA-256 `eb8bb3b318b3b1a4fe1983291efb92161e22fac998f86230b5f2b7f3cf15c3ab`. I independently compared all **28 Python source files**, package README metadata and the retained/dist wheel bytes. Installed proof records confirm execution outside the checkout with `PYTHONPATH` absent and imports from isolated site-packages.
- Scoped implementation/prose whitespace passes. The full staged evidence check exits 2 for preserved blank context lines in two archived diffs; this is accurately disclosed. I do not characterize the complete evidence diff as clean.

**Limits and acceptance gate**

This review used existing evidence and read-only inspection; it did not rerun tests, mutate files or reopen live access. The separate Codex CLI second opinion is **SKIPPED**, as required for a Codex controller. The controller's [preservation audit](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/.sdd/3-sec-filing-index-ingestion-stage-3-spec/controller-verification/audit-final-fix1.json) records primary-tree preservation and no audit failures.

Evidence remains native macOS ARM64/Python 3.14.0. All 22 later Stage 7 checks remain reserved; no Linux worker, deployed Azure identity/ETag behavior or actual capacity is established.

**Stage 3 acceptance remains BLOCKED by the 51 conflicting retained observations: SEC-0141/0142/0143 contain 21/24/6 respectively.** Strict refusal and preservation remain required under the approved specification. This implementation approval does not authorize a completion stamp, roadmap tick, retirement, integration, merge or cleanup.
