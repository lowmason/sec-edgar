# Plan 5 Task 6 implementation report

Status: implementation committed and verified; independent Task 6 review/acceptance remains pending and gates Task 7.

Implementer/self-reviewer: `/root/task6_implement` (Codex, inherited available model; provider does not expose Sonnet/Opus aliases). Checkout `/Users/lowell/.codex/worktrees/sec-edgar-stage4-plan5/sec-edgar`, branch `codex/sec-edgar-stage4-plan5`, accepted predecessor base `a3988cd7a3a9638bea915d819b1b52a0ca60ee01`. Owned commit `2ed1413fb234686c353200534aa31a1c19400c64`, `feat: persist frozen workflow selection and immutable results`. Commit contains only `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/results.py` and `packages/sec-edgar-ingest/tests/test_workflow_results.py`. Evidence and this report are intentionally unstaged for the controller.

## Interfaces and authority

Implemented call signatures remain `freeze_workflow(current, intent, store, objects) -> RunContext` (current is the workflow context), `freeze_selection(context, selection, store, objects)`, `read_workflow_result(path, store, objects) -> WorkflowResult`, `write_workflow_result(result, store, objects, observer=None) -> str`, and `workflow_key(context)`. No runner, CLI, legacy reconstruction or later proof-harness dependency was introduced.

The WorkflowAttempt key is SHA256 of canonical `[run_id, command, attempt_id]`. Its payload has exactly context/intent/selection_ref/result_ref. Intent, selection and report sibling objects remain canonical create-once JSON. Object descriptors have exactly ref/sha256/bytes. Member receipt descriptors preserve the existing six fields ref/sha256/bytes/member_id/parser_version/schema_version and now reject extras. The selection retains exact `sec-workflow-selection-v1` fields, singleton jobs, sorted unique members, their original projections and T4 captures, disjoint already-complete captures, checked discovery call, actual frozen session and exact required-directory ledger. Result intent retains exactly the nine prescribed fields.

Intent index begin precedes intent-object commit. Canonical saved intent recovers a missing workflow index and the surviving begun index supplies the original start after an early crash. Selection object precedes selection descriptor repair; report object precedes result descriptor repair. A contradictory existing context, invocation or descriptor refuses; no overwrite is called repair. Exact finished replay is readable after the deadline; unfinished expired work refuses. Source-unit counts and every selected member are rechecked against selection, receipts and immutable completion captures.

Historical validation reopens immutable member/parent/discovery provenance, checked child captures, T5 receipts, completion captures, and captured repair resolutions. It does not compare an old capture against a later active quarter pointer or make current repair checks. Current repair resolution remains T5 responsibility. Publication-resumable or repair-pending terminal children cannot finalize. Real non-resumable missing-result member failures remain failed, retain actual original Attempt/command/terminal evidence, and never become COMPLETE. T4 resolution validation transitively reopens the original repair-authority anchor. No accepted predecessor implementation was edited.

## Exact verification and red/green history

