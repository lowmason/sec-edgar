# Task 8 implementation report

Status: implemented and verified; independent task review remains pending. This report does not accept Task 8 or authorize Task 9.

Branch: `codex/sec-edgar-stage4-plan5`.
Predecessor base: `376d051070e8c23a7b26a280dbdc82e1408481c4` (accepted Tasks 1–7).
Owned implementation commit: `da1044da3f5dc0b3937005556b7cc3b25ab47185`.
Commit subject: `feat: assemble durable backfill and daily workflow coverage`.

Only `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/runner.py` and `packages/sec-edgar-ingest/tests/test_workflow_runner.py` were committed. This report and new Task 8 evidence remain unstaged for controller/reviewer handling. No predecessor code, approved spec/plan, snapshot, input, binding/config registry, dependency pin/lock, controller ledger, or primary checkout was edited.

## Implemented public interfaces

- `reuse_exact_binding(value: Mapping, store, objects) -> tuple[Error, ...]`: verify retained singleton pins, retain isolated corrupt-reuse gaps, transfer only one verified fingerprint, and refuse divergent winners.
- `select_work(context: RunContext, settings: Settings, intent: Mapping, dispatcher: Dispatcher, store, objects) -> Mapping`: bootstrap legacy evidence, retain inventory/receipt uncertainty, revisit older unresolved members, perform deterministic checked discovery, project every original parent member, capture exact completed units, and return the Task 6 schema with canonical singleton jobs.
- `baseline_gaps(selection, results, evidences, store, objects) -> tuple[Error, ...]`: validate frozen parent provenance and member child evidence, check actual publication absence, and mark only baseline gaps entirely attributable to checked selected source refusals.
- `run_workflow(context: RunContext, settings: Settings, intent: Mapping, dispatcher: Dispatcher, store, objects, observer=None) -> WorkflowResult`: freeze selection before source dispatch, replay immutable receipts with exact context/projection checks, repair receipt indexes only to the validated descriptor, stop after fatal acquisition, retain undispatched deadline/halted units, and assemble coverage/counters/captures/repair resolutions.

Original exact members remain individual checkpoints. Complete/failed/pending counters collapse source identity; discovery counts match immutable parent cardinality. Completion captures and child receipts retain the original processing authority and affected-quarter obligations.

## Red → green and reproduced deviations

Evidence directory: `specs/evidence/sec-filing-index-ingestion/stage-4/plan5-execution/task-8/`. Each command JSON records exact argv, combined full stdout/stderr, and exit code; the scoped commands also retain their test filters. No test assertion was weakened.

1. `red.json`: the unchanged prescribed runner discovery command exited 1 with `ModuleNotFoundError: sec_edgar_ingest.workflows.runner`, after writing the supplied six real-store tests and before creating production code.
2. `initial-green.json`: the supplied mixed-refusal/valid-progress test failed, reporting `quarantined` instead of `incomplete`. A diagnostic reproduction decoded the report and identified the Q4 collection gap `content_length_mismatch`: replacing the ZIP body/digest left the original conflicting ZIP's Content-Length header. Both supplied fixture-body replacement sites now set Content-Length to the replacement bytes' length (including the empty-directory fixture). Assertions are unchanged; guards and parser behavior are unchanged.
3. `cardinality-red.json`: the supplied subtract-known discovery count was restored and tested against accepted Task 6. A fresh backfill after prior successful publication failed with `selection discovered-source count differs from immutable parent`. Corrected to `len(current)`, which equals the original discovered parent cardinality; reducer source-identity deduplication is preserved.
4. `immutable-replay-red-final.json`: replay after replacing the mutable DiscoverySession row with corrupt data failed in `registry.record → read_member → read_parent` with `KeyError: frozen`. Saved receipts now use the full predecessor `_read_receipt`, bind exact frozen context/member projection, derive the exact predecessor descriptor/key, and use immutable index insertion (missing rows repaired; divergent rows refused). Baseline assembly validates the frozen `parent_provenance` through the predecessor object-only validator. Mutable discovery data cannot replace historical frozen authority.
5. `missing-provenance-red.json`: missing frozen member provenance caused the supplied broad FileNotFoundError handler to redispatch discovery; the regression failed with `AssertionError: recomputed frozen selection`. The fallback now surrounds only the initial selection.json read. Missing evidence for an existing frozen selection propagates refusal without rediscovery.

The two early immutable-replay setup runs are retained transparently: `immutable-replay-red.json` used a newly generated deadline and failed frozen-context validation; `immutable-replay-red-corrected-setup.json` then used the original context but initially addressed an unhashed state key. Neither is claimed as the production defect red. The final reproduction uses the exact original context and the actual SHA-256 DiscoverySession key.

## Verification

Final unchanged runner command:

