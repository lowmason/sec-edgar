# Baseline harness fix report

Status: implementation ready; focused verification passed; full baseline pending.

Implementer baseline_fix read required skills, both diagnostic cases, delayed-child trace, helper and named test; prepared minimal diff. Agent apply_patch stalled160.9s without application, so controller applied exactly its reported diff. This tooling handoff is not a behavior/scope change.

Changed only acquisition_race_entry in packages/sec-edgar-ingest/tests/support.py: wrap h.client.fetch to perform request_barrier wait before original fetch, remove wait outside collect. Comment explains download-choice and coordinator-ownership ordering. No timeouts, assertions or production changes.

Confirmed RED: original fresh452-test baseline failed named three-collector race(_queue.Empty/staging barrier errors). Event-controlled actual-store diagnostic before-collect case has all3 child exits1; late child recovers staged bytes without fetch/checkpoint, then waits at binding barrier. Retained unchanged /private/tmp/sec-edgar-race-evidence-20261007T224919 and script; outer diagnostic exit120 due Tee close/flush after complete case summaries, not claimed exit0.

Control: barrier at client.fetch entry yields all3 child exits0, all3 fetch/checkpoint/result events, one binding insert winner and two conflicts. No sender/coordinator/state stubs.

GREEN: controller ran uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_acquisition_processes.py -k test_three_independent_collectors_barrier_request_and_actual_binding_race -v: exit0, 1 test in1.690s, OK. Full guarded452-test baseline currently pending in session98271; must pass before Task1 starts.

Self-review: preserves actual coordinator serialization, staged/binding barriers, request pacing and adoption assertions. Barrier is outside coordinator ownership. No Git mutations by implementer, no primary changes. Design-intent comment meets clean-code C3; synchronization fixes target requested function directly. No additional concerns identified.
