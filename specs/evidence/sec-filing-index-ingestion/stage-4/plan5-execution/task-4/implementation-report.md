# Task 4 implementation report

Status: implementation complete; fresh independent controller review pending. No acceptance is claimed by this report.

Implementer: `/root/task4_implement` (Codex). Checkout: `/Users/lowell/.codex/worktrees/sec-edgar-stage4-plan5/sec-edgar`, branch `codex/sec-edgar-stage4-plan5`. Base: `a42407f04165de30162e693a8940248263ac02d7`. Owned commit: `75682afe7fe88d11dc1b08a1578d602e856d5c67` (`feat: validate workflow completion and durable repair evidence`). The commit contains only completion.py, support_workflow_evidence.py, and test_workflow_completion.py. Evidence and this report remain unstaged for the controller.

## Result and implementation boundary

Current evaluation reads the exact member registry/projection/parent, decoded Binding/Snapshot and Processing observation identity, immutable observation readback, and every quarter returned by the publisher's `_affected_quarters` rules. A formerly affected quarter remains required. Completion requires exact active manifest membership and no retained checked or ordinary legacy unfinished-publication obligations. No per-source flag or boolean mock supplies authority.

Completion/member/parent captures retain original parent and projection objects, actual discovery-session snapshot, required-unit progress/listing receipts, recovered-parent descriptor when applicable, exact raw Binding/Snapshot and ObservationRef, and hash/length-bound generation captures. Historical validators use captured immutable objects and discovery receipts, without live pointers or current Processing indexes. Recovered discovery delegates to Task 2's pure validator, preserving explicitly failed required units and original incomplete discovery.

Repair obligations bind canonical original checked or ordinary public publication command, exact context/input/observations, and full affected-quarter set. Fresh successful publication produces a resolution containing immutable call/result/generation captures and exact PublicationReceipt/Processing artifacts. Current artifact validation and immutable historical resolution validation are separate. A later pointer advance does not reopen a previously validated resolution. Original unfinished Attempt and command bytes remain unchanged, including after an expired retry requires a fresh attempt.

No publisher, parser, dependency, pin, registry/config/workset baseline, acquisition production code, or controller ledger was edited. No live SEC/Azure/network/provider/Stage 7 action was used; all 22 Stage 7 integrated checks remain reserved/not_run. No new dependencies. No full-suite repeat: the controller reserves Task 11 final verification.

## TDD and retained results

All proof files live in `specs/evidence/sec-filing-index-ingestion/stage-4/plan5-execution/task-4/`. Each run has full combined output and a JSON file retaining exact argv and exit. The working directory for every command is the isolated checkout above.

The exact scoped red/green command was:

```text
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_completion.py -v
```

- `red.txt`, `red-command.json`: exit 1, absent completion module / missing Task 4 APIs. No cache or fixture substitution; production module did not exist before this run.
- `green-1.txt`, `green-1-command.json`: exit 1, 8 supplied methods; 5 PASS and 3 helper errors before assertions. These are not reported as successful behavior tests.
- `red-authority.txt`, `red-authority-command.json`: exit 1, 12 methods; 3 assertion failures exposing corrupt session/registry acceptance, plus the same 3 helper errors. Additional binding-winner and missing immutable file cases passed against the core.
- `fixture-clock-diagnostic.txt`, `fixture-clock-diagnostic-command.json`: exit 0, 1 guarded diagnostic asserting the real revised discovery parent is incomplete with no members. `fixture-clock-mismatch.json` retains its failed parent, error details, harness clocks, wall clock and original sentinel journal. `diagnostic.py` retains the diagnostic source.
- `green-2.txt`, `green-2-command.json`: exit 0, 12/12 PASS, 42.385 seconds. Original behavior assertions unchanged.
- `red-return-contract.txt`, `red-return-contract-command.json`: exit 1, 13 methods; 12 PASS, exact return-contract assertion failed (`None != SourceWorkset`). This was observed before adding the return.
- `green-final.txt`, `green-final-command.json`: exit 0, 13/13 PASS, 44.646 seconds; same 13 tests.
- `green-final-whitespace.txt`, `green-final-whitespace-command.json`: exit 0, 13/13 PASS, 44.957 seconds, after EOF-only fixture correction. No further scoped behavior run is needed for whitespace alone; this run was already started before that controller guidance.

Required authoritative publication regression commands were retained independently:

```text
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_etl_cli.py -v
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_etl_publication.py -v
```

`test_etl_cli.txt` and its command JSON: exit 0, 38/38 PASS, 6.588 seconds. `test_etl_publication.txt` and its command JSON: exit 0, 24/24 PASS, 6.615 seconds. These authoritative modules were not edited.

