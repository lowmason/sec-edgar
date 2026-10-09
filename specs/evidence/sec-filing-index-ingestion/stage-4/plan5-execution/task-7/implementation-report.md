# Plan 5 Task 7 implementation report

Status: implemented, verified, and committed; independent Task 7 review and acceptance remain pending and gate Task 8.

Implementer/self-reviewer: `/root/task7_implement`, Codex inherited available model (provider lacks Sonnet/Opus aliases). Isolated checkout `/Users/lowell/.codex/worktrees/sec-edgar-stage4-plan5/sec-edgar`, branch `codex/sec-edgar-stage4-plan5`, accepted predecessor base `c5a6989da3a21d348dda29eeb842b9d2aef1e9e5`. Owned commit `d31f08d40bd815ce1431003332c8ab6448db909f`, `feat: reconstruct verified legacy workflow backlog`, contains exactly `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/legacy.py` and `packages/sec-edgar-ingest/tests/test_workflow_legacy.py`, 545 added lines. Evidence and this report remain unstaged for the controller.

## Interfaces and preserved authority

Implemented `bootstrap_legacy(store, objects) -> tuple[Error, ...]` and `reconstruct_parent(session, store, objects) -> str`. Existing pure `validate_parent_recovery(parent_ref, descriptor, objects) -> Mapping` is imported/re-exported unchanged from accepted Task 2 provenance and returns exact original `session` and ordered `progress`. No predecessor file was edited. Capture objects are canonical create-once `sec-workflow-parent-recovery-v1` JSON; the `WorkflowParentRecovery` index key is the original recovered workset ID with exact ref/sha256/bytes descriptor.

Reconstruction freezes every original required unit in hierarchy order and its original DirectoryProgress value or None. Accepted validator reopens actual listing bodies and receipts, checks original ancestor authorization/context and reconstructs exact parent bytes. Missing progress becomes a failed `discovery_pending` unit; no source is invented. Parent and recovery objects are committed and verified before immutable index insertion. Existing capture is validated and preserved; a changed frozen original session refuses. DiscoverySession is never rewritten or finalized by recovery.

Legacy bootstrap has isolated boundaries for registry records, each original discovery revision, child call, command Attempt/reference, source projection/binding transfer, and Source/Processing record. Unresolved corrupt records remain visible as `legacy_member_unresolved` with canonical `record_sha256` and kind; no unavailable Versioned.key assumption is introduced. Existing projection references are collected before validating their records, so even corrupt projections cannot become original parents. Valid registered projections resolve only to their original parent. Repeated bootstrap retains bounded original singleton registry and immutable pins, without recursive projections or fabricated source completion.

Actual acquisition/ETL command objects are re-read and compared against command context and stored results; collect/transform snapshot references reopen the exact source parent. Checked/ordinary publish command validation uses accepted completion authority, preserving absent-uncommitted versus corrupt-begun publication distinctions and the original immutable repair anchor. Successful raw bindings transfer only after exact snapshot metadata and retained raw bytes verification; divergent winner returns a gap and remains unchanged. Existing completion and current-version diagnostics remain the accepted predecessor responsibility.

## Exact red/green and regression evidence