All evidence is create-only under `specs/evidence/sec-filing-index-ingestion/stage-4/plan5-execution/task-6/`. Each named text file retains exact child argv, complete combined stdout/stderr, and actual child exit. Every suite invocation used this unchanged command in the isolated checkout:

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_results.py -v
```

| Evidence | Actual result |
| --- | --- |
| 01-red.txt | Exit 1, absent `sec_edgar_ingest.workflows.results` import; original proposed tests installed first, production absent |
| 02-proposed.txt | Exit 1, 12 methods, 10 errors, 37.392s; original snippets installed, concrete fixture/serialization mismatches reproduced |
| 03-fixture-corrected.txt | Exit 1, 12 methods, 1 failure and 6 errors, 40.824s; remaining frozen child-call serialization and no-op role mutation reproduced |
| 04-normalized.txt | Exit 0, original 12 methods PASS, 47.427s; ResourceWarnings exposed test-only SQLite deletion helper lifetime |
| 05-boundaries-red.txt | Exit 1, 16 methods, 1 failure and 1 error, 59.955s; extra receipt descriptor accepted (production defect), new terminal-test Error constructor setup error |
| 06-boundaries.txt | Exit 0, 16 methods PASS, 62.704s; no warnings |
| 07-repair-transitive.txt | Exit 1, 17 methods, 1 setup error, 66.198s; actual repair report was written before nonexistent Versioned.key access |
| 08-green-complete.txt | Exit 0, all 17 methods PASS, 70.875s; no warnings |
| 09-diff-check.txt | Exact `git -c core.whitespace=cr-at-eol diff --check`, exit 0 |
| 10-stage-owned.txt | Exact explicit `git add` of only the two owned files, exit 0 |
| 11-staged-diff-check.txt | Actual staged `git -c core.whitespace=cr-at-eol diff --cached --check`, exit 0 |
| 12-commit-owned.txt | Exact prescribed commit command, exit 0; commit above |

The Task 6 brief lists no separate named predecessor regression commands; controller confirmed no additional filenames were required. No broad full suite or reserved integrated check ran. Offline/frozen cached dependencies were available. No dependency download, network fetch or live trigger occurred.

## Acceptance evidence

The four required distinct checks pass: skipped before-dispatch source captures are required and counted once; historical reports read their original generation after a pointer advances; exact finished expiry replay works while changed invocation/correlation/image/parser/deadline refuses and unfinished expiry fails; fatal discovery without a result retains frozen prior pending jobs and ownership_lost accounting. Original discovery tests also retain empty parent/full listing authority, root/year/empty-quarter required roles and bridge, listing bytes/receipts, actual begun-but-unfinished session ledger, current parser backlog refusal, changed selection and missing/tampered evidence refusal, and exact missing workflow/child-index replay.

Added Task 6 cases cover intent commit interruption and original-start recovery, intent-object missing-index recovery, selection object before index interruption and exact-only repair, extra member receipt descriptor refusal, actual failed member terminal receipt/report replay and terminal-byte corruption refusal, and a genuine repair-resolution report after WorkflowAttempt/WorkflowRepairObligation index deletion. The latter refuses corruption of `worksets/sec/workflow-repair-authority/call-sha256=<originalcallSHA>/obligation.json`, preserving accepted T4 immutable anchor authority transitively. The failed-member test likewise reopens the T5 retained actual original child `terminal.json`.

## Concrete deviations from proposed snippets

1. Original snippet fixtures invoked collect/transform/publish through EvidenceFixture.invoke's sequence step IDs. Accepted T5 correctly requires `<command>-<member_id>`. The owned test adds invoke_member using the real Dispatcher and canonical member steps. Assertions remain intact; no predecessor validator was relaxed.
2. Public checked calls and completion captures are FrozenMappings. The shipped to_mapping_value normalizes tuples, but a mutable list can still contain FrozenMappings. `_plain` first uses shipped freeze then shipped to_mapping_value and canonical JSON, preserving every field. The test explicitly normalizes fixture calls/captures before constructing mutable evidence arrays. `_validate_report` uses one normalized full intent for exact immutable comparisons, avoiding tuple-vs-array and nested frozen representation mismatches. This does not weaken equality or drop fields.
3. `simple_pack` creates its root with exist_ok=False, so the empty-parent test uses a fresh `root / 'pack'` child instead of the already-created TemporaryDirectory root.
4. The required-unit role tamper originally rewrote unit zero to `quarter`, which was already its role. It now changes the actual root unit to quarter; the refusal assertion is unchanged and exercises a real substitution.
5. Boundary test reproduced acceptance of an extra member receipt descriptor field. Report validation now requires exactly the predecessor six-field descriptor schema before verification/readback.
6. The owned test-only SQLite deletion helper's `with Connection` committed without closing. It now uses contextlib.closing and an explicit commit, eliminating reproduced ResourceWarnings without production deletion APIs.
7. Added proof setup corrections are retained honestly: Error requires source_id/details, and Versioned exposes original repair call_sha256 in its value rather than a key attribute. Neither was a production red result.

No approved plan/spec/snapshot, retained input, binding/config/workset bytes, primary checkout or controller ledger was edited. No new dependency, pin change, parser relaxation, provider integration or Stage 7 action was introduced. All 22 Stage 7 integrated checks remain reserved/not_run and live access remains closed.

## Self-review and handoff

Scoped diff: accepted base above to owned commit above, exactly two added files, 1,011 lines. Self-review checked exact schemas/identity/correlation, object-before-index ordering, missing-index recovery versus contradiction refusal, immutable-only historical capture validation, complete receipt/evidence accounting, incomplete publication refusal, count derivation, canonical finished replay, and absence of later-task imports. New module stays within the prescribed workflow persistence boundary (G6/G30); no adjacent tidying or module movement was done. Applied explanatory normalized intent variable (G19), immutable boundary/expiry/corruption tests (T5/T6), and exact names for member-step helper and receipt descriptor refusal (N1/N4). Design-intent deadline and test-only deletion comments remain (C3).

Independent reviewer identity/findings/acceptance are not claimed here. The controller must dispatch fresh task review of the owned commit and resolve findings before Task 7. No known failing scoped check remains; broader/integrated/deployed fit is intentionally unmeasured and reserved.


## Independent review correction: fix round 1

Reviewer `/root/task6_review` found three Important authority gaps in initial range `a3988cd7..2ed1413f`; retained review is `specs/evidence/sec-filing-index-ingestion/stage-4/plan5-execution/task-6/review-initial.md`. Initial status was NOT compliant / Needs fixes. The controller authorized spec-preserving corrections before Task 7. Implementer applied receiving-code-review and systematic-debugging, traced each boundary to accepted predecessor APIs, and reproduced all findings before changing production. No predecessor edits were necessary.

Owned correction commit: `6cc18036480ead01247b52aff5348d2c27a5ac1f`, `fix: bind workflow reports and selections to original authority`. Exactly results.py and test_workflow_results.py, 76 insertions/13 deletions. Independent re-review/acceptance remains pending; this report does not claim reviewer clearance.

Root cause 1: manual report receipt decoding called validate_member_evidence but bypassed WorkflowMembers._read_receipt and its _validate_context. A canonical receipt transplanted into another begun attempt could retain the original child calls while changing only receipt context/path/descriptor. The regression creates that exact attempted transplant, accounting for the revised discovery-free frozen selection, and requires Conflict. Report validation now uses the full predecessor immutable receipt reader. It then checks decoded member and context against the report, the complete descriptor against the predecessor's exact descriptor, and evidence member against frozen selection. Existing predecessor context validation binds workflow command/attempt/run, execution, original start/deadline, pinned date, exact reproducible settings and allowed collection/repair provenance. The reader uses immutable objects; it does not introduce current completion or repair checks.

Root cause 2: selection arrays could agree with each other while omitting every real discovered source, and discovered_sources was only checked as a nonnegative integer. Separate real-parent regressions show coherent omission of members/jobs/member_provenance/already_complete and positive substitution 999 must both refuse. Selection validation now derives each exact discovered singleton projection and its original member/parent/ref identity from the validated immutable original parent. Every such projection must occur in dispatch members or before-dispatch completion captures, and discovered_sources must equal the original parent's source cardinality. Extra registered pending members remain permitted; the check requires discovered coverage without equating the entire pending union to current discovery. All original selection/skipped/empty-parent/fatal-discovery assertions remain intact.

Root cause 3: immutable-only validation was also used for first selection freeze. A real begin_discovery had registered four frozen units; genuine checked call/error nevertheless allowed the caller to omit both session and units. The existing begun-fatal-discovery test now attempts that coherent omission before any selection object exists and requires Conflict. First freeze checks the available actual DiscoverySession authority and requires its entire captured value and full frozen units. After canonical selection object exists, exact replay skips this mutable lookup and continues to validate immutable saved captures. The test deletes the mutable DiscoverySession index after valid capture, asserts its absence, then requires successful identical frozen selection replay. No selection schema field or new immutable format was added.

Correction evidence is create-only under `specs/evidence/sec-filing-index-ingestion/stage-4/plan5-execution/task-6/fix-1/`; each file retains exact argv/full combined output/actual exit. All suite calls use the same unchanged guarded offline/frozen Task 6 command printed above.

| Correction evidence | Actual result |
| --- | --- |
| 01-red.txt | 20 methods, 76.400s, exit 1; four actual refusal assertions fail (both discovered-union/count cases, transplanted receipt, omitted actual session+units); no setup errors |
| 02-green.txt | 20/20 PASS, 75.471s, exit 0, warning-free after production fixes |
| 03-green-complete.txt | 20/20 PASS, 75.686s, exit 0, warning-free; includes deleted-mutable-session historical replay assertion |
| 04-diff-check.txt | Exact unstaged whitespace command, exit 0 |
| 05-stage-owned.txt | Explicit add of only owned results.py/test_workflow_results.py, exit 0 |
| 06-staged-diff-check.txt | Actual staged whitespace command, exit 0 |
| 07-commit-owned.txt | Explicit correction commit command, exit 0; commit above |

Public signatures, canonical object/index schemas, original red/green evidence, earlier fixture corrections, deadline semantics, historical pointer/terminal/repair-anchor checks and original acceptance assertions are preserved. No weakened assertion, new dependency, parser relaxation, network access, Stage 7 execution, approved plan/spec change, retained-input change, primary-checkout edit or controller-ledger edit occurred. Evidence/report remain unstaged for the controller.

Scoped self-review confirmed immutable full receipt validation (G6/G30), authority-derived coverage/counts and first-freeze versus replay separation, preserving complete exact fields (G19/N4) and adding failure-neighbor checks at the identified authority boundaries (T5/T6). No adjacent tidying was included. The initial snippets shared these bugs; correction changes their authority logic to meet the approved spec rather than copying the defect. No known scoped failing check remains. Independent re-review must resolve spec/quality findings and accept Task 6 before Task 7.
