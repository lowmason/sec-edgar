# Reconciliation and withdrawal approval

Stage 5 adds four commands:

- `reconcile` refreshes every supported quarterly source through the Stage 4 workflow runner.
- `candidates` lists gated withdrawals.
- `approve` activates one exact gated candidate.
- `rollback` moves a quarter back to an earlier generation of its exact lineage, with a record.

Everything here uses local fixture state or offline evidence. Live SEC, Azure, credential, schedule and deployment work stays reserved for Stages 6–8.

## Run a reconciliation

`sec-edgar-ingest reconcile` takes the same arguments as `backfill`: config, run, execution and attempt IDs, and deadline. Local fixtures also take a fixture pack, state directory and date. Discovery is always `--mode quarterly --refresh`, with discovery ID `workflow-reconcile-<run-id>`; there is no public `--refresh` flag. Requested quarters run from `backfill.start_quarter` through the pinned endpoint. The report is `runs/sec/<run-id>/reconcile/<attempt-id>/result.json`.

| Outcome | Exit | Meaning |
|---|---|---|
| `unchanged` | 0 | Every refreshed source returned bytes that are already published |
| `success` | 0 | At least one quarter published a correction |
| `incomplete` | 3 | A gap (including `source_reverted`), a failure, or non-gate pending work beside completed sources. Read `gaps` and member outcomes |
| `awaiting_approval` | 10 | The only unresolved work is gated, even beside completed sources. Review `candidates` |

A failed or quarantined correction leaves the quarter's prior generation active. The failed member's source period names the affected quarter.

A `source_reverted` gap means the SEC now serves bytes identical to an older snapshot than the active one. The active generation stays, and every reconcile reports the gap. To follow the SEC, roll back (below) to the generation whose membership hash equals the gap's `observed_sha256`; `quarter_history` lists each generation's membership hash. If no generation in the lineage holds those bytes, the gap repeats until the SEC serves different bytes. Restored bytes that differ in any way are a new snapshot and publish normally.

## Review a withdrawal request

`sec-edgar-ingest candidates --config PATH [--state-dir PATH]` prints `{"candidates": [...], "error": null, "outcome": "success"}`. Each entry names:

- `quarter`, `generation_id`, `base_generation_id`, `quarterly_sha256` and `candidate_ref`;
- the change file, and every `withdrawn` key's prior row;
- `status`:
  - `pending`: its base is active and the source still serves the candidate's bytes;
  - `superseded`: its base is active, but a later download of the source has different bytes. `approve` refuses it. Once a later download of the source completes, the following run drops the superseded gated member;
  - `active`;
  - `stale`: the base moved on, or an approved candidate's generation was later replaced by a generation other than its base;
- `approved`;
- the membership source's `latest_observed_sha256` and `latest_observed_at`.

`approved` means an approval was recorded for this exact candidate, not that it was ever active. The pointer, `quarter_history` and `EtlState.rollbacks` show what took effect.

Before approving, confirm all three:

1. `status` is `pending`.
2. Every `withdrawn` row should leave the active catalog.
3. `latest_observed_sha256` equals `quarterly_sha256`. A later download with different bytes lists the candidate as `superseded`, and `approve` returns `approval_stale` for it. When the SEC goes back to the base's bytes, the run that downloads them still reports `awaiting_approval`; once that download has completed, the following run drops the superseded gated member. The candidate keeps listing `superseded`: candidates are never deleted, and the status compares the source's latest download with the candidate's bytes. A later download that itself withdraws rows does not clear the hold, and neither does a quarantined one. A download quarantined at transform has already become the source's latest download, so the candidate lists `superseded` and `approve` refuses it while the gated member stays held. A download refused at its envelope never becomes the latest download, so the candidate stays `pending`.

## Approve

```text
sec-edgar-ingest approve --config PATH --quarter YYYYQn --generation ID \
  --quarterly-sha256 HASH [--approver TEXT] [--state-dir PATH]
```

`--approver` is required on the local-fixture backend and refused on Azure. On Azure, `approve` signs in with the operator's `az login` and records `entra:<tenant-id>/<object-id>` followed by the account's user name. The same holds for `rollback --operator`.

