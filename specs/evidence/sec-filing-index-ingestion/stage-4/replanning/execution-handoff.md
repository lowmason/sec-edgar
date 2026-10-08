# Approved Stage 4 Plan 5 execution handoff

**Owner approval recorded 2026-10-08 at 14:12:29 America/New_York. This planning session remains stopped.** A separate session may execute the approved offline Stage 4 scope after the preservation gate below is reconciled. Approval does not certify that the archived original worktree has been restored.

The [fresh owner receipt](approval/owner-approval.json) binds the unchanged Stage 4 specification, replacement Plan 5 and original approval-roadmap snapshot. The direct owner message was “Approved.” Do not request approval of the same Plan 5 scope again. Preserve PROPOSED headers in approved source/snapshot bytes; this receipt supplies the approval precedence. Original Plan 4 and its addendum remain historical inputs; their former permission cannot replace this handoff.

## Read before acting

Read the complete files, using the preserved planning checkout as the initial read-only source:

- [Plan 5](../../../../plans/5-sec-filing-index-ingestion-stage-4-spec.md), including all eleven tasks, code/regressions, commands, traceability and preservation/integration gates.
- [Approved Stage 4 specification](../../../../sec-filing-index-ingestion-stage-4-spec.md), completed Stage 3 spec/Plan 3 and the referenced parent/ADR contracts.
- [Original stop/replanning handoff](../execution/replanning-handoff.md) and [original implementation handoff](../implementation-handoff.md), including every retained review/addendum/Task 1 evidence file they require.
- [Planning verification](verification.json), [structural review](structural-review.md), [fresh approval preflight](approval/approval-preflight.json), [fresh owner receipt](approval/owner-approval.json) and its read-only [approved Plan 5 snapshot](approval/approved-plan-5.md).

Read and use using-git-worktrees, subagent-driven-development and verification-before-completion. Follow the relevant engineering/testing/review skills at the task boundary; use executing-plans only if the owner chooses inline execution. Resolve actual available models/roles; do not claim unavailable Opus/Sonnet/Haiku aliases.

## Verify authority and preserve evidence first

The planning checkout is `/Users/lowell/.codex/worktrees/sec-edgar-stage-4-replan/sec-edgar`, branch `codex/sec-edgar-stage-4-replan`. The reviewed document commit is `bf36795fd548cdec40d3707a337f6787418726dd`; the approval/handoff documents are a subsequent documentation-only checkpoint on that branch. Resolve its actual local commit and verify ancestry and the exact hashes before selecting the execution base. No network fetch is required or authorized.

| Approved document | SHA-256 |
|---|---|
| Plan 5 source and approved-plan-5 snapshot | `87f9108735a13a9699086e5f50f1d4ce082c740d7f58eb47d37fdd775da67b45` |
| Stage 4 spec source and original approved-stage-4-spec snapshot | `5b822a4113eaa18c53a18ae71f244d6b69d2abd9e533381a69644e4b88cd1b0a` |
| Original approval-roadmap snapshot | `0101934eadf0ca3241b03a458c80ec300012430875c44522410836ab6c0ecc03` |
| Original Plan 4 source/snapshot | `d23d62c965f51a4af9a89edd615cc77ed267b58601875f06bcd27cc339c2508c` |
| Original Plan 4 owner receipt | `1a4beabfe15f8d39bb710ba7f92fb9ac1ea60eafc926a8f28905ad6c2ea176bc` |

**Preservation reconciliation is still open. Before execution mutations, complete the owner-reviewed reconciliation required by Plan 5.** The original stopped checkout `/Users/lowell/.codex/worktrees/sec-edgar-stage-4/sec-edgar` remained absent at approval, despite the owner's earlier “recovered” report. The stopped branch `codex/sec-edgar-stage-4` and archive snapshot `refs/codex/snapshots/44e1d887f038bc90b963848b95a277c13f57f9d9` both retain `e870a7318d47699c0e4a76ab59fba72781b0debe`. Track restoration through the owning chat's managed worktree attachment; do not treat a Git checkout or copied tracked files as restoration of ignored evidence. Do not use UI/database workarounds to bypass attachment ownership.

The pre-archive retained inventory has 30,854 records. Exact ignored recovery at `/private/tmp/sec-stage4-ignored-recovery-phpsldej` was reverified: 1,555 records, 147,893,973 regular bytes and three exact symlink targets, including all twelve SDD files and the ignored roadmap. Preserve `receipt.json` SHA-256 `a1ccf73e2032ed2dd18f9f441c96f365d08f8f94496010d34f4c6c2f306a3597` and its payload. The 433 unmatched records are 374 `.venv` runtime/installation records and 59 package bytecode files. The verified evidence recovery does not waive the full retained-tree/managed-attachment gate. If reconciliation requires an owner decision, request that specific preservation decision; the Plan 5 approval is already recorded. Do not begin implementation while this gate remains unresolved.

Preserve these input roots and every root named by Plan 5; never use them as output directories:

