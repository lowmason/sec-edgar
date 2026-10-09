# Stage 4 replanning handoff

## Current owner instruction

**Planning only. Implementation is stopped.** The owner requested stopping implementation and replanning Stage4, chose **"Keep spec; rebuild execution plan"**, and requested doing that in **another session**. Preserve the approved spec, scope, acceptance rules and original approval snapshots. Write a replacement execution plan for owner review; do not resume implementation under the old Plan4 approval or the correction addendum.

The fresh session needs no prior chat history. Use `writing-plans` and relevant design/review skills to rebuild the task boundaries and ordering against the shipped APIs and exact approved specification. The earlier ultra review is an input, not a substitute for a coherent replacement plan. No new requirement needs to be invented to fill its gaps.

## Workspaces and Git state

- Primary project: `/Users/lowell/Projects/sec-edgar`.
- Preserved execution worktree: `/Users/lowell/.codex/worktrees/sec-edgar-stage-4/sec-edgar`.
- Preserved branch: `codex/sec-edgar-stage-4`.
- Partial implementation HEAD: `3713cff7b81836143aaed05220fa77acf61bed73` before the final documentation checkpoint commit carrying this handoff.
- Primary main and local origin/main baseline: `fe95642bddf006f3d2d6cb3ccc57e595d75dc4cd`. No fetch is authorized.

Inspect existing managed artifacts and use `using-git-worktrees` for any planning checkout. The old execution checkout belongs to the previous task and must remain preserved; it is available for read-only inspection. If it cannot be attached/reused safely in the new task, create an inspected managed planning worktree from the preserved branch's final documentation checkpoint HEAD, using native worktree tools. Keep primary read-only. Do not overwrite the old execution branch, remove its worktree, or silently accept its partial implementation.

## Required reading

Read from the preserved execution worktree, or the inspected planning checkout carrying these tracked inputs:

1. `specs/evidence/sec-filing-index-ingestion/stage-4/implementation-handoff.md` — original complete approved execution handoff and preservation constraints, still authoritative for scope/evidence but superseded for permission to continue old-plan implementation.
2. `specs/evidence/sec-filing-index-ingestion/stage-4/approval/owner-approval.json` and its exact spec/plan/roadmap snapshots.
3. `specs/sec-filing-index-ingestion-stage-4-spec.md` — keep this approved spec unchanged.
4. `specs/plans/4-sec-filing-index-ingestion-stage-4-spec.md` — read as the plan being replaced, not the task sequence to execute.
5. `specs/evidence/sec-filing-index-ingestion/stage-4/execution/ultra-plan-review.md` — fresh ultra-effort static review with six defects, exact source references, regression cases and mandatory elaborations.
6. `.../execution/execution-addendum.md` — owner-approved correction interpretations; no permission to restart implementation after the later stop.
7. `.../execution/task-1-gap-interface.md`, `implementation-stop.md`, `sec-edgar-stage4-task1-report.md`, `sec-edgar-stage4-task1-review.md` and the two retained fix1 red/green logs.
8. Relevant existing acquisition/discovery/workset/ETL/publication/reader/result/CLI/proof code and completed Stage3 spec/plan, independently checking any interface the replacement plan consumes.

Do not rely on an ignored progress ledger or private temporary draft as the only source of any requirement. The old `.sdd/4-sec-filing-index-ingestion-stage-4-spec` ledger remains available for diagnosis, but this handoff and retained tracked evidence carry the stop/replan state.

## Verified authority and preservation

Reverify approved source/snapshot hashes before planning:

- Spec: `5b822a4113eaa18c53a18ae71f244d6b69d2abd9e533381a69644e4b88cd1b0a`.
- Plan4: `d23d62c965f51a4af9a89edd615cc77ed267b58601875f06bcd27cc339c2508c`.
- Approved roadmap: `0101934eadf0ca3241b03a458c80ec300012430875c44522410836ab6c0ecc03`.
- Approval receipt: `1a4beabfe15f8d39bb710ba7f92fb9ac1ea60eafc926a8f28905ad6c2ea176bc`.

Approval remains evidence of the exact original scope despite PROPOSED headers; preserve those bytes and headers. The replacement plan is a new document, not an in-place edit of the approved original. Check `specs/plans/` and `specs/plans/completed/` for the next plan ID; expected5, but inspect. Do not retire Plan4/spec or stamp Stage4 complete.

Fresh execution preservation: `/private/tmp/sec-edgar-stage4-execution-preservation-bm3tc33_`,30,017 records/424,389,627 bytes, verified against retained payload. Two prior reconciliation inventories and the historical Stage3 closeout were verified. Full post-setup primary hash check was unchanged; primary index was separately reconfirmed empty at the stop. No primary code/Git/index mutation has been made. See tracked `execution/primary-preflight.json`, `post-setup-primary-check.json`, and `authority-preflight.json` for exact evidence.

