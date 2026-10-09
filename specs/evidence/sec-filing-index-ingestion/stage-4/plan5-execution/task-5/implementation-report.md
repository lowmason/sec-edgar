# Task 5 implementation report

Status: implemented and scoped checks passed; independent Task 5 review remains pending. Task 6 is gated on that review.

Implementer: `/root/task5_implement` (Codex, inherited available model; provider does not expose requested Sonnet/Opus aliases). Checkout: `/Users/lowell/.codex/worktrees/sec-edgar-stage4-plan5/sec-edgar`; branch `codex/sec-edgar-stage4-plan5`; accepted predecessor base `e0690e2a9b2eadd7cea7c35c120352edd60fc8df`. Owned implementation commit: `4bd46760cc9d929e1e3ecbf0e2198c7ff2cd7442`, `feat: process exact workflow source units through checked commands`. Only workflows/processing.py, workflows/members.py, and tests/test_workflow_processing.py were committed. Evidence and this report are unstaged for the controller.

## Interfaces and authority

- `ProcessedMember(result: MemberResult, evidence: Mapping[str, object])` is a strict frozen Record.
- `process_member(value, context, dispatcher, store, objects, observer=None) -> ProcessedMember` validates exact registered projection; reopens deterministic existing receipt before dispatch; resolves outstanding publication repairs with original transformed input/settings and fresh workflow deadline; collects with origin settings; transforms/publishes with current settings; retains every exact child/gap/quarter; propagates resumable publication failures.
- `validate_member_evidence(result, evidence, objects) -> None` validates strict evidence fields/version, immutable original parent/singleton projection, deterministic checked child namespace/step/ref/context/input/output codecs, exact progress/ref/outcome/gap/quarter flags, terminal correlation, immutable complete captures and exact resolution prefix. It never treats MemberResult decoding alone as proof.
- `WorkflowMembers.record(result, context, evidence) -> Mapping` validates registry/member/evidence and exact reproducible workflow context pin, creates canonical member receipt before index, and rejects conflicting immutable index/body.
- `WorkflowMembers.completed(value, parser_version, schema_version) -> Mapping | None` validates exact receipt descriptors/body/schema/path/context/evidence, requested versions and immutable binding; outstanding repairs prevent completion. Successful historical captures reopen immutable manifests rather than current pointer equality.
- Internal `WorkflowMembers.replay(value, context)` reads the exact deterministic receipt path, verifies frozen context and member, and repairs its missing index through record without dispatching a child. No unknown-object enumeration.

Receipt path: `runs/sec/<run>/<workflow-command>/<attempt>/members/<member-id>/result.json`. Body has exactly format_version/context/result/evidence and version `sec-workflow-member-receipt-v1`. Index kind `WorkflowMemberResult`; key is SHA256 of canonical `[run, command, attempt, member_id, parser_version, schema_version]`; descriptor has exact ref/sha256/bytes/member_id/parser_version/schema_version fields.

Terminal authority addition: when a real checked non-resumable child has no immutable result, processing first reopens its actual persisted unfinished Attempt through Task 3 `unfinished_child`. It writes a create-once canonical object at the original child's `result_ref` directory `/terminal.json`, with exactly `{context: actual_attempt_context, terminal_error: exact_ChildUnfinished_details}`. Details preserve call/outcome/exit/stdout/stderr/gaps/repair_pending/resumable. This is Task 5-owned supporting evidence, not a fabricated child result or completion. Historical validation reopens this object, checks actual/template context and original command bytes, exact call/outcome/gaps/exit and step/input correlation. Record also checks its context/gaps against the persisted unfinished Attempt. Publication-resumable children propagate and never get a member receipt. Downstream Task 6 can replay a failed immutable member receipt without treating its terminal evidence as COMPLETE.

## Red/green and checks