`commit-and-whitespace.json` retains the first exact `git -c core.whitespace=cr-at-eol diff --check`, explicit owned `git add`, and extra staged whitespace check. The staged check exited 2 for the supplied fixture's extra blank line at EOF; the commit was not executed in that attempt. This was a whitespace failure, not a test failure. `commit-and-whitespace-final.json` retains corrected exact and staged whitespace checks (both exit 0), explicit owned add (exit 0), and successful owned commit (exit 0).

## Reproduced deviations from supplied snippets

1. The supplied `EvidenceFixture.revised_member()` mixes the checked CLI's wall-clock lease journal with DiscoveryHarness's October 6 fixed clock. The retained diagnostic has harness before `2026-10-06T00:00:02.000004+00:00`, wall-clock journal `not_before=2026-10-08T19:08:36.550681+00:00`, and harness exhausted to `2026-10-06T01:00:00+00:00`. The root retained `sender_unverified` with `queue wait exhausted turn deadline`; required children retained `ancestor_failed`. The helper now uses the existing checked Dispatcher, same fixture pack, a distinct original discovery ID/step, and `--refresh`. It preserves the source/rows/version assertions and original/new parent distinction. No production clock/acquisition change.
2. The supplied historical member/completion core accepted malformed discovery-session registration and an extra member registry field. Added real captured-proof corruption tests first; their three expected assertions failed. `_validate_discovery` now invokes exact `validate_discovery_session` for both normal and recovered evidence, and member/completion historical validators require exact registry fields. Recovered receipts still use Task 2 pure reconstruction.
3. The supplied `validate_member_provenance` omitted its specified SourceWorkset return. Added the exact projection-equality regression, observed the failed return assertion, and added `return projection`. Parent validator already returns its exact parent.
4. The new module's public return annotations were made explicit, imports consolidated, unused supplied imports/dead singleton temporaries removed, and direct date import used. These are confined to newly authored Task 4 code. No adjacent tidying or additional module split.
5. The supplied fixture's EOF blank line was removed after the staged whitespace proof flagged it. Controller instructed commit before independent review; this follows that execution-order override rather than the brief's nominal review-before-commit sequence. Acceptance still awaits independent review.

## Exact public interfaces

`signatures.json` retains final source-derived signatures and line numbers:

```text
evaluate_member(value, parser_version, schema_version, store, objects) -> CompletionEvaluation
capture_member_provenance(value, store, objects) -> Mapping
validate_member_provenance(evidence, objects) -> SourceWorkset
capture_parent_provenance(parent_ref, store, objects) -> Mapping
validate_parent_provenance(evidence, objects) -> SourceWorkset
validate_discovery_session(session) -> RunContext
validate_capture(capture, objects) -> None
outstanding_repairs(value, store, objects) -> tuple[Mapping, ...]
resolve_repair(obligation, successful_publish_call, store, objects) -> Mapping
validate_resolution_capture(resolution, objects) -> None
validate_resolution(resolution, store, objects)
```

Additional supplied reader helpers `read_legacy_publish` and `read_repair_obligation` are retained. No parameter list, optional authority flag, or existing Tasks 1-3 API was changed.

## Self-review and clean-code application

- F1/F3: public parameter lists follow the approved interfaces; no flags bypass identity or evidence validation. Objects/state dependencies are explicit. Current store-dependent validation and historical immutable validation are separate entrypoints.
- G30/G34: functions remain grouped around discovery provenance, object descriptors, original publish-call authority, repair artifacts/resolutions, and current evaluation; no line-count-driven fragmentation.
- G19/N1: exact context, affected quarters, descriptor and publication artifact values use the task/publisher vocabulary rather than opaque success markers.
- G24/F401/F811/F841: new module imports consolidated, supplied unused imports and dead singleton temporaries removed; no dependency or neighboring module touched.
- C3/C4: preserved explanations of canonical original-command authority and why unfinished/corrupt inventory cannot supply repair authority; no conversational history added to production code.
- T1/T5/T6: 13 real-store methods cover old/new quarter membership, corrupted Processing decoder identity, immutable captures after advance, checked and ordinary legacy unfinished repair, expiry/new-attempt boundaries, copied-obligation tampering, repaired discovery session provenance, malformed captured registry/session, divergent binding winner, missing original parent/projection/raw/observation/generation/receipt files, and exact public return value.
- Commit path audit: only three owned code/test paths were committed. Evidence/report remain for controller staging. Existing accepted authority corrections and pins are unchanged.

## Independent review handoff / concerns

No known unresolved implementation failure in the required scoped tests. Fresh independent reviewer identity, scoped base..head diff and findings are pending controller dispatch after this report/commit; no reviewer identity or acceptance is fabricated here. Review should independently check full historical original-session/listing/parent/binding/version identity, formerly affected quarter coverage, legacy and checked repair obligation authority, historical resolution after pointer advance, exact returns/signatures, and preservation of original failed Attempt and pointer rows. Controller reserves integrated final verification for Task 11.

