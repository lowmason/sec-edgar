# SEC filing-index ingestion — Stage 5: Reconciliation and withdrawal approval

**Status: READY FOR EXECUTION (2026-10-11) — owner accepted the §9 recommendations; implementation not started.**
**Owner:** Lowell Mason.
**Implementing plan:** [Plan 6](plans/6-sec-filing-index-ingestion-stage-5-spec.md).
**Authority:** [Parent design](sec-filing-index-ingestion-spec.md), [ADR](sec-filing-index-ingestion-adr.md), [roadmap](sec-filing-index-ingestion-roadmap.md), accepted [F1](sec-filing-index-ingestion-stage-1-findings.md), completed [Stage 3](completed/sec-filing-index-ingestion-stage-3-spec.md), and Stage 4's completion authority (roadmap "Stage 4 completion" note, [retired Plan 5](plans/completed/5-sec-filing-index-ingestion-stage-4-spec.md) header and [completion record](evidence/sec-filing-index-ingestion/stage-4/plan5-execution/completion/completion-record.md)). Only roadmap Stage 5 (R5, R7, R10) is specified here, plus the recorded rollback the owner assigned to it (§9).

## 1. Reconciliation and scope

Resumed 2026-10-11 against `main` at `6ef957bb` (merged PR #4). Stages 1–4 carry authoritative stamps. The Stage 4 spec deliberately keeps its pre-completion Rollout line because its bytes are hash-bound to the approval; its completion authority lives in the three Stage 4 locations above. Stages 6–8 were re-validated against the shipped code and are unchanged.

Stage 5 re-validation found that the shipped code already provides most of the parts. Stage 3 stages complete gated candidates with a hash-bound gate record. Its closed-quarter membership rule already prevents daily observations from adding keys that quarterly membership excludes. Discovery supports `--refresh`, and the run context supports the `reconciliation` priority. Still missing are: a reconcile workflow; an approval record and operation; reader acceptance of an approved gated generation; operator listing and history; completion rules for snapshots superseded during reconciliation; and the explicit recorded rollback that parent §4.7 requires. Stage 7 rehearses that rollback (parent §7 step 5), and F1 D-04 names its operator, but no stage's Produces line built it until the owner assigned it here.

**Process (owner decision, 2026-10-11):** lean. Each task gets red/green TDD and a review, and a final whole-branch review closes the stage. The stage exit runs the full offline suite plus a wheel build and CLI smoke test. Earlier stages' preservation audits, hash-bound approval snapshots and evidence bundles are not carried forward. Azure adapters stay in step with the local backend.

## 2. Constraints inherited by Plan 6

Copied verbatim from the accepted parent contract:

- The implementation will live in **`packages/sec-edgar-ingest/`**, with `sec-edgar-ingest` as the distribution and CLI name and `sec_edgar_ingest` as the Python import package.
- Backfill, daily ingestion and reconciliation differ in source selection, not in their downloader, parser or publication code.
- The quarterly baseline is reconciled periodically.
- Each scheduled run refreshes every supported quarterly source.
- Unchanged bytes skip transformation when parser and schema versions also match.
- Reconciliation failures leave the last valid catalog active and identify the affected quarters.
- An HTTP failure, absent listing or open-quarter absence is not a withdrawal.
- A closed-quarter replacement that removes records requires explicit approval tied to its source hash before those records leave the active catalog (4.4).
- If keys disappear, stage the entire replacement and a change report; leave the prior generation active until approval names that exact source hash and candidate generation.
- Approval cannot be reused for a later download.
- After a replacement is approved, old daily observations cannot recreate a key it excludes.
- A subsequent valid quarterly snapshot may reintroduce the key, recorded as a new change.
- No response failure, empty replacement or unexplained format change can produce withdrawals.
- A gated candidate is `awaiting_approval`, not current.
- **Withdrawal pending:** retain the active generation and emit an approval request naming exact hashes. This is a distinct gated outcome, not successful reconciliation.
- The pointer update is the publication boundary.
- Per-source published flags are recoverable indexes, not a second commit authority.
- Atomicity is **per quarter**, not across the entire historical dataset.
- Moving a quarter pointer back requires an explicit recorded rollback; it cannot reverse downstream exports already consumed.
- A rollback changes active pointers; it does not erase source history or retract data that consumers have already used.
- CI runs on committed fixtures and mocked SEC responses; it downloads nothing from the SEC.

The accepted pins carry over unchanged: Python **>=3.14**, Requests **2.34.2**, Identity **1.26.0**, Blob **12.31.0** / **2026-04-06**, Tables **12.7.0** / **2020-12-06**, PyArrow **25.0.1**, and the existing `uv.lock`. Stage 5 adds no dependencies and no config keys; `reconciliation.require_withdrawal_approval` is already enforced as `true`. Existing config, workset and binding-registry bytes are never rewritten. Work is offline only: no SEC, Azure, credential, deployment or trigger activity. All 22 Stage 7 integrated checks remain reserved/not_run.

## 3. Reconcile workflow (R5, R7)

`sec-edgar-ingest reconcile` takes the same arguments as `backfill` and runs through the same Stage 4 runner, child dispatcher, member registry, completion and report code. Only source selection differs:

- Discovery runs `discover --mode quarterly --refresh` under discovery ID `workflow-reconcile-<run-id>`. The report validator requires `refresh` for `reconcile` and forbids it for `backfill`/`daily`.
- Requested quarters are the same inclusive span as backfill: `backfill.start_quarter` through the pinned endpoint (all supported quarters). A requested quarter with no readable generation stays a reported gap.
- The workflow context priority is `reconciliation`. Children keep the shipped derivation: only daily discovery is `daily`, and everything else is `backfill`. The coordinator ranks only `daily` ahead of other work ([coordination.py:193](../packages/sec-edgar-ingest/src/sec_edgar_ingest/coordination.py)), so reconciliation and backfill units already share one non-daily turn order (§4.3), and retained child contexts stay replayable.
- Re-downloaded identical bytes resolve to the original `Snapshot` record (`AcquisitionState.remember_snapshot`). Processing identity is therefore unchanged, transform reports `unchanged`, publish reports `unchanged`, and the workflow outcome is `unchanged`.
- Changed bytes go through the same transform/publish path, with Stage 3 precedence, open-quarter retention and the closed-quarter gate. An invalid corrected snapshot is quarantined by the shipped parser. The quarter keeps its prior generation, and the failed member's source period identifies the affected quarter.
- A gated quarter is never reported as success. Its publish outcome and member outcome are `awaiting_approval`, the report counts it in `awaiting_approval_quarters`, and `candidates` (§6) lists the approval request.
- **Run-level gate outcome (amends the shipped Stage 4 reducer; owner decision §9 Q4).** For every workflow command, a run whose only unresolved work is gated is `awaiting_approval` (exit 10), even beside completed sources. A gap or a failed source still makes the run `incomplete` (exit 3). Any other pending outcome (`pending`, `deferred`, `throttled`) makes it `incomplete` beside completed sources and `pending` (exit 4) otherwise. Fatal and all-quarantined precedence is unchanged.
  - Stage 4 §5 says both "mixed progress is `incomplete`" and "gate-only unresolved work is `awaiting_approval`". The shipped reducer read the first phrase broadly: any completed work beside a gate was mixed. The owner adopted the narrower reading on 2026-10-11: mixed means completed work beside non-gate unresolved or failed work.
  - The hash-bound Stage 4 spec is not edited; this section records the amendment. Plan 6 Task 3 updates the one accepted Stage 4 assertion that encoded the old reading (`test_gate_only_and_mixed_gate_progress_preserve_current_pointer`, mixed case).
  - Reconcile refreshes every quarterly source, so a gate usually sits beside unchanged quarters. A typical gated reconcile therefore exits 10.
  - Stored `sec-workflow-result-v1` reports re-validate their outcome with the reducer. A Stage 4-era report written as `incomplete` for a gate beside completed sources therefore no longer validates, and replaying that exact attempt is refused as `state_conflict`. No such report exists outside temporary test state; the retained Stage 4 evidence holds only a gate-only report, whose outcome both readings agree on. The format version is not bumped.
- Quarterly-mode discovery inventory also lists directories of sources still needing acquisition, which can include daily directories. Under `refresh`, every member of those directories is re-fetched. This affects only sources that are still pending, and Stage 5 does not change discovery inventory.

## 4. Supersession and reverts

Stage 3 selects at most one snapshot per source, and the later receipt wins. Stage 4 completion requires a member's *exact* observation in every affected quarter ([completion.py:778](../packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/completion.py)). Under repeated reconciliation, that turns a routine case into a crash:

1. A gated correction S2 is superseded by a newer download S3.
2. S2's member publishes `unchanged`.
3. Completion still says incomplete, and `processing.py` raises `Conflict`, so the workflow fails with `state_conflict`.

**Rule.** For every affected quarter, a member is accounted for when the active generation holds one of these:

- its exact observation, or
- an observation of the same source under the same parser/schema versions, with a different hash and a strictly later snapshot receipt.

This mirrors `select_sources`. Live evaluation (`evaluate_member`) and immutable capture validation (`validate_capture`) apply the same rule. Repair-resolution checks stay exact, because they verify one specific committed publication.

**Reverts are detected and reported, not published.** Identical bytes keep their first receipt time. So a download that returns to older bytes, for example S1 → S2 → S1, binds the original S1 record, and receipt order keeps S2 selected. The source state still records the actual latest observation (`latest_downloaded_snapshot` / `latest_received_at`).

After processing, the runner adds a workflow gap `source_reverted` (retryable) for each processed source and affected quarter where all of these hold:

- the latest observed hash differs from the active selected hash, and
- the latest hash's first receipt is earlier than the active receipt, and
- the active receipt is earlier than the latest observation.

The gap names both hashes, both times and the generation, and the workflow outcome becomes `incomplete` (exit 3). The runner is shared (R5), so the check runs for every workflow command; a revert first seen during backfill or daily is reported the same way. The catalog keeps the selected snapshot.

**Reverts stay unpublished (owner decision §9 Q1).** Publishing them would change Stage 3 receipt ordering, because selection would need each hash's latest observation time. Instead, an operator resolves a reported revert with a recorded rollback (§5) to the generation built from the reverted-to bytes, when the active lineage holds one. The next reconcile then reports `unchanged` and no gap, because the latest download and the active selection agree again. When the lineage holds no such generation, the gap repeats until the SEC serves different bytes.

**Known limitation (deferred, §9).** A gated member whose source later reverts to its base bytes cannot clear. Each run re-stages the same candidate. The candidate's `latest_observed_sha256` then differs from its `quarterly_sha256`, so the operator must not approve it, and the run stays `awaiting_approval`. The future fix is to let a later completed download of the same source supersede older pending members. Stage exit records it in `specs/deferred_items.md`.

## 5. Withdrawal approval and recorded rollback (R10, parent §4.7)

**Approval evidence.** This is one immutable object per approved candidate:

```text
approvals/sec/filing_index/year=<yyyy>/quarter=<q>/generation=<id>/approval.json
```

It is routed to the accepted `approvals` container and written as canonical JSON with format `sec-withdrawal-approval-v1`. Its fields are:

- `quarter`, `generation_id`, `base_generation_id`, `source_fingerprint`
- `quarterly_sha256` — the membership snapshot hash
- `candidate_ref`, plus `gate_sha256`, the SHA-256 of the Stage 3 gate payload
- `manifest_ref`, `manifest_sha256`, `manifest_bytes`
- `approver` — one printable line of at most 256 characters
- `approved_at` — UTC

These fields cover the parent's Withdrawal approval record (quarter, candidate generation, source hash, approver, approval time) and bind the exact candidate. A repairable index record of kind `WithdrawalApproval`, keyed by generation ID, mirrors the object in the accepted `Approvals` table. `table_for` routes it there, and the Azure state store gains a fixed `Approvals` client, the same way `ActivePointers` is handled. Binding-registry bytes are unaffected.

**Reader acceptance.** `validated_manifest` accepts a generation whose manifest says `gate: awaiting_approval` only when its approval object exists, is canonical, and equals the approval rebuilt from that exact manifest, capture and gate payload. It then validates the gate record exactly as for any candidate. Without such an object, the existing refusal stands. All readers, publish paths, repair and workflow completion go through this one function. A saved capture of an approved generation therefore stays readable using object storage alone.

**`approve` operation.** The command is `sec-edgar-ingest approve --config PATH --quarter YYYYQn --generation ID --quarterly-sha256 HASH --approver TEXT [--state-dir PATH]`. Steps:

1. Read the generation's manifest by its exact address. Refuse unless it is an `awaiting_approval` candidate whose content and gate record validate.
2. Refuse unless `--quarterly-sha256` equals its membership snapshot hash.
3. Read the quarter pointer:
   - If the pointer already names the candidate, the result is `unchanged`; the existing approval is re-read and indexed.
   - Otherwise, if the pointer does not name the candidate's base, the result is `approval_stale`, with no writes.
4. Write the approval object. If one already exists for this exact candidate, keep and re-validate it: the first approval wins.
5. Index the approval.
6. Compare-and-swap the pointer from the exact base version. A lost race rereads and resolves to `unchanged` or `approval_stale`.

`approve` leaves Processing/PublicationReceipt indexes alone; the next publish touching that quarter repairs them through the shipped `unchanged` path. Gated workflow members resolve on the next workflow run, because their exact observation is now active. Approval binds one generation ID, which hashes the base and full source fingerprint. So a later download, or a rebuild against a moved base, is a different candidate that needs its own approval.

**Exact read/write set for `approve`** (Stage 6 maps an operator role to it):

- **Reads:** the `ActivePointers` entity; generation manifests, data, change and `retained-base` objects; observation manifests and rows; the gate record under `worksets/sec/candidates/`; the approval object.
- **Writes:** the approval object, the `Approvals` entity, and the `ActivePointers` conditional replace.

F1's preliminary matrix lacks the `worksets` read, and the shared Azure factory also performs its registry conditional write. Stage 6 must grant that read and either confirm the factory step or supply an approver-specific factory.

**Outcomes** (new names are added to `EXIT_CODES`):

| Outcome | Exit | When |
|---|---|---|
| `success` | 0 | This invocation moved the pointer to the candidate |
| `unchanged` | 0 | The candidate was already active |
| `approval_refused` | 2 | Not a valid gated candidate, wrong quarterly hash, or invalid approver text; no write |
| `approval_stale` | 11 | The candidate's base is no longer active; no pointer change |
| `state_conflict` / `internal_error` | 9 | Corrupt evidence or unexpected failure |

**Recorded rollback (owner decision §9 Q2).** The command is `sec-edgar-ingest rollback --config PATH --quarter YYYYQn --from-generation ID --to-generation ID --operator TEXT --reason TEXT [--state-dir PATH]`. Steps:

1. Refuse invalid arguments. The two generation IDs must be different hashes. `--operator` must be one printable line of at most 256 characters, and `--reason` one printable line of at most 1,024 characters.
2. Read the quarter pointer:
   - If there is none, the result is `rollback_refused`.
   - If it already names the target, the result is `unchanged`, with no write.
   - If it does not name `--from-generation`, the result is `rollback_stale`, with no write.
3. Walk the active generation's exact lineage through each `retained-base.json` (§6). Refuse unless the target is an earlier generation in it. A roll-forward, or a generation outside the lineage, is refused.
4. Validate the target exactly as every reader does (`validated_manifest`). An approved gated target is valid only with its approval.
5. Write the rollback record, then index it. If a record already exists for this exact attempted move, keep and re-validate it: the first record wins.
6. Compare-and-swap the pointer from the exact version read in step 2. A lost race rereads, and resolves to `unchanged`, `rollback_stale` or a fresh attempt.

The record is one immutable object per attempted move:

```text
approvals/sec/filing_index/year=<yyyy>/quarter=<q>/rollback=<rollback-id>/rollback.json
```

It is canonical JSON with format `sec-pointer-rollback-v1`. Its fields are:

- `quarter`, `from_generation_id`, `to_generation_id`
- `from_pointer_version` — the exact pointer version the swap replaces
- `to_manifest_ref`, `to_manifest_sha256`, `to_manifest_bytes`
- `operator`, `reason`
- `rolled_back_at` — UTC

The rollback ID is the SHA-256 of the quarter, both generation IDs and the source pointer version. A retry of the same move is therefore idempotent, and a later move between the same two generations gets its own record. A repairable index record of kind `QuarterRollback`, keyed by rollback ID, mirrors the object in the `Approvals` table. `EtlState.rollbacks(quarter)` lists a quarter's records.

The record is written ahead of the pointer swap, so it records an attempted move, not proof of one. A record whose swap lost a race remains. The pointer, and the lineage read from it, decide what took effect.

A rollback is not a pin. Sources stay selected by receipt order, so the next publish of a newer observation builds forward from the restored generation. Re-publishing the rolled-back-from inputs yields the same deterministic generation ID. A rollback changes the active pointer only (§2): it erases no source history, approval or candidate. Rolling back past an approved candidate makes that candidate `pending` again in `candidates`. A later `approve` re-activates it under its first stored approval; publishing never re-applies an approval by itself.

**Exact read/write set for `rollback`:**

- **Reads:** the `ActivePointers` entity; generation manifests, data, change and `retained-base` objects; observation manifests and rows; for a gated target, its gate record and approval object; the rollback object.
- **Writes:** the rollback object, the `Approvals` entity, and the `ActivePointers` conditional replace.

Like `approve`, it leaves Processing and PublicationReceipt indexes to the next publish. F1 D-04 already separates the rollback role; Stage 6 maps it to this set.

| Outcome | Exit | When |
|---|---|---|
| `success` | 0 | This invocation moved the pointer to the target |
| `unchanged` | 0 | The target was already active |
| `rollback_refused` | 2 | Invalid arguments, no active pointer, or a target outside the active lineage; no write |
| `rollback_stale` | 11 | The active generation is not `--from-generation`; no pointer change |
| `state_conflict` / `internal_error` | 9 | Corrupt evidence or unexpected failure |

## 6. Candidates and change history

**`sec-edgar-ingest candidates --config PATH [--state-dir PATH]`** is read-only and prints canonical JSON. On Azure, opening the stores still makes the shared factory's idempotent registry write (§5). For each recorded gated candidate, sorted by quarter and generation, it shows:

- the approval request: `quarter`, `generation_id`, `quarterly_sha256`, `base_generation_id`, `candidate_ref`, the change-file ref, and every withdrawn key's prior row
- `status`: `active`, `pending` (its base is active) or `stale`
- `approved`: whether an approval is indexed
- the membership source's latest observed hash and time, so an operator can see when the SEC no longer serves the candidate's bytes

This is the approval request §5 calls for, and the listing that Stage 6 alerting and Stage 7 runbooks use.

**`quarter_history(quarter, objects, state)`** is a library API. Starting from the active pointer, it returns the newest-first generation lineage through each exact `retained-base.json` capture. Each entry includes:

- generation and base IDs
- mode and gate
- row and change counts
- the membership hash
- the change-file reference
- for approved gated generations, the approval evidence

Recovery tooling reads the change history as this lineage together with `EtlState.rollbacks(quarter)`. After a rollback, the lineage starts at the restored generation, and the rollback records name the generations it left.

## 7. New public contracts (for Stage 6)

- **Commands:** `reconcile` (workflow), `approve` and `rollback` (operator mutations) and `candidates` (read-only).
- **Outcomes:**
  - `approval_refused` and `rollback_refused` (2), and `approval_stale` and `rollback_stale` (11), are new.
  - Workflow gap code `source_reverted` is new.
  - For every workflow command, run-level `awaiting_approval` now also covers gate-only unresolved work beside completed sources (§3).
  - Reports use `runs/sec/<run-id>/reconcile/<attempt-id>/result.json`.
- **Objects and records:**
  - the approval object path and `sec-withdrawal-approval-v1` format
  - the rollback object path and `sec-pointer-rollback-v1` format
  - record kinds `WithdrawalApproval` and `QuarterRollback`, both routed to table `Approvals`
  - workflow priority `reconciliation`

## 8. Verification and boundary

| Requirement | Offline exit proof | Plan tasks |
|---|---|---|
| R5 / §4.2 | Backfill, daily and reconcile share the same runner and the same four checked child commands. Only reconcile discovery carries `refresh`. | 3, 7 |
| R7 / §§4.2, 4.4 | A corrected quarterly fixture yields the expected updates and additions. Unchanged bytes give `unchanged` transform/publish/workflow. Open-quarter absence is retained. An invalid correction keeps the prior generation. A gate beside unchanged quarters is `awaiting_approval` (exit 10) with one `awaiting_approval_quarters`. A superseded gated member completes on the next run. A revert yields `source_reverted` / `incomplete`, and a rollback to the reverted-to generation clears it. | 3, 4, 7 |
| Run-level gate outcome (§3) | For backfill, daily and reconcile, gate-only unresolved work beside completed sources is `awaiting_approval`; adding a gap, a failed source or another pending outcome makes it `incomplete`. | 3 |
| R10 / §§4.4, 4.6, 5 | Reader refuses unapproved and mismatched approvals. Approve succeeds once, is idempotent, refuses a wrong hash or non-candidate, and is stale after the base moves. A later download needs a new approval. A stale daily replay cannot resurrect a withdrawn key. A later quarterly reintroduction is recorded as `added`. | 1, 2, 5, 7 |
| Recorded rollback / parent §§4.7, 10 | Rollback moves the pointer only to an earlier generation in the active lineage, records the move first, and is idempotent. It refuses roll-forward and outside targets, accepts an approved gated target, is stale once the pointer moves on, keeps a lost race's record, and does not pin. | 6, 7 |
| Azure in step | `WithdrawalApproval` and `QuarterRollback` reach `Approvals` through pinned-SDK mocked requests. The factory opens the `Approvals` client. Approval and rollback paths route to the `approvals` container. | 1, 6 |
| §§5–6 | Named outcomes and exit codes, the `candidates` listing, `quarter_history` lineage and rollback records, full offline suite, wheel build, and help for every command | 2, 5, 6, 7 |

**Out of scope:**

- **Roll-forward, pins and candidate dismissal.** `rollback` moves back only within the active lineage. Nothing pins a quarter against later publishes, and no command dismisses a stale candidate.
- **Telemetry and alerts** for pending approvals and last successful reconciliation: Stage 6.
- **Schedules and trigger enablement:** Stages 6 and 8.
- **Approver and rollback-operator identity and credential mapping:** Stage 6.
- **Integrated checks**, including the rollback rehearsal against corrected fixtures: Stage 7.

**Known limitations:**

- Source selection is per quarter (Stage 3 §6). A superseded snapshot's rows in a quarter where the newer snapshot has no rows remain eligible there; this matters only for quarterly sources with cross-quarter filing dates.
- A gated member whose source reverts to its base bytes cannot clear (§4). It is deferred, not fixed, in Stage 5.

## 9. Owner decisions (2026-10-11)

The owner accepted each recommendation below.

1. **Revert semantics: detect and report.** Reverts stay unpublished, and a recorded rollback resolves them (§4). If the SEC restores the *exact original bytes* after an approved withdrawal, the withdrawn key does not return by itself. Each reconcile reports `source_reverted` until the operator rolls back to the generation that holds those bytes. A restoration with any different bytes is a new snapshot and reintroduces normally.
2. **Rollback ownership: Stage 5.** Stage 5 builds the explicit recorded rollback (§5). Stage 6 maps its operator role, and Stage 7 rehearses it.
3. **Stale exit code: 11** for both `approval_stale` and `rollback_stale`. Exit 9 stays reserved for conflicts, corrupt evidence and unexpected failures.
4. **Run-level gate signal: change the shared reducer** for every workflow command (§3). A reconcile-only rule would break R5's single shared workflow path.

The owner also deferred the gated-then-reverted limitation (§4) rather than widening Stage 5 to fix it.

## 10. Rollout note

> Roadmap: specs/sec-filing-index-ingestion-roadmap.md, Stage 5 — on plan completion, tick the
> stage and re-validate later stages against what shipped.

The owner's 2026-10-11 decisions (§9) are applied, and Plan 6 is ready to execute on branch `stage-5-reconcile`. This document is not a completion stamp or a live-access authorization.