```text
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_runner.py -v
```

`verified-green.json`: exit 0, 19 methods PASS, 188.679 seconds. Earlier retained green checkpoints: 12 methods (`expanded-green.json`) and 17 methods (`final-green.json`); these are not substitutes for the final check. `repair-scoped.json` records the scoped post-CAS/process-death case passing.

Named predecessor commands use the same guarded/offline/frozen argv and `-p` filename:

| Filename | Methods | Exit | Evidence |
|---|---:|---:|---|
| test_workflow_completion.py | 20 | 0 | test_workflow_completion.py.json |
| test_workflow_processing.py | 14 | 0 | test_workflow_processing.py.json |
| test_workflow_results.py | 20 | 0 | test_workflow_results.py.json |
| test_workflow_legacy.py | 10 | 0 | test_workflow_legacy.py.json |

The predecessor suites completed before the final runner-only catch correction; they do not import this runner and predecessor files were unchanged. No broad suite or reserved Stage 7 integrated check was run.

`git-check-1.json`: prescribed `git -c core.whitespace=cr-at-eol diff --check`, exit 0.
`git-check-2.json`: additionally checked staged new-file whitespace with `git -c core.whitespace=cr-at-eol diff --cached --check`, exit 0.
`git-check-0.json` and `git-check-3.json` record explicit owned-file staging and the two-file staged diff.
`commit.json` records the required commit command and successful output.

## Required scoped coverage and observed histories

- Inclusive Q3→Q4 baseline publication: two complete sources and one logical filing per quarter; complete captures/receipts round-trip through the real result reader.
- All source refusals: no accepted Processing or pointer state, both baseline gaps retained and attributed to checked quarantine; mixed valid/refused progress remains incomplete.
- Empty quarter: independent baseline_source_missing remains unmarked; valid empty daily discovery without backlog returns no_new_sources.
- Formerly affected Q3 after initial publication and a Q4 replacement: original Q3 pointer stays intact, Q4 publishes, Q3 failure prevents complete source coverage.
- Ordinary post-CAS ancillary failure and simulated process death: Q3 pointer already exists, no workflow report is written, replay repairs ancillary publication evidence before source completion and preserves that pointer.
- Expired original/fresh valid workflow attempt: repair resolutions retained, Q3 pointer unchanged, original WorkflowChildCall rows preserved, two complete source identities.
- Gate-only and mixed gate/progress: awaiting_approval/current pointer separation retained; gate-only awaiting_approval, mixed incomplete, and Q3 pointer unchanged.
- Failed daily directory: boundary held, baseline publications retained; coverage is independent of boundary date.
- Backfill/daily sharing run/attempt IDs: disjoint child result namespaces and logical filing deduplication retained.
- Fresh versus exact replay: fresh discovery includes every immutable parent source; exact replay dispatches nothing and returns the same receipt/capture intent.
- Deadline after selection: every selected source reported pending, no source child calls/receipts, no Processing rows or pointers.
- No-result discovery: absent parent does not erase the actual frozen required-unit session ledger or older pending jobs.
- Corrupt retained registry/receipt: valid sibling publications continue while legacy uncertainty remains explicit.
- Historical replay after mutable discovery corruption: original immutable receipt/parent provenance retained. Missing receipt index repairs exactly; contradictory descriptor refuses without overwrite. Missing frozen provenance refuses without reselecting or redispatching.

## Self-review and skill application

Read and applied clean-code, clean-coder, test-driven-development, and verification-before-completion. Used the inherited available model; no subagents, network, fetches, provider changes, or dependency changes.

Applied: public names and context/projection/descriptor terminology retain domain meaning (N1/N4); the four approved functions keep selection, checked receipt orchestration, reuse, and baseline attribution cohesive (G6/G30); comments preserve the reasons immutable authority and singleton checkpointing matter (C3/C4); source, empty-quarter, deadline, refusal, repair, missing-evidence, and divergent-index boundaries have real-store tests (T1/T5/T6). No adjacent tidying or structural refactor was performed.

Reviewed ownership/diff, source-identity counter collapse, exact discovered-member representation, frozen session/ledger preservation, receipt full schema/context binding, missing-index repair versus divergent-row refusal, no discovery on missing frozen evidence, fatal dispatch stopping, affected-quarter repair, and quarantine attribution. The runner deliberately consumes the existing internal full receipt reader/descriptor helpers, as the accepted Task 6 reader does, rather than adding an alternate receipt decoder.

No unresolved implementation finding identified by this self-review. Independent review is required and remains the gate for Task 9. Live-access authorization remains closed; all 22 Stage 7 integrated checks remain reserved/not_run. Selected limits remain unmeasured deployed fit; raw/observation/generation/manifest/candidate/quarantine/report retention remains indefinite in development.
