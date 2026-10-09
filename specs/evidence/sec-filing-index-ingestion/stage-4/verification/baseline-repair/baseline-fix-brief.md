# Baseline race harness repair

Owner instructed Resolve first after the fresh Stage4 baseline ran452 tests and failed only the three-collector race. Work in /Users/lowell/.codex/worktrees/sec-edgar-stage-4/sec-edgar on codex/sec-edgar-stage-4; do not touch primary.

## Confirmed cause and red evidence

Read /private/tmp/sec-edgar-race-evidence-20261007T224919/before-collect/child-2.jsonl and both case summary.json files. Diagnostic script: /private/tmp/sec-edgar-race-diagnostic-20261007T224919.py. It deliberately holds third worker's recover_promoted until another receipt is checkpointed. With the existing pre-collect start barrier, third worker correctly recovers the receipt, bypasses fetch/receipt checkpoint and waits at binding barrier while other two wait at staged barrier; all exit1. With start barrier at client.fetch entry, all3 exit0, exactly one insert succeeds and two conflict. Production recovery is correct.

Diagnostic process ended120 due its Tee flushing a closed output at interpreter shutdown, after both complete summaries were written. Preserve that diagnostic failure unchanged; it does not change captured ordering evidence. Do not claim diagnostic command exit0.

## Ownership and change

Own ONLY packages/sec-edgar-ingest/tests/support.py acquisition_race_entry and, only if useful to assert existing guarantees, packages/sec-edgar-ingest/tests/test_acquisition_processes.py named test. You are not alone in this codebase; preserve other edits and adjust around them. No Stage4 module or production-file edits. No timeout increases, no sleep, no dropped race/pacing/raw/adoption assertions.

Move request barrier synchronization into a wrapper around h.client.fetch before the original fetch is called. That is after recovery chose download and before coordinator acquires ownership. Keep existing request_barrier_ready/request_barrier_released traces (or clear matching names), staged and binding barriers, actual client/coordinator/state/store implementation and all assertions. Explain why synchronization belongs here. The original outside-collect barrier must be removed. Do not synchronize inside sender while it owns the coordinator.

Read test-driven-development and clean-code skills. Red evidence is actual unmodified baseline failure plus deterministic original-path failure, not dependency/sandbox errors. Implement minimal fix, self-review and report. No further agents.

Controller will run focused and full guarded tests and commit after review; do not start escalation requests or mutate Git. You may use apply_patch for files despite shell sandbox restrictions. Write full implementation report at .sdd/4-sec-filing-index-ingestion-stage-4-spec/baseline-fix-report.md with files changed, confirmed cause, red evidence, choices, outstanding verification. Return short status and report path.

## Binding limits

Offline evidence/fixtures only. SEC/Azure/auth/network access closed, all22 Stage7 checks reserved/not_run. Do not change pins, guards, parser, raw/registry retained bytes or SEC-0141/0142/0143 quarantine acceptance. Primary required four legacy files remain absent. No git add -A, stash/reset/restore, primary builds or primary mutations.
