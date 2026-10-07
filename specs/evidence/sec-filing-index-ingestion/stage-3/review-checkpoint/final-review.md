**Assessment: Needs fixes for the offline implementation. Stage 3 acceptance remains separately blocked by the retained-source conflicts.** No Critical findings; two Important findings and one Minor finding.

Reviewed the supplied [whole-branch package](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/.sdd/3-sec-filing-index-ingestion-stage-3-spec/review-5f90a211..3c868351.diff), covering 13 commits from `5f90a2116eab21525e88a02d0988567e71d95967` through `3c868351ea8c417d2a5edf88c6091ef0b72d519a`. The review used the current production, test and documentation hunks, approved plan/spec, interface ledger, latest delivery report and actual retained evidence. No files were changed, suites rerun, agents spawned or network operations performed.

**Strengths**

- Source transformation preserves original observations and physical lines, detects conflicting duplicates across the whole source, and accepts outputs only after immutable Parquet readback.
- Candidate validation checks source ranking, membership, complete key coverage, exact-base deltas and provenance refresh counts. The additional immutable base capture closes the earlier suppressed-withdrawal gap.
- Publication uses real conditional pointer operations, rebuilds from the winning source set after a conflict, reevaluates withdrawal gates and preserves losing candidate objects.
- Captured readers validate the complete generation and finish spooling before exposing a row. Saved captures remain independent of later pointer advances.
- The evidence distinguishes successful native implementation proofs from source acceptance and deployed capacity. Real process traces demonstrate insert/replace losses, union-preserving rebuilds, gate reevaluation and all four forced-death boundaries.

**Important I1 — Recoverable receipts currently determine which committed quarters are revisited.**

Location: [etl/commands.py:187](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/commands.py:187), particularly the `PublicationReceipt` scan at line 195.

`_affected_quarters` starts with incoming quarter counts, then discovers previous quarters exclusively through publication receipts. A permitted crash after pointer CAS but before receipt creation therefore leaves a committed quarter invisible to this lookup.

A concrete sequence is:

1. A daily snapshot containing only Q3 rows commits Q3 and dies before its receipt is written.
2. A newer snapshot of the same source changes those filing dates to Q4.
3. A new publish command visits Q4 only, because the incoming reference has no Q3 count and the Q3 receipt is absent.

The command can report success without revisiting or reporting the committed Q3 generation. For daily input, this omits the expected conservative absence reconciliation. An analogous quarterly revision can omit the own-quarter empty-membership refusal. The pointer remains readable, but the command’s affected-quarter coverage is incomplete.

This follows Task 6’s receipt-based discovery wording literally; that wording is insufficient when combined with Task 5’s allowed crash window and the specification’s rule that receipts are repairable indexes rather than publication authority.

**Fix:** discover affected committed quarters from validated pointer/manifest captures, or repair/validate an authoritative source-to-quarter view before relying on the indexes. Add a regression that leaves the old publication unreceipted, publishes a changed-date snapshot without first resuming the old command, and verifies both old and new quarter outcomes.

**Important I2 — An ordinary repair exception after CAS is frozen as a failure that hides the committed generation.**

Locations: [etl/publication.py:102](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/publication.py:102), [etl/commands.py:225](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/commands.py:225), and [cli.py:227](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py:227).

After a successful pointer CAS, `record_publication` can raise an ordinary storage or bounded-CAS exception. `run_publish` catches that exception and constructs a failed `PublicationResult` with both `generation_id` and `manifest_ref` set to `None`. The CLI then writes that result immutably and completes the Attempt.

An exact subsequent invocation replays the saved failure. Its repair loop only handles quarters whose saved outcome is `published` or `unchanged`, so this committed quarter is skipped. A transient ancillary write failure consequently leaves a frozen failed attempt that omits the actual committed capture; its missing indexes require a separate manual repair or new attempt.

