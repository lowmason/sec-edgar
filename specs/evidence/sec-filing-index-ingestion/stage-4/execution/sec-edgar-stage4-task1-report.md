# Task 1: coverage and workflow result contracts

Controller final fix1 GREEN: exact Step2 guarded offline command exit0, all25 tests passed0.087s, no warnings/errors. Test code unchanged between fix1 actual RED (8 failures) and minimal2-line production GREEN. Full actual output /private/tmp/sec-edgar-stage4-task1-fix1-green.log; red /private/tmp/sec-edgar-stage4-task1-fix1-red.log. Scoped re-review pending; prior pending statements below describe their recording time.

Status: GREEN_READY for controller application and verification; implementation green has **not yet run**. No task completion, passing-suite, commit or review acceptance claim is made in this report.

## Scope and authority

Read `.sdd/4-sec-filing-index-ingestion-stage-4-spec/task-1-brief.md` as the requirements source, including its verbatim Global Constraints. The controller confirmed preparation/owner approval and baseline `775866aae5cc2c9cf974be6a614716a14548f081` with 452 passing baseline tests; those are controller-supplied facts, not this agent's executions. Read the owner-approved six-correction execution addendum and ultra plan review in `/private/tmp`; F5 applies to this task. Original proposed-status brief/snapshot bytes were preserved.

Skills applied: test-driven-development and clean-code; clean-coder read for scope boundaries. No adjacent cleanup performed. Only assigned new workflow contracts and tests were prepared. No managed-worktree writes, Git mutation, escalation, network operations, test execution, dependency change, Stage 2/3 source change, or subagent dispatch was performed by this agent. Controller applies the absolute-path patches and runs checks.

Owned files:

- `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/__init__.py`
- `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/contracts.py`
- `packages/sec-edgar-ingest/tests/test_workflow_contracts.py`

Prepared artifacts:

- `/private/tmp/sec-edgar-stage4-task1-red.patch`: tests only, 23 test methods, already applied by controller.
- `/private/tmp/sec-edgar-stage4-task1-green.patch`: only the two new production files, no test adjustment.
- `/private/tmp/sec-edgar-stage4-task1-interface.md`: exact F5 gap-details interface and Task 4 authority requirements.

## Requirements implemented by the pending green patch

Frozen `MemberResult` and `WorkflowResult` records inherit existing strict typed nested `Record` conversion and detached immutable mappings. The decoder-compatible field annotations use `collections.abc.Mapping`, including nested directory-outcome mappings. Member validation enforces exact member SHA, source/snapshot/transformed workset path shapes, allowed child commands and safe paths, accepted parser/schema versions, unique quarter results, successful captures for complete members, and strict exclusion of accepted transforms/completion from whole-source quarantine.

Workflow validation enforces the format version, daily/backfill context/path namespace, UTC end and nonnegative end ordering, unique member IDs, source workset reference shape, nonnegative integer discovery/backlog intent counters, exact reduced outcome/counters, unique/disjoint already-complete source hashes, requested-quarter ordering and uniqueness, and canonical boundary dates. Invalid already-complete collections and missing required intent counter keys are refused with ValueError. This remains structural validation: future tasks must validate exact stored-object and child/publication authority.

The public `member_status`, `summarize` and `workflow_path` signatures match the brief. Every existing EXIT_CODES outcome is classified explicitly in tests; unknown outcomes are refused through existing `exit_code`. Reduction uses each source identity's worst status, distinct source download/transform/quarantine progress counts, quarter publication counts, fixed fatal precedence, explicit mixed-progress incomplete status, pure awaiting-approval state, old-backlog handling and valid zero-output contract support. Zero-output contract support does not authorize empty IDX parser acceptance.

F5 is corrected before generic gap/incomplete reduction: a nonempty set of terminal failed whole-source quarantined members yields `quarantined` only if all retained workflow gaps carry exact checked structural attribution to those selected source refusals. An empty gap set also permits that outcome. Independent gaps, malformed attribution, mixed valid/refused progress, or nonterminal quarantine remain incomplete. Fatal outcomes still take precedence.

F5 exact interface: gap code `baseline_publication_missing`; details marker `coverage_cause='selected_source_quarantine'`; nonempty unique array `source_ids`, every identity belonging to selected quarantined members; `gap.source_id`, if present, must belong to its attribution array. Each gap may name an exact subset because quarters can have different causes. No gap is dropped. Task 4 must establish complete successful discovery, exact selected source/refusal evidence, and absence of independent cause before producing this marker. See the interface artifact for complete elaboration.

No broadening of existing `read_result` or redefinition of publication authority. No resource/dependency pin or original retention change. Strict retained SEC-0141/0142/0143 quarantine acceptance remains unchanged. All live-access authorizations remain closed; all 22 Stage 7 integrated checks remain reserved/not_run.

## Red evidence and required green verification