All proof files are create-only under `specs/evidence/sec-filing-index-ingestion/stage-4/plan5-execution/task-5/`; every named output has a matching `-command.json` with exact argv and actual child exit. Working directory is the isolated checkout above. Guarded runners used cached offline/frozen dependencies, no fetches. The required exact scoped command was retained first as missing-module red, then rerun for coverage greens:

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_processing.py -v
```

Final covering result: `green-complete`, 14/14 PASS, 63.065 seconds, exit 0. Required original regression files: test_collection.py 35/35 PASS and test_etl_cli.py 38/38 PASS, each with the same guarded runner and exact filename, exit 0. No broad suite or reserved integrated check ran. Both unstaged and staged whitespace checks passed. Their exact argv/output/exit are retained.

| Evidence | Exit | Run size/time |
|---|---:|---|
| `red` | 1 | 1 tests, 0.000s |
| `example-defects` | 1 | 4 tests, 14.527s |
| `red-authority` | 1 | 8 tests, 29.289s |
| `green-authority` | 1 | 8 tests, 26.857s |
| `green-expanded-1` | 1 | 13 tests, 58.283s |
| `green-expanded-2` | 0 | 13 tests, 60.513s |
| `green-final` | 1 | 13 tests, 61.469s |
| `red-context-pin` | 1 | 1 tests, 3.649s |
| `green-final-corrected` | 1 | 14 tests, 63.512s |
| `green-terminal-pin-focused` | 1 | 2 tests, 6.357s |
| `green-complete` | 0 | 14 tests, 63.065s |
| `regression-collection` | 0 | 35 tests, 11.497s |
| `regression-etl-cli` | 0 | 38 tests, 6.882s |
| `diff-check` | 0 | exact command output retained |
| `staged-diff-check` | 0 | exact command output retained |
| `stage-owned` | 0 | exact command output retained |
| `commit-owned` | 0 | exact command output retained |

The tests cover retained transport-prefix success without source quarantine; genuine conflicting and malformed source refusals with physical line/reason/raw SHA, no accepted Processing/observations/pointer; strict child/capture/version/ref/quarter/flag/terminal tampering before record; content-first receipts, interrupted object/index repair, immutable index conflicts; origin v1 acquisition with current v2 transform/publication and no borrowed versions/new member; historical successful v1 receipt after v2 pointer advance; fatal first collection with no ETL and all gaps; partial Q3 invalid/Q4 published and gate-only awaiting approval; expired original publication repaired with fresh context/settings while original Attempt/command bytes, absent old result and pointer versions remain unchanged and PublicationReceipt membership is repaired; actual unfinished collect-execution error and exact failed receipt replay.

Genuine behavior reds: absent processing module; required conflicting source outcome (`invalid_source` versus member `quarantined`); foreign workflow namespace accepted by record; object-only receipt replay redispatching a child; mismatched receipt workflow config hash accepted despite unchanged effective settings. The authority red had 6 PASS and 2 assertion failures before those fixes. The pin red was 1 focused assertion failure before pin validation.

Other retained failures are not claimed as behavior reds: supplied frozen capture/list equality incompatibility; implementation-local projection name shadowing; synthetic fatal response missing strict fixture body fields; incorrect assumption that HTTP403 lacks a child result; temporary test-edit NameError; pin validation raising ValueError before conversion to registry Conflict; focused terminal test accidentally passing original rather than mutated evidence. Each was reproduced, corrected without weakening its intended assertions, and covered by final green. The initial shell helper `python` was unavailable; local `python3` drove evidence scripts, while all actual tests used the pinned uv Python runner.

## Authorized deviations and corrections

1. Supplied example compares frozen captured member arrays directly with decoded JSON list values. Validator normalizes evidence through shipped `to_mapping_value`, preserving canonical field/value identity. Returned completion captures use the same frozen strict-record shape as processed evidence.
2. Shipped ETL intentionally registers transform refusal as `invalid_source` exit7 while supplied Task 5 acceptance explicitly requires terminal failed member `quarantined`; its validator example otherwise demands literal final-child outcome. Only an exact terminal transform proving `quarantined` count and no accepted transformed/unchanged observation derives member `quarantined`; validator independently derives that rule. Original child outcome/gaps/result bytes remain unchanged. Actual refusal test confirms `invalid_source`, quarantined=1, transformed=0, line4 conflicting duplicate reason and zero accepted state. Publication invalid_source remains invalid_source.
3. The brief's example has no exact receipt replay operation and insufficient workflow-context correlation. Added deterministic replay, full receipt schema/descriptor correlation and reproducible context pin, with genuine failing tests before corrections.
4. Added immutable terminal Attempt snapshot described above so historical objects-only evidence validation can bind a missing-result terminal error to exact persisted state. It does not modify Task 3 or any original Attempt/command/result bytes.

## Self-review and clean-code pass

Reviewed every changed path against Task 5 brief. Existing Task 2 register prevalidation before mutation and project_member recursion guard are preserved; Task 3 snapshot canonical validation and Task 4 repair-authority anchors are untouched. Receipt/codecs refuse tampering; historical manifests remain authority; source-refusal normalization is narrowly derived; no report/inventory orchestration was added.

Applied in owned code: descriptive `source_projection` avoids imported projection shadowing (N1/N4); `_member_outcome` names source-level refusal derivation (G28); receipt object/path/descriptor/context reading stays cohesive within registry and child authority stays within processing (G6/G30); tests exercise actual CLI and immutable object/index interruption boundaries (T1/T5/T6). Import consolidation is limited to imports needed by new receipt methods; predecessor method bodies are unchanged. No adjacent cleanup, parser/provider/version/dependency/pin changes, retained-input rewrite or primary-checkout edits.

All 22 Stage 7 integrated checks remain reserved/not_run. No live SEC/Azure/auth/compute/deployment/image/network/trigger action occurred. Remaining checkpoint: independent reviewer must inspect this scoped commit and terminal support authority, then accept or request changes before Task 6. No acceptance is asserted here.