The existing tests cover repair exceptions directly at the publication API and hard death/BaseException recovery through the CLI. They do not cover this ordinary-exception command path. It violates the requirements to expose actual per-quarter advancement and repair post-commit failures without falsely treating publication as uncommitted.

**Fix:** preserve the successful commit boundary through error handling. An unresolved post-CAS ancillary failure should leave a resumable attempt without a misleading terminal result, or use a truthful result representation that retains the committed capture and supports repair. Add a CLI regression injecting a one-shot receipt/index failure after actual CAS, then retrying the exact invocation and verifying repaired indexes with an unchanged pointer version.

**Minor M1 — The documented ETL examples select an unsupported acquisition parser.**

Location: [ETL runbook:25](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/docs/runbooks/sec-edgar-etl-publication.md:25), also the publish example at line 31.

Both examples use `conf/sec-edgar-ingest.yaml`. A narrowly scoped inspection of that unchanged configuration confirmed its parser is `fixture-envelope-v1` at [configuration line 40](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/conf/sec-edgar-ingest.yaml:40). ETL explicitly rejects that acquisition provenance label before opening adapters. The later replay paragraph assumes a configuration already using `fixture-index-parser-v1`, but never creates it.

**Fix:** show preparation of a separate ETL configuration with a supported row parser and use its path in both commands. Verify the documented transform/publish sequence against that configuration while preserving acquisition configuration compatibility.

**Spec compliance and evidence**

The seven-task implementation substantially fulfills the approved records, Arrow schemas, exact dependency pins, strict parsing, raw replay, conservative catalog, immutable candidates, CAS publication, captured reading, CLI separation and native proof requirements. The documented refinements—mandatory base sidecar for every noninitial generation, attempted manifest references on publication conflicts, frozen command envelopes and the optional result observer—are coherent with those contracts. The two recovery findings above remain unresolved cross-task gaps.

I inspected the retained full-check logs: all **442 test lines report OK**, the runner reports **160.172 seconds**, and wheel/sdist builds, CLI help, module version and compile checks succeeded. Sequence and isolated installed commands both record exit 0. I independently verified all **7,525 frozen evidence files / 72,546,066 bytes**, with exact inventory coverage and no mismatches. The retained wheel is **110,438 bytes**, SHA-256 `7d370cbe94d82254ae2095e8bcb8993ebef939651fc788181fc6b90906d1cfdc`; its 28 production Python files and README match the reviewed tree. See the [verification record](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/specs/evidence/sec-filing-index-ingestion/stage-3/verification.md).

The historical evidence whitespace limitation is accurately disclosed: full historical/staged evidence checks exited **2**; scoped implementation/prose checks exited **0**. This is not a claim that the complete evidence diff is clean.

**Known blocked acceptance gate**

The two independent retained scans agree on hashes, row counts and quarter totals across **970,622 rows**. SEC-0141, SEC-0142 and SEC-0143 contain **21, 24 and 6** conflicting observations: 45 form-only and 6 company-only differences. Actual transformation refuses those sources at physical lines **6,580 / 87,808 / 40,292**, retains quarantine evidence, preserves raw bytes and creates no accepted processing reference or pointer.

That refusal correctly follows the approved policy. Under spec §8 it still blocks Stage 3 acceptance pending owner reconciliation. Seven accepted receipts and complete parsing coverage cannot substitute for that gate.

**Cannot verify and disposition**

This review establishes no Linux amd64/Python 3.14.8 worker capacity, live Azure/HNS/identity behavior or deployed concurrency. All 22 later Stage 7 checks remain reserved. The new findings are deterministic source-level integration traces; I did not execute additional reproductions under the read-only review restriction. A separate Codex CLI second opinion was **skipped**, as instructed.

**Ready to merge: No.** Resolve the two Important recovery findings and the runbook correction through narrow changes and focused regression evidence. Independently retain the owner-dependent source acceptance blocker; no Stage 3 COMPLETE stamp, roadmap tick, retirement, integration or cleanup is justified.
