# Task 10 implementation report

Implementation commit: `e69a9d1244be56826ce6496aeec3f92c81bf8e45` (`test: prove workflow CLI and process recovery offline`), based on accepted Tasks 1–9 commit `8689156b26364063ae14ef44a0f89a6bfeb37951` on `codex/sec-edgar-stage4-plan5`. Implementation verification passed; independent task review and owner fixture/process acceptance remain pending. This report does not accept the task or enable Task 11.

Only the three owned test/proof files, four expressly listed appended support helpers, and thirteen fixed synthetic fixture files were committed. Newly created Task 10 evidence and this report remain unstaged. No production code, predecessor code, plan/specification, primary/retained input, binding/config/workset, controller ledger, dependency/pin, parser policy, or Stage 7 check was changed. No standalone proof main/parser, installed wrapper, or complete installed inventory verifier was implemented; those remain Task 11.

The test-only public interfaces are `sequence(output: Path) -> Mapping[str, object]`, `harness_files() -> tuple[Path, ...]`, and `native(output: Path) -> Mapping[str, object]`. The inventory contains the six specified support/config files and all thirteen fixed proof fixture files. The proof imports production CLI, child/result readers, captured-quarter readers, and stores; observers terminate/fault at actual durable boundaries without supplying successful results.

The fixed generator ran once at a create-only destination with the exact approved offline/frozen command, retained in `fixture-generation.json`. Inspection is retained in `fixture-review.json`: eleven response URLs, sixteen explicit responses per URL, all body hashes and content lengths checked, deterministic ZIP metadata, one parser-valid row per source, and no extra preamble or empty source. `expected.json` specifies rows separately from runtime reports. Its SHA-256 is `3dbca2c261f73eec350e57bdc5d009ee0a8af253ce45068d75c53bd032e64153`; manifest SHA-256 is `1911b466b85bdcb269ef77384548b8511ac9425d8e16688b58c32f90de948fdb`. The sequence checks local parser `fixture-index-parser-v1`, schema `sec-index-v1`, 90-second exchange, 67,108,864 received-byte and 536,870,912 expanded-byte settings before commands, retaining `checked-config.json`.

Tests and listed fixture helpers were written first. The exact acceptance command below ran before corrections and exited 1 (`red-acceptance.json`): ten methods passed and F2 errored because the brief supplied the dispatch descriptor's earlier context to strict request-history validation. This is a reproduced proof setup error, not a missing production behavior. Production `_context_matches` deliberately permits the actual child to begin later within the parent deadline. The owned test now independently obtains `read_child(original_call, store, objects).context`; its exact two-attempt history, prefix bytes, receipt error, completion, zero quarantine/failure, and reader assertions are unchanged. The parent explicitly confirmed this scope-preserving correction. No runtime fix was indicated.

The process first run exited 1 (`red-process.json`): sequence setup lacked the not-yet-generated fixed `expected.json`; all twelve actual process-death/reopen cases passed. That missing fixture is a setup red, not a semantic production failure. There was no unavailable dependency cache and no manufactured behavior red. After the single fixed-fixture generation, the exact unchanged process command passed both methods, covering the sequence and twelve boundaries. No assertion was weakened and no successful authority was mocked.