| Outcome | Exit | Next action |
|---|---|---|
| `success` | 0 | The pointer moved. The next reconcile resolves the gated members. |
| `unchanged` | 0 | The candidate was already active. |
| `approval_refused` | 2 | Correct the arguments. Nothing was written. Exit 2 with empty stdout is a usage or configuration error; see stderr. |
| `approval_stale` | 11 | The base moved (`error.details` names `active_generation_id` and `base_generation_id`), or a later download supersedes the candidate (`error.details` names `latest_observed_sha256`). Reconcile, then review the current candidates. |
| `state_conflict` / `internal_error` | 9 | Corrupt evidence or an unexpected failure. Stop and investigate. |

The approval object is immutable: `approvals/sec/filing_index/year=<yyyy>/quarter=<q>/generation=<id>/approval.json`, format `sec-withdrawal-approval-v1`. The first stored approval wins. An approval binds one candidate generation, so a later download, or a rebuild on another base, needs its own approval. `approve` writes the approval object (the decision), then an activation record (the move), then the conditional pointer replace. The record is at `approvals/sec/filing_index/year=<yyyy>/quarter=<q>/generation=<id>/activation=<activation-id>/activation.json`, format `sec-approval-activation-v1`, and both are indexed in `Approvals`. `unchanged`, refusals and an `approval_stale` found before the swap write no activation; an activation whose swap lost a race stays as evidence of the attempt, and the pointer decides what took effect. stdout names it in `activation_ref`. A retry of the same exact pointer move keeps the first attempt's record: the first record of an attempted move wins, so the re-submitted actor is not recorded for that move. `approve` does not repair Processing or PublicationReceipt indexes; the next publish that touches the quarter repairs them.

`approve` writes the approval record before it swaps the pointer. If the swap loses a race to a newer generation, `approve` returns `approval_stale` and an exact-bound approval record for that candidate can remain. It authorizes nothing by itself and cannot be used for any other candidate or download. If the quarter is later rolled back to that candidate's base, a further `approve` activates the candidate under the stored approval, unless a later download of the source has different bytes (the candidate then lists as `superseded`, and `approve` returns `approval_stale`); that re-activation writes only an activation record, attributed to its own actor.

## Roll back

```text
sec-edgar-ingest rollback --config PATH --quarter YYYYQn --from-generation ID \
  --to-generation ID [--operator TEXT] --reason TEXT [--state-dir PATH]
```

`--from-generation` must be the active generation, and `--to-generation` an earlier generation of its exact lineage; take both from `quarter_history`. The command writes an immutable record first, at `approvals/sec/filing_index/year=<yyyy>/quarter=<q>/rollback=<id>/rollback.json` (format `sec-pointer-rollback-v1`), then swaps the pointer. A record whose swap lost a race stays as evidence of the attempt; the pointer decides what took effect.

| Outcome | Exit | Next action |
|---|---|---|
| `success` | 0 | The pointer moved to the target. |
| `unchanged` | 0 | The target was already active. |
| `rollback_refused` | 2 | Correct the arguments; the target must be earlier in the active lineage. Nothing was written. Exit 2 with empty stdout is a usage or configuration error; see stderr. |
| `rollback_stale` | 11 | The active generation is not `--from-generation` (it changed, or that generation was never active). Re-read `quarter_history` and decide again. |
| `state_conflict` / `internal_error` | 9 | Corrupt evidence or an unexpected failure. Stop and investigate. |

A rollback is not a pin: the next publish of a newer observation builds forward again. It cannot retract data consumers already used. Rolling back to an approved candidate's base shows it `pending` again, or `superseded` if a later download of the source has different bytes. From `pending`, `approve` re-activates it under the original stored approval and records the re-activating actor in a new activation record. Rolling back further shows it `stale`, and `approve` returns `approval_stale`; reconcile to stage a new candidate.

## History

`quarter_history(quarter, objects, state)` in `sec_edgar_ingest.etl.history` returns the active generation's lineage, newest first, through each exact `retained-base.json`. Each entry carries the counts, gate, mode, membership hash and change file, plus the approval for each approved gated generation. `EtlState.rollbacks(quarter)` returns the quarter's rollback records; after a rollback, they name the generations the lineage no longer shows.

## Not provided

- Roll-forward, pins and dismissal of stale candidates.
- Alerts for pending approvals and schedules are Stage 6's Azure definitions (Plan 10).
- Integrated checks, including the rollback rehearsal, belong to Stage 7.