## Fix round 1: independent authority review correction

Independent reviewer: `task4_review`, initial review retained at `specs/evidence/sec-filing-index-ingestion/stage-4/plan5-execution/task-4/review-initial.md`, range `a42407f0..75682afe`. Initial decision was Needs fixes: three Important authority findings. This section supersedes the earlier no-known-concern statement; it records fixes and verified tests, not independent acceptance. Re-review remains for the controller.

Correction commit: `c191ec685a775f69e1307d2707a3a01aba0d3b21`, `fix: bind workflow repair evidence to original publication calls`. It contains only the owned completion.py and test_workflow_completion.py. Original fixture clock/provenance-return corrections remain; support_workflow_evidence.py was not changed in this round. Approved docs/plans/snapshots, controller ledger, publisher/dependencies, Tasks 1–3, and all live/Stage 7 boundaries remain unchanged.

Applied receiving-code-review and systematic-debugging alongside test-driven-development, clean-code/clean-coder and verification-before-completion. The reviewer probes were hypotheses; independent guarded real-store reds below confirmed the authority-loss paths before the respective production corrections.

### Root causes and corrected authority

1. `_obligations` previously validated whatever resolution descriptor appeared under the original call key. The resolution was internally valid but its embedded original obligation was not compared with the obligation being discharged. The two-call reproduction repaired only the first call, misindexed its valid resolution under the second, and observed false completion. The evaluator now reads the resolution payload and requires its exact embedded original obligation descriptor to equal the current canonical descriptor before historical resolution validation/discharge.
2. `_publish_calls` caught corrupt/missing immutable command, Attempt context, and transformed input evidence and continued. The scan therefore dropped uncertainty, allowing current pointer membership to claim completion. Both checked and ordinary begun corruption now raise an explicit Conflict, retained by evaluation as a `state_conflict` gap. The valid persisted checked call before begin remains nonblocking. A neighboring independent red proved that a missing Attempt with an existing immutable command was wrongly treated as pre-begin; `_call_context` now checks command/result artifacts and reports missing begun Attempt authority. Only no-Attempt/no-begun-artifact calls qualify for that pre-begin exclusion.
3. `_read_document` proved hash/canonical bytes and observation-quarter inclusion, but did not establish the canonical original obligation. A copied payload could retain the observed Q3 quarter and remove formerly affected Q4. The corrected real fixture publishes an initial nonempty Q3/Q4 observation, then a new nonempty Q3-only observation; the original unfinished obligation captures both quarters. Before the fix, a hash-valid copy dropping only Q4 was accepted. The original obligation now has an immutable per-original-call anchor; every obligation read/current resolution/historical resolution must match that exact anchored descriptor. Caller-supplied copied payloads cannot create or change the anchor.

The new internal immutable authority object is:

```text
worksets/sec/workflow-repair-authority/call-sha256=<canonical-original-call-sha256>/obligation.json
```

Its canonical exact schema is `{format_version, call_sha256, descriptor}`, with `format_version=sec-workflow-repair-authority-v1`. `call_sha256` is the SHA-256 of canonical original checked/legacy call bytes; `descriptor` is the existing exact `{ref, sha256, bytes, format_version}` obligation descriptor. Original obligation and resolution payload/descriptor formats are unchanged. `fix-1/anchor-schema.json` retains this contract for downstream Tasks 5/6/proof readers.

Creation follows the existing checked-call working pattern: validate original call/context and transformed input, capture full publisher-affected set plus retained publisher outcomes, write immutable obligation object, write/read back the exact immutable per-call anchor, then insert the recoverable WorkflowRepairObligation index. A missing index reads the existing anchor first and restores the original descriptor without consulting later pointers for its quarter set. A divergent index/absent or malformed original anchor refuses with a gap; it is not overwritten. A pre-fix unanchored index is not used to synthesize authority from a caller/mutable index. Historical readers reopen the original anchor and immutable obligation/call/generation bytes without current indexes or pointers.

Malformed recoverable obligation/resolution descriptors now fail the shared Mapping shape check explicitly rather than producing an unhandled TypeError. A focused red independently reproduced the None-descriptor failure. No bypass flag or second publication authority was introduced. When corrupted inventory cannot establish source provenance, evaluation conservatively retains a completion-blocking gap rather than silently omitting that record.

### Actual fix-round TDD / verification

Evidence is create-only under `specs/evidence/sec-filing-index-ingestion/stage-4/plan5-execution/task-4/fix-1/`; all output files contain full combined output, with matching JSON records for exact argv/exits. Working directory remains the isolated checkout above. The full covering command remained exactly:

```text
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_completion.py -v
```