Exact scoped commands, each with full argv/stdout/stderr/exit retained in Task 10 JSON evidence:

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_acceptance.py -v
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_process.py -v
```

`green-acceptance.json`: exit 0, eleven tests PASS (143.656 seconds). Final `green-acceptance-retained.json`: same argv, exit 0, eleven tests PASS (140.477 seconds), with `SEC_EDGAR_TASK10_ACCEPTANCE_EVIDENCE` selecting a fresh Task 10 evidence directory. This optional observer retains all eleven original fixture/store trees, command records, and actual production reader captures before temporary cleanup; it does not construct report/completion authority. Original temporary roots and retained roots are recorded in each `checked-evidence.json`. `green-process.json`: exit 0, two tests PASS (86.669 seconds), including twelve real worker deaths and fresh recovery commands. The final retained acceptance rerun verified the observational retention addition; no further discretionary tests or repeats followed.

The retained native proof invoked `native(Path(output))` directly using the create-only evidence `native-driver.py`, guarded before test imports. Its full argv/exit/stdout/stderr are in `native-proof-command.json`; exit is 0. It is an evidence invocation driver, not a new harness script main or installed mode. `native-proof/sequence` contains checked reports, every command, fixture copy, state/raw/generation/report objects and reader captures for inclusive Q3/Q4 baseline, daily overlap, fresh unchanged repeat, exact completed replay, and actual primitive-only legacy backlog. Each requested quarter has exactly one independently expected logical row; daily overlap creates no duplicate logical filing. Completed exact replay preserves report bytes and fixture cursor state.

`native-proof/process-recovery.json` records twelve exit-91 workers and twelve exit-0 recoveries. Every worker command argv, exit, stdout/stderr file, fsynced PID/boundary marker, reopened report, rows, reader capture and pointer-before/after snapshot is retained with its state/fixture tree. Parent handles close before spawn and reopen after death; each resumed public command revalidates production authority. The actual boundaries are:

- `workflow.after_attempt_begin`
- `workflow_child.after_call`
- `collection.after_binding`
- `workflow_child.after_result`
- `workflow.after_selection`
- `publication.after_pointer`
- `publication.after_repair`
- `etl_result.after_object`
- `workflow.after_member_processing`
- `workflow.after_member_receipt`
- `workflow.after_report_object`
- `workflow.after_attempt_finish`

The post-pointer process proof requires one committed pointer and a begun publish with no result; recovery preserves that pointer. Historical report bytes at report-object/attempt-finish boundaries remain identical. Actual `workflow-repair-authority/call-sha256=<original-call-sha>/obligation.json` objects survive in the two native publication interruption trees and F3 retained acceptance tree (three anchors total), indexed by `verification-summary.json`. No terminal-error path was exercised by these successful recovery cases; Task 5's retained missing-result terminal history was not replaced, simplified or claimed COMPLETE.

F1–F5 and R1/R2 acceptance covers moved-quarter backlog after independent Q4 publication, retained retry prefixes without terminal source quarantine, ordinary post-CAS failure with no parent report and fresh checked repair, parent command namespace and exact replay, all-conflicting baseline quarantine/gaps/no pointer, empty/mixed independent-quarter progress, older gated withdrawal, older unacquired backlog, outage spanning Q4/Q1/Q2, failed-directory boundary hold, and Q4/Q1 transition. F6 native proof and explicit harness inventory are exercised here; complete installed inventory and live transitive mismatch remain Task 11.

Eight Stage 3 regression files were run separately with the same exact guarded runner, retaining each full output and exit under `regression-<filename>.json`: parser 7, transform 21, publication/reader 24, CLI 38, catalog 31, contracts 11, storage 12, processes 6. All 150 tests PASS, exit 0. The full suite remains reserved for Task 11, including its required exact SEC-0141/0142/0143 21/24/6 whole-source refusals. Task 10 did not relax parser policies or rewrite their retained specimens/raw hashes. These are offline local fixture and mocked SDK tests; wire-like diagnostic strings in regression output do not represent live requests.

`git -c core.whitespace=cr-at-eol diff --check` exited 0, retained in `diff-check.json`; the staged counterpart also exited 0 before commit. The scoped committed diff is retained as `task-10.diff`, SHA-256 `4de7fb0efe095123dfcd19f8e371a5921e6442135bc314f2222da735b393b3d0`. It touches exactly seventeen owned files. The evidence command summary confirms eleven retained acceptance cases, twelve native boundaries, all regression exits, and repair paths.

Self-review identity: the Task 10 implementing Codex agent (inherited available provider; Sonnet/Opus routing unavailable). Reviewed committed scope against the sole task brief, production authority imports, bounded child-start contract, observer-only process faults, create-only output/fixture contracts, file inventory, full command outputs, and preserved independent progress. Applied in-scope clean-code checks: removed unused new proof imports and redundant new support import (F401), removed supplied placement-only comments (C3), used named guard mappings and explicit recorded command/reader fields (G19/N1), and added exact consumed interface annotations. No adjacent cleanup was made. Remaining approval gates are independent task review plus owner fixture/process evidence review, dispatched by the root agent after this committed handoff; no implementer self-review is presented as independent review.

Evidence root: `specs/evidence/sec-filing-index-ingestion/stage-4/plan5-execution/task-10/`. All live-access authorization remains closed. All twenty-two Stage 7 integrated checks remain `reserved/not_run`. No SEC/Azure/authentication/compute/provisioning/deployment/image build/network fetch/trigger enablement occurred.