Preserve all retained bytes, primary historical untracked Stage3 originals, ignored roadmap, and required primary absences:

- `packages/sec-edgar-index-ingest/README.md`
- `packages/sec-edgar-index-ingest/pyproject.toml`
- `packages/sec-edgar-index-ingest/src/sec_edgar_index_ingest/__init__.py`
- `packages/sec-edgar-index-ingest/src/sec_edgar_index_ingest/py.typed`

No `git add -A`, stash/reset/restore in primary. Completed Stage3 documents in origin/main are authoritative over historical untracked originals. Preserve inspected managed worktree/branch state and approved inputs.

## Partial implementation and tests

- `c308137a`: exact approved documents and preservation receipts.
- `775866aa`: test-only baseline race repair and complete retained proof. Worker barrier moved after receipt recovery selects download and before coordinator ownership; no production/assertion/timeout change. Independent review clean. Full guarded baseline452 tests passed158.483s, exit0.
- `604a1c46`: owner-approved execution addendum, ultra review and gap interface.
- `791e91dc`: Task1 strict workflow contracts/reducer/tests,23tests passed0.066s.
- `3713cff7`: Task1 invariant fix: quarantine requires failed status and no accepted transform. Actual red25tests/8failures0.085s, then same25tests green0.087s, exit0; staged whitespace clean.

Task1 remains **unaccepted**: initial independent review found the invariant defect; its scoped re-review was interrupted on the owner's stop. Tasks2–7 have not started. No workflow CLI, member registry, dispatcher, runner or installed Stage4 proof exists. Do not claim full-suite validation of the partial Stage4 implementation; the452baseline precedes it. Preserve partial code as candidate evidence, explicitly decide whether a replacement-plan task adopts/retests/reviews it or replaces it. Do not silently reset it or tick it complete.

All old agents are completed/idle/interrupted; no implementation/test process is running. A preliminary new read-only completion-design agent was interrupted when the owner requested the fresh session; no output from it is accepted.

## What the replacement plan must resolve

1. **Affected-quarter completeness:** new observation quarter_counts omit formerly affected quarters; align with actual publisher obligations so partial replacements stay pending.
2. **Quarantine semantics:** failed transport-prefix retention can coexist with accepted later download; distinguish that evidence from terminal whole-source refusal and enforce quarantine as a failed-source subset.
3. **Cross-run repair obligations:** a committed pointer does not erase a known unfinished publish/ancillary repair. Model current data authority, historical immutable captures and unfinished command obligations explicitly.
4. **Child identity:** namespace deterministic child attempts by parent workflow command so backfill/daily may share run/attempt IDs without collision.
5. **Aggregate precedence:** retain baseline gaps while giving solely quarantined sources the specified quarantined/exit7 outcome; independent missing sources/directories and mixed progress remain incomplete. Assess the partial gap-attribution interface; do not treat a marker as storage authority.
6. **Installed dependencies:** prove the complete accepted frozen lock, including transitive pins, using cached hash-bound installation and reviewed-wheel --no-deps, not only five direct versions.

Also make exact original parent/listing/session provenance, binding-winner readback, decoded Processing-version equality, child-result/capture validation, immutable before-dispatch completion captures, frozen selection/replay/index repair, legacy isolation and no recursive projection executable requirements. Define every consumed helper before its independently testable consumer. Avoid another task-order contradiction like old Task2 depending on a Task4 helper. Split the oversized recovery/orchestration task by actual independent review boundaries and keep each task self-contained with meaningful real-store red/green evidence.

Suggested planning direction: completion and evidence contracts before orchestration; separate checked dispatch, member processing, frozen invocation/selection/report persistence and legacy reconstruction. Evaluate alternatives against existing APIs rather than copying this suggestion into an unverified plan. Carry every approved requirement through a traceability and acceptance matrix, including fresh native/process and installed-wheel proofs.

## Boundaries and next handoff

Offline only: no live SEC/Azure/authentication/network fetch/dependency change/deploy/image build/schedule activation/merge/later-stage work. Exact pins and limits remain as in approved spec. SEC-0141/0142/0143 stay exact whole-source quarantines with21/24/6 conflicts, no accepted observations or publication; do not weaken parsing. All22 Stage7 checks remain reserved/not_run.

Deliver the replacement plan as a concrete, self-contained saved artifact with exact task interfaces, complete meaningful regression setups, commands, review gates, preservation and integration procedures. Self-review spec coverage, placeholders and cross-task signatures; use a fresh structural review where justified. Present it for owner review and a fresh execution handoff. **Do not execute it in the planning session.** This handoff authorizes replanning, not replacement-plan implementation.