- `/private/tmp/sec-edgar-stage3-merged-closeout-hhgufen8`
- `/private/tmp/sec-edgar-stage4-reconcile-9mbg9qog`
- `/private/tmp/sec-edgar-primary-reconcile-1t9zru9x`
- `/private/tmp/sec-edgar-stage4-execution-preservation-bm3tc33_`
- `/private/tmp/sec-edgar-stage4-replanning-ubszs55d`
- `/private/tmp/sec-stage4-ignored-recovery-phpsldej`

Primary `/Users/lowell/Projects/sec-edgar` remains read-only. HEAD/local origin/main are `fe95642bddf006f3d2d6cb3ccc57e595d75dc4cd`; its original 30,007 file/symlink records and index SHA-256 `739086e5194794b7845942dfe0699994f0845f7a28bdb2518e8f8318f5f52f60` matched at approval. Seventy-one additional Stage 4 recovery files appeared there and match the stopped checkpoint; preserve them in place. Keep historical untracked Stage 3/4 documents, ignored roadmap/wheels/dist/evidence and all four legacy `sec-edgar-index-ingest` package absences. Never stage, stash, reset or restore in primary; never use `git add -A`.

Once reconciliation passes, create a fresh preservation preflight and inspect this chat's managed artifacts before creating/reusing a separate execution checkout from the verified approval/handoff commit. Use native managed worktree tools under using-git-worktrees. Preserve both stopped and planning branches/checkouts/evidence. Record primary HEAD/index/status, regular/symlink inventories, approved hashes and required absences before/after worktree operations. Setup must remain offline; missing exact cached artifacts block the relevant step.

## Execute only Plan 5, in order

Tasks 1–11 are the execution contract. Candidate contracts at commits `791e91dc` and `3713cff7` remain unaccepted; Task 1 adopts them only as a candidate and requires fresh tests/review. Keep the test-only baseline race repair `775866aa` and original logs. Historical 452 baseline tests and the candidate's earlier green results discharge no fresh Stage 4 gate.

Follow each task's owned files, earlier-task APIs, meaningful red/green cycle, exact guarded commands and fresh spec/quality review. Keep actual outputs in distinct create-only evidence directories. Commit explicit paths in the execution checkout only. No member, task or workflow becomes complete from a flag, stdout status or unvalidated pointer. No later task begins past an unresolved predecessor review gate.

All F1–F6 and R1/R2 regressions remain required: every affected quarter; retry-prefix versus terminal refusal; ordinary and checked unfinished publication repair; parent-command child namespace; checked quarantine/mixed-progress precedence; full applicable frozen dependency graph. Preserve exact member/binding/snapshot/version authority, empty-parent listing receipts, all required discovery units, conservative boundary progression, older backlog and validated deadline accounting. Reports and replay retain immutable original evidence; current completion additionally checks current publication membership and repair obligations.

The strict SEC-0141/0142/0143 whole-source refusals remain exactly hash-bound with 21/24/6 conflicting observations, no accepted Processing/ObservationRef and no publication. Keep original specimen exit 1 and the distinct Stage 3 acceptance amendment. Do not edit raw bytes, weaken the parser, select a duplicate winner, accept zero-row replacements or infer a supported historical range from bounded fixtures.

Keep accepted Python/library/service API pins and complete uv.lock unchanged. All SEC/Azure/authentication/network/deployment/image/schedule authorizations remain closed; all twenty-two Stage 7 checks remain reserved/not_run. Stage 5 approval/reconciliation operations, Stage 6 image/IaC/ADF/schedules, Stage 7 integration and Stage 8 production coverage/activation remain outside this execution scope.

Finish with Task 11's fresh full offline suite/build/help/version/compile/whitespace gates, native and isolated installed backfill/daily/reader proofs, full transitive lock inventory and wrong-transitive refusal, exact source/wheel/installed byte inventory and retained process-death/reopen evidence. Obtain independent whole-branch review and owner review of actual coverage. Apply completion/retirement protocol only after those gates; preserve the approved source/snapshot bytes. Integration/cleanup remains a later deliberate owner decision. No merge, push, deployment, activation or removal of preserved worktrees follows automatically from passing checks.

## Prompt for a fresh execution session

> Execute the approved Stage 4 replacement Plan 5 in a separate offline session. Read and follow the complete handoff at `/Users/lowell/.codex/worktrees/sec-edgar-stage-4-replan/sec-edgar/specs/evidence/sec-filing-index-ingestion/stage-4/replanning/execution-handoff.md` and its exact-hash owner approval receipt. Use subagent-driven-development and using-git-worktrees. First reconcile the open retained-worktree/ignored-evidence preservation gate and run a fresh preservation preflight; implementation starts only after that gate passes. Preserve the stopped and planning branches/worktrees, primary checkout, approved snapshots, all retained evidence and strict whole-source quarantine rules. Execute Plan 5 tasks in order with fresh red/green evidence and reviewer gates. Do not request Plan 5 approval again, assume recovery is complete, change the specification, fetch dependencies/network data, or expand later-stage/live scope.