Exact brief Step 2 command, executed by controller in the managed worktree:

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_contracts.py -v
```

Controller-confirmed actual RED: exit 1; `ModuleNotFoundError: No module named 'sec_edgar_ingest.workflows'`; unittest reported one import-failure test in 0.000 seconds. No dependency or network failure. This confirms absence of the requested production module under the guarded cached environment before implementation preparation.

GREEN: **not yet executed**. Controller must apply the pending green patch and repeat the command above; expected 23 tests passing. Controller owns broader regression/compile/whitespace/review/commit checks and must append actual commands, output, and disposition before marking Task 1 accepted.

The 23 tests cover all registered outcomes, unknown outcome rejection, empty daily/discovery failures/old backlog, mixed valid-invalid progress, worst-state deduplication and distinct progress counters, pending and fatal precedence, quarter publication/approval counts, zero-output support, reference/version rejection, missing successful captures, duplicate quarters, strict nested Mapping/DirectoryOutcome roundtrips, immutable/detached nested values, unknown nested keys/types/counters, invalid identity/time/quarter/date ordering, invalid intent counters, disjoint already-complete captures, workflow path validation, and F5 retained-gap/exit-7, independent failures, malformed/foreign attribution, mixed progress, and fatal precedence.

## Static self-review and choices

Compared the pending production source against the brief's fields/public interfaces and all 23 test assertions. No actual green execution was performed. The F5 exception is narrowly isolated in a private predicate, preserving retained evidence and avoiding broad suppression of baseline gaps. Counts and fatal priority remain the brief's selected semantics. Mapping decoding freezes gap `source_ids` arrays as tuples; the private predicate accepts that frozen representation and refuses non-array/string/duplicate/foreign attribution before set comparisons. Actual authority remains an orchestration responsibility.

Applied: descriptive source/quarantine/capture variable names (N1, N4); named format/parser/reference constants (G25); explicit all-quarantined condition and separate attribution predicate (G19, G28); cohesive contracts/reduction module without unrelated extraction (G30, G34); meaningful strict-codec, coverage-boundary and F5 refusal tests (T1, T5, T6).

Material remaining concern: structural F5 attribution can only validate internal consistency with supplied member records. Task 4 must validate it against exact immutable listing/selection/child/refusal/publication evidence; these contracts never make a supplied marker an independent authority. Green, regression and fresh review acceptance remain pending controller execution.

## Controller green verification

Controller applied the exact green patch with no test changes and ran the same Step 2 guarded offline command in the managed worktree. Exit 0; all 23 named tests passed; no warnings/errors.

```text
Ran 23 tests in 0.066s

OK
```

Status after this verification: implementation green, independent task-scoped spec/quality review pending. The prior GREEN_READY statement describes the report's preparation time. No full Stage4 completion is claimed.

## Review round 1: failed-subset quarantine correction

Received `/private/tmp/sec-edgar-stage4-task1-review.md`; applied receiving-code-review to evaluate its Important finding against the actual MemberResult constructor. The existing cross-field condition excludes complete outcomes but permits all four pending outcomes with `transformed=False, quarantined=True`. That conflicts with the approved whole-source terminal refusal semantics and can produce quarantined counters with zero failed sources. The correction is within assigned Task 1 contract scope; no new policy, stored-object authority, parser acceptance, F5 interface, or retained evidence change is proposed.

Prepared `/private/tmp/sec-edgar-stage4-task1-fix1-red.patch`, tests ONLY, absolute managed path. Two regression methods each enumerate `pending`, `deferred`, `throttled`, and `awaiting_approval`: direct MemberResult constructor rejection, and nested WorkflowResult decoder rejection from otherwise-valid pending report mappings with counters adjusted to match the inconsistent member. Adjusting the quarantine counter isolates the missing member invariant from counter-disagreement validation. Existing terminal failed quarantine and F5 tests remain unchanged.

Controller-reported pre-review Task 1 GREEN, as supplied in the review: original 23 tests passed, exit 0, 0.066 seconds; staged whitespace check clean. These are supplied controller results, not agent executions. Fix round 1 RED is pending; expected eight `ValueError not raised` subtest failures across the two added methods, exposing direct and nested acceptance of the inconsistent records. No production fix prepared before confirmed red.

Required controller command for red and green:

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_contracts.py -v
```

Applied: targeted table-driven cross-field boundary regressions (T5, T6), without managed-worktree writes, test/Git execution or unrelated edits. Awaiting actual controller red output.

### Round 1 confirmed red and pending green fix

Controller confirmed actual fix1 RED using the guarded offline Step 2 command above: exit 1; `Ran 25 tests in 0.085s`; `FAILED (failures=8)`. All four pending outcomes were accepted both by the direct MemberResult constructor and nested matching-counter WorkflowResult decoder. The original 23 methods passed. These results were supplied by the controller; this agent ran no tests.

Prepared `/private/tmp/sec-edgar-stage4-task1-fix1-green.patch`, changing only the MemberResult cross-field quarantine check. It now requires both no accepted transform and `member_status(outcome) == 'failed'` for quarantined members. Reusing the existing status classifier rejects every current PENDING/COMPLETE outcome and continues to reject unknown outcomes through exit_code. Existing complete-member capture checks, terminal failed quarantine acceptance, reducer/F5 attribution, public interfaces and retained gaps are unchanged. The rejection message describes both required constraints.

Static self-review: the two-line production change addresses the reproduced constructor failure; strict nested Record decoding constructs MemberResult and therefore enforces the same check. No speculative or unrelated edits. Applied: enforce one shared status classification in the cross-field invariant (G19, G28), preserve focused fault-boundary regressions (T5, T6).

Fix1 GREEN is **not yet run**. Controller must apply this patch and repeat Step 2; expected 25 passing methods. Controller remains responsible for actual output, review-round recheck, broader checks and acceptance/commit. No completion claim is made here.