- `red.txt` / `red-command.json`: exit 1, 19 methods, seven failures. Six failures independently establish foreign-resolution false completion, checked missing command/transformed bytes, corrupt checked Attempt context, ordinary missing command false completion, and later-pointer recomputation after losing the obligation index. One failure was my new two-quarter ZIP fixture setup (stored compression rejected by the real parser), not the formerly-quarter authority assertion; it receives no authority-red credit.
- Corrected that test fixture to required ZIP_DEFLATED, without changing production parser/envelope or behavioral assertions. `red-formerly.txt` / command JSON use the same guarded filename with `-k copied_obligation_cannot_drop_only_formerly`: exit 1, one method, expected `assertRaises` failure because the formerly-Q4-only removal was accepted. Both original quarters and the remaining nonempty observed Q3 are asserted first.
- `green-binding-inventory.txt` / command JSON: same guarded filename with `-k foreign_valid_resolution -k corrupt_begun -k valid_checked_call_before_begin`; exit 0, four methods PASS, 11.672 seconds. This verified the first two minimal corrections before adding anchor authority.
- `green.txt` / command JSON: full command, exit 1, 19 methods, 18 PASS and one recovery assertion failure caused by FrozenMapping-versus-plain-dict equality. The public interface permits Mapping representations. Corrected the test to compare canonical bytes of every descriptor field and the full tuple; no quarter/field/identity check was removed. Final green confirms exact descriptor byte equality and repaired index descriptor equality.
- `red-missing-attempt.txt` / command JSON: guarded filename with `-k corrupt_begun_checked`; exit 1, one method, expected `complete=True` failure for a missing Attempt with retained immutable begun command bytes. Fixed only that begin distinction; valid pre-begin coverage remains.
- `red-malformed-index.txt` / command JSON: guarded filename with `-k original_anchor_precedes`; exit 1, one method ERROR showing None descriptor escaped as TypeError. Fixed the shared descriptor shape guard and non-null authority descriptor requirement before final run.
- `green-final.txt` / command JSON: exact full command, exit 0, **20/20 PASS**, **70.520 seconds**. No further production edits followed this covering proof. Original expiration/fresh repair, original Attempt/command and pointer row equality, and historical validity after pointer advance are retained and passing.
- Fresh required unchanged `test_etl_cli.py` command: exit 0, **38/38 PASS**, 5.868 seconds; full `test_etl_cli.txt` and command JSON retained. Fresh required unchanged `test_etl_publication.py` command: exit 0, **24/24 PASS**, 5.906 seconds; full output and command JSON retained. These modules were not edited.
- Automatic permission review timed out before the final edit/test shell command started. Tool explicitly permitted one retry; the retry succeeded and produced the actual final proof above. The timeout supplies no shell/test exit or evidence of unsafe work and is not reported as a test result.
- `commit-and-whitespace.json`: exact `git -c core.whitespace=cr-at-eol diff --check`, explicit owned add, extra staged check, and owned commit all exit 0. Only the two owned correction files were staged.
- `signatures.json`: AST-derived public signatures compared exactly with Task 4's original signature evidence; all unchanged. Parameter lists, return annotations, CompletionEvaluation shape, original descriptor formats, and pure/current validation split remain unchanged. Only source line numbers moved.

New/expanded real-store cases cover foreign valid resolution identity, checked and ordinary begun corruption, immutable command with absent Attempt index, valid no-begin call, formerly affected-only tampering with nonempty source inputs, anchor-first index recovery after pointer advance (publisher quarter recomputation patched to raise if attempted), actual object-before-index write ordering, missing anchor, divergent/malformed index refusal and unchanged anchor/index bytes. These supplement the retained 13 methods rather than replacing their checks.

### Fix-round self-review and handoff

- T1/T5/T6: reproduced each reviewed false-completion path before fixes and covered adjacent missing-begun-Attempt/malformed descriptor cases; no boolean mock supplies authority.
- N1/G19/G30/G34: per-original-call SHA and immutable descriptor authority are explicit narrow helpers; current resolution linkage remains at discharge, historical document authority is shared; no adjacent code cleanup or new module split.
- C2/C3/C4: removed the obsolete comments deferring standalone completion uncertainty to Task 7; retained why original immutable capture precedes recoverable indexing.
- F1/F3: no public parameters/authority flags changed. New anchor is immutable provenance, not a second publication pointer or success flag.
- Readback/retention: original publication remains the existing pointer boundary; raw/generation/call/obligation/resolution/anchor retention remains indefinite in development. Missing indexes can recover from anchors; malformed evidence cannot redefine them.

Implementation tests and whitespace are verified; independent re-review remains pending controller dispatch over `75682afe..c191ec68` (and whole Task 4 scope as needed). No known unresolved authority test failure remains. No acceptance is claimed until that re-review passes.