All evidence is create-only under `specs/evidence/sec-filing-index-ingestion/stage-4/plan5-execution/task-7/`. Each file includes exact argv, complete combined stdout/stderr and actual child exit. The unchanged scoped command is:

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_legacy.py -v
```

| Evidence | Result |
| --- | --- |
| 01-red.txt | Exit 1, expected absent legacy module import (one loader error); original proposed tests installed before production |
| 02-proposed-green.txt | Exit 0, original 7 methods PASS, 23.575s |
| 03-boundaries.txt | Exit 0, 9 methods PASS, 28.835s; added binding/corrupt projection and strengthened capture hashes |
| 04-final-green.txt | Exit 0, 9 methods PASS, 28.764s; includes actual alternate ancestor listing/receipt tampering |
| 05-provenance.txt | Exit 0, test_workflow_provenance.py, 16 methods PASS, 3.042s |
| 06-completion.txt | Exit 0, test_workflow_completion.py, 20 methods PASS, 71.340s |
| 07-discovery.txt | Exit 0, test_discovery.py, 43 methods PASS, 8.873s |
| 08-worksets.txt | Exit 0, test_worksets.py, 20 methods PASS, 0.213s |
| 09-collection.txt | Exit 0, test_collection.py, 35 methods PASS, 11.151s |
| 10-complete-green.txt | Exit 0, final 9 methods PASS, 28.849s; real recovery capture explicitly created before close/reopen |
| 11-diff-check.txt | Exact prescribed git -c core.whitespace=cr-at-eol diff --check, exit 0 |
| 12-stage-owned.txt | Exact explicit git add of the two owned paths, exit 0 |
| 13-staged-diff-check.txt | git -c core.whitespace=cr-at-eol diff --cached --check, exit 0; checks newly created staged files |
| 14-commit-owned.txt | Exact prescribed commit command, exit 0 |

Each named regression used the same offline/frozen guarded runner and exact filename, changing only `-p` from the scoped command. Final scope plus named regressions totals 143 passing methods. There were no setup errors, cache blockers, observed behavioral implementation failures after the initial absent-module red, or weakened assertions. Extra cases passed the prescribed implementation and did not lead to speculative changes. Guarded dependencies were already cached; no fetch/new dependency occurred. No broad suite or Stage 7 integrated check ran.

## Required cases and deviations

Original seven real CommandHarness regressions remain intact: downloaded source exact original pin/parent and repeated bootstrap; interruption at actual parent-object write; interruption before quarter progress insertion; corrupt parent versus valid sibling/fresh ordinary discovery; immutable recovery capture tampering; persisted registry/recovery capture; corrupt Source and Processing versus valid original parent. Interruption raises Crash(BaseException) across actual LocalObjectStore/LocalStateStore boundaries while invoking shipped discovery.

The before-parent-write test explicitly proves recovered ID is absent from session current, predecessor and history, and session bytes/version remain identical. Missing progress preserves all required units with failed discovery and zero invented members. Alternate canonical capture/descriptor objects refuse ref/SHA/length changes, frozen execution context, omitted required ledger, absent ancestor, accepted members attached to failed progress, source ID/URL relabeling and endpoint relabeling. An additional variant changes a real root listing to remove the advertised year and rewrites its matching alternate receipt and SHA/length; successful retained children still refuse due to absent original ancestor listing entry.

Two added real-command tests verify divergent singleton Binding winner refusal without changing either winner, original parent pin or retained raw bytes; and corrupt WorkflowMember projection references in discovery history cannot supply original provenance or increase the registry. The close/reopen test now explicitly calls reconstruct_parent after real discover/collect because the original finalized-parent bootstrap snippet alone did not create a recovery capture. It asserts a nonempty real WorkflowParentRecovery entry, closes/reopens through CommandHarness's shipped open_stores on the same root and checks identical canonical full-row hashes for DiscoverySession/WorkflowMember/WorkflowParentRecovery/Binding and every retained object hash.

Production is exactly the proposed Task 7 implementation. Test changes are stronger coverage, not assertion relaxation. No approved plan/spec/snapshot, retained input, binding/config/workset bytes outside temporary fixtures, primary checkout or controller ledger was edited. No parser/version/pin/provider change, deployment/authentication/compute/Azure/SEC access or trigger enablement occurred. All 22 Stage 7 integrated checks remain reserved/not_run. Indefinite retention remains unchanged.

## Self-review and independent review handoff

Self-review scope: `d31f08d40bd815ce1431003332c8ab6448db909f` against accepted base above, exactly the two owned files. Checked capture schema/address/byte validation, original required-unit ledger and listing ancestry, object-before-index ordering, first retained capture preservation, unchanged session state, new recovered ID branch, failure/missing progress distinction, isolated unresolved record hashes, corrupt projection filtering before provenance adoption, exact snapshot pin transfer/raw readback and repeated bounded registry growth. Checked accepted publication helpers and repair authority are called rather than bypassed. Final staged whitespace check and owned commit succeeded.

Applied clean-code rules: original-authority recovery remains within workflow provenance boundary (G6/G30), projection/binding corruption and storage interruption boundaries have deterministic real-command assertions (T1/T5/T6), descriptive binding-winner and corrupt-projection test names state their behavior (N1/N4), and close/reopen named index/object hash maps expose immutable evidence checks (G19). Kept proposed design-intent comments explaining why an uncommitted publication command cannot reach CAS (C3). No adjacent tidying or module movement.

Independent reviewer identity, findings and acceptance are not claimed. Controller must dispatch fresh task review, resolve findings and accept Task 7 before Task 8. No known failing scoped/regression check remains; broader integrated/deployed fit remains intentionally reserved and unmeasured.


## Independent review correction: fix round 1

Reviewer `/root/task7_review` returned Needs fixes / spec noncompliant for initial range `c5a6989d..d31f08d4`, one Important malformed-session isolation finding. Retained initial review is `specs/evidence/sec-filing-index-ingestion/stage-4/plan5-execution/task-7/review-initial.md`. Controller authorized this scoped correction; independent re-review and acceptance remain pending, and Task 8 remains gated.

Correction commit `9d5ae2932d825ca56df4b4a964f09270cf8f1ac5`, `fix: isolate malformed legacy discovery units`, contains only legacy.py and test_workflow_legacy.py, 71 insertions/2 deletions against `d31f08d40bd815ce1431003332c8ab6448db909f`. Evidence and appended report remain unstaged for controller retention. Applied receiving-code-review and systematic-debugging; verified the feedback against actual original sort and accepted pure validator rather than adding blanket exception handling.

Root cause: reconstruct_parent called `u['url'].count('/')` while sorting raw frozen units before rebuild_recovered_parent could validate them. Numeric/null/object URL values raised AttributeError, which correctly was not in LEGACY_ERRORS but therefore escaped the session boundary and hid valid sibling progress. The prescribed initial implementation had this same defect. The actual new real-command regression first interrupts LocalObjectStore.put_once at the original parent write, then runs shipped discovery for a valid sibling, changes only the interrupted session frozen units, and bootstraps. It checks an unresolved DiscoverySession gap with exact canonical record SHA, exactly one validated sibling projection, and unchanged canonical entire corrupt row including storage version. Six near-boundary variants cover numeric/null/list/object URLs, null unit, and wrong ledger container shape.

The helper `_validated_frozen_units` now checks frozen mapping, nonempty array ledger, each unit mapping/exact existing fields, safe text URL/period/role/optional bridge_period and allowed original roles. Both reconstruct_parent and the DiscoverySession bootstrap boundary call it before sorting or parent adoption. It raises existing caught ValueError for malformed shapes; LEGACY_ERRORS and public APIs/schemas remain unchanged. This is basic prevalidation only; actual URL/listing/receipt/frozen-context authority still comes from accepted predecessor pure validator/read_parent. No malformed record is rewritten or silently accepted, and no AttributeError was blanket-caught.

Neighboring raw nested operations were inspected narrowly: legacy reads frozen units before pure validation; optional unit bridge fields and role/period are now type-checked at that same boundary. Other legacy accesses use StateStore detached mapping values, validated record decoders, or indexing/hash operations whose malformed inputs already raise caught ValueError/TypeError/KeyError/Conflict. No predecessor, parser, retained input, provider, or unrelated module edit was required. No broader suite, fetch, live access, new dependency or reserved Stage 7 action occurred.

All correction evidence is create-only under task-7/fix-1 and retains exact argv, complete stdout/stderr and exit:

| Evidence | Actual result |
| --- | --- |
| 01-red.txt | Exact unchanged guarded legacy command, exit 1; 10 methods, 3 genuine AttributeErrors at raw sort for numeric/null/object URLs, 34.109s; no setup/cache failure |
| 02-green.txt | Same exact command, exit 0; 10 methods PASS, 34.139s |
| 03-provenance.txt | Same guarded runner, exact test_workflow_provenance.py, exit 0; 16 methods PASS, 3.070s |
| 04-completion.txt | Exact test_workflow_completion.py, exit 0; 20 methods PASS, 71.541s |
| 05-discovery.txt | Exact test_discovery.py, exit 0; 43 methods PASS, 8.868s |
| 06-worksets.txt | Exact test_worksets.py, exit 0; 20 methods PASS, 0.221s |
| 07-collection.txt | Exact test_collection.py, exit 0; 35 methods PASS, 11.412s |
| 08-diff-check.txt | Prescribed git -c core.whitespace=cr-at-eol diff --check, exit 0 |
| 09-stage-owned.txt | Explicit git add of only the two owned files, exit 0 |
| 10-staged-check.txt | git -c core.whitespace=cr-at-eol diff --cached --check, exit 0 |
| 11-commit-owned.txt | Correction commit command, exit 0 |

Final correction scope plus listed regressions totals 144 passing methods, no warnings. Original nine methods and assertions remain intact; new test was retained unchanged red to green. Code deviation from proposed snippet is required prevalidation restoring its promised per-record isolation. Self-review checked guard placement before all original revision/reconstruction paths, caught typed validation rather than programming-error suppression, unchanged corrupt row/version, valid sibling authority and bounded registry, and exact two-file staged scope. Applied coherent validation helper at the boundary (G6/G30), descriptive units validator (N1/N4), and malformed typed/container boundary tests alongside real sibling evidence (T5/T6). Independent reviewer clearance is not claimed.
