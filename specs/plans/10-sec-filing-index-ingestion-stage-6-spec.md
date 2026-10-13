# SEC filing-index ingestion — Stage 6 Azure definitions and orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

> Roadmap: specs/sec-filing-index-ingestion-roadmap.md, Stage 6 — on plan completion, tick the
> stage and re-validate later stages against what shipped.

**Goal:** Define the whole Stage 6 Azure deployment as versioned Bicep with a committed compile: role matrix, storage, registry, monitoring, the job, the factory pipelines, stopped triggers and alerts. Prove the run-worker pipeline's start, poll, result and classification logic offline by interpreting its committed JSON.

**Architecture:** This is the second Stage 6 plan, and it carries the roadmap stamp: **its completion ticks Stage 6.** It runs after Plan 9 and consumes Plan 9's worker contract:

- the Azure config template;
- `--config-env` and `CONTAINER_APP_JOB_EXECUTION_NAME`;
- `workflow_summary`;
- the JSON content type.

`infra/azure/sec-edgar-ingest/main.bicep` compiles with Bicep 0.38.33 into the committed `main.json`. The tests read only committed files, with the stdlib.

The run-worker pipeline is authored in `pipelines/render.py` and rendered to committed JSON. A strict ADF interpreter (`tests/adf_interpreter.py`) runs that JSON against scripted Azure responses, once under every reading of the behaviour the ADF documentation leaves open. Nothing calls Azure.

**Tech Stack:**

- Bicep 0.38.33, installed by Azure CLI 2.90.0;
- the ARM API versions of F1 §5;
- ADF 2018-06-01 pipeline JSON and KQL;
- Python ≥3.14 unittest under `tests/network_guard.py`;
- uv 0.12.15, offline and frozen.

**Spec:** `specs/sec-filing-index-ingestion-stage-6-spec.md` (APPROVED 2026-10-12). This plan implements:

- §5, the role matrix;
- §7 and §8, the monitoring resources and alerts;
- §9, §10 and §11;
- the §12 rows marked 10;
- §15.

## Global Constraints

Copied verbatim from spec §2:

- ADF passes references, not index contents.
- A start timeout with an unknown execution id is an ambiguous start, not permission to launch a second copy.
- Resolve the existing execution or stop for operator recovery.
- Success also requires the matching worker result file.
- **Execution unknown:** ambiguous job start or unresolvable execution status. No false success and no blind launch retry.
- A successful start is not job success.
- Failed, timed-out and unknown executions propagate correctly; a missing or mismatched worker result cannot pass the stage.
- A gated reconciliation is not reported as complete.
- ADF owns the production schedules, configured with its supported Eastern time-zone identifier and daylight-saving behavior.
- Container Apps Jobs has no independent schedule for these same runs.
- Trigger enablement is an explicit release step, not a side effect of creating infrastructure.
- Use managed identities for ADF management calls and worker access to Azure resources.
- Pin and review permissions; do not place storage keys in worksets or source URLs.
- Production deployment pins the image digest and configuration revision.
- Keep infrastructure, role assignments, job definitions, ADF pipelines, schedules and alerts under version control.
- Alert on a failed job, ambiguous start, lease failure, access block, exhausted retry budget, quarantine, unresolved publication conflict or pending withdrawal approval.
- Report discovery age, oldest listed-but-unpublished source and last successful reconciliation separately.
- A no-new-file run is distinct from a failed discovery; weekends alone do not imply stale ingestion.
- CI runs on committed fixtures and mocked SEC responses; it downloads nothing from the SEC.
- **F1 §2 bindings:** D-01 tenant and subscription; D-02 group `rg-sec-edgar-dev-eastus`; D-03 names; region order eastus → eastus2 → centralus.
- **F1 §5 management API versions:** Jobs `2026-07-01`; ADF `2018-06-01`; Storage `2025-06-01`; UAMI `2024-11-30`; roles `2022-04-01`; ACR `2025-11-01`; Log Analytics `2025-07-01`; diagnostic settings `2021-05-01-preview`; action group `2023-01-01`; scheduled-query alert `2023-12-01`.
- **F1 §6 job values:** 2 vCPU / 4 GiB, one replica, parallelism 1, completion count 1, `replicaTimeout` 3,600 s, zero native retries.
- **D-18 observer:** 30 s poll base, a longer Retry-After honored, and a 4,200 s observation deadline.
- **Tools:** CLI **2.90.0**, Bicep **0.38.33**, uv **0.12.15**.
- Existing config, workset and binding-registry bytes are never rewritten. All 22 Stage 7 integrated checks remain reserved/not_run.

From spec §1, §9, §10 and §14:

- The work is offline: no SEC, Azure management or data-plane, credential, deployment or trigger activity. D1 authorizes local tool installs only.
- `az deployment … validate` and `what-if` call Azure, so they wait for Stage 7. Nothing in this plan logs in to Azure or selects a subscription.
- The suite reads `main.json`, the pipeline JSON, `roles.json` and the alert KQL with the stdlib; it needs no external tool. Only the check script runs Bicep.
- Lean process: red/green TDD and a review per task, a final whole-branch review, and at plan exit the full offline suite, a wheel build and a CLI smoke test.

**Leave alone:**

- `specs/evidence/**`;
- the accepted F1 bytes;
- `specs/sec-filing-index-ingestion-stage-4-spec.md`;
- `specs/plans/4-…` and `specs/plans/5-…`;
- everything under `specs/plans/completed/`;
- the historical roadmap sections;
- deferred items not bound to Stage 6;
- Plan 9's shipped code and files, which this plan only consumes.

**Prerequisite: Plan 9 is complete.** Tasks 2, 5 and 7 import or read what it ships:

- the `--config-env` workflow parser;
- `infra/azure/sec-edgar-ingest/config/sec-edgar-ingest.azure.template.json`;
- `sec_edgar_ingest.workflows.summary.SUMMARY_FIELDS`.

Check before Task 1:

```bash
test -f packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/summary.py && test -f infra/azure/sec-edgar-ingest/config/sec-edgar-ingest.azure.template.json && echo ready
```

Expected: `ready`.

**Conventions used below.** Run every command from the repository root `/Users/lowell/Projects/sec-edgar`. One test module runs with:

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py <module> -v
```

Every commit message ends with:

```text
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

## Decisions

- **D1** (owner, brief, 2026-10-12): "Local build, Stage 6 only. Install a local container runtime with buildx (amd64 emulation) and Bicep 0.38.33. These are tool installs only, with no Azure or SEC calls. The local image proves the commands run; the release image is still built by ACR quick task in Stage 7 (S7-05), so its digest will differ." Applied in: Task 4 (Bicep install), Task 9 (Bicep rebuild check); the container runtime is Plan 9's. Home: spec §14.
- **D2** (owner, brief, 2026-10-12): a short Stage 6 spec with an owner-decisions section before the plan. Applied in: the spec (approved 2026-10-12). Home: spec §14.
- **D3** (owner, spec review, 2026-10-12): "Approved — write both plans". This approves the spec, Q1–Q4 and its twelve defaults, including two plans at the §13 seam (this plan carries the stage stamp) and offline checks on the committed compiled template with an expression interpreter (§10). Applied in: all tasks; Global Constraints.
- **D4** (owner, plan review, 2026-10-13): "Plan 10 approved", as written ("As written, with Task 3"), including the Task 3 spec amendment (Settled item 4). Applied in: all tasks; Task 3 (spec amendment).
- **D5** (owner, plan review, 2026-10-13): "Decline now, keep item open". This plan adds no alert on a non-null `summary_error`, so Task 7 is unchanged. The deferred item "Plan 10 has no alert on `summary_error`" stays open, to close before the Stage 7 deploy. No alert in this plan reads `gap_codes`, so its keys stay unconstrained here. Applied in: Task 7 (nothing added). Home: this entry.
- **D6** (owner, plan review, 2026-10-13): "D1 covers it; carry both to Stage 7". D1 covers the Colima VM disk image (about 325 MB) that Plan 9's Task 11 downloaded. This plan builds no image and starts no container runtime, so two Plan 9 deferred items carry to later work: the image-smoke hardening to Stage 7's image work, and the `docker image ls -a --digests` check to the next `colima start`. Applied in: none. Home: this entry.
- **D7** (owner, plan review, 2026-10-13): "Yes, per-model for Plan 10". Each commit ends with the `Co-Authored-By` line naming the model that wrote it (Opus, Sonnet or Haiku 5.5), not the literal Opus line in this plan's commit messages. This continues the owner's choice during Plan 9's execution (2026-10-13). Applied in: every commit. Home: this entry.

Settled for the owner's review at plan approval:

1. **Two plans** (brief default 1). Plan 9 is the worker half; this plan is the definitions half and ticks Stage 6.
2. **Deferred-item scope** (brief default 2). This plan closes no deferred item; Plan 9 closes the three Stage 6 items.
3. **Offline checks** (brief default 3), as spec §10 states. One addition: the pipeline JSON is authored in `pipelines/render.py`, and a test requires the committed JSON to equal its output. That parallels `main.bicep` → `main.json`, and makes the 47-activity pipeline reviewable as named expressions rather than 1,000 lines of JSON.
4. **Start-body evaluation (spec amendment, Task 3).** The start override is a JSON object whose container fields are ADF expressions. This follows the nested-expression body in ADF's control-flow tutorial, but no reference page states it. A wrong evaluation cannot produce a matching result, so it can only end in a non-success outcome. Task 3 adds it to §11's S7-06 assumptions.
5. **Switch property `on`.** The ARM template reference for `factories/pipelines@2018-06-01` names the Switch expression `on`; the Switch how-to page shows `expression`. The pipelines use `on`, the property the deployment schema accepts, and the interpreter refuses `expression`.
6. **Following a 202.** Only a validated `Location` header is followed (spec §7.1). The validation rejects:
   - another scheme, host, user information or port;
   - another subscription or region;
   - another route;
   - a dot or percent-encoded segment;
   - a fragment, or a second query;
   - any API version other than `2026-07-01`.

   An `Azure-AsyncOperation` header alone yields `execution_unknown`. The operation response names the execution only when its `id` is exactly `<job>/executions/<name>`. An operation-status body therefore never passes for an execution.
7. **Reading of §7.3.** A matching result whose `outcome` is not an `EXIT_CODES` key is `result_mismatch`, the "present but not matching" row.
8. **Budgets.**
   - The run-worker pipeline has 47 activities, against ADF's documented maximum of 120 per pipeline, inner activities included.
   - Its longest expression has 1,265 characters, against a limit of 8,192, and the pipeline object is 18.5 KB, against 200 KB. `validate_pipeline` enforces all three limits.
   - Its Until times out at 3 h. That covers two launches of 4,200 s observation plus their waits.
   - A timeout leaves the outcome empty, so it ends `execution_unknown`.
9. **Values the spec leaves to the plan.**
   - The resource group uses API `2024-03-01`; F1 §5 lists no group version.
   - The Consumption environment is a workload-profiles environment with the `Consumption` profile.
   - Alert names are `alert-sec-edgar-<slug>`.
   - Per-run alerts are stateless and run every 15 minutes over a 30-minute window. One event can mail twice; an event ingested up to 15 minutes late still mails.
   - The staleness alerts are stateful and run hourly over two days.
   - Every rule sets `skipQueryValidation`, because the resource-specific tables may not exist before first ingestion. S7-17 proves that each alert fires.
10. **Bicep is first compiled during execution** (D1 timing). The template tests locate values in the shapes Bicep emits. Task 4 Step 7 says what to do when the emitted shape differs but the meaning holds.
11. **Plan size.** About 4,300 lines, over the lean guide, as Plan 9 was. Most of it is complete code: the interpreter, the pipeline source, the Bicep, and the test suites.

---

## File map

| File | Responsibility | Task |
|---|---|---|
| `tests/adf_interpreter.py` (new) | Strict ADF expression and activity interpreter | 1 |
| `infra/azure/sec-edgar-ingest/pipelines/render.py` and `*.json` (new) | Run-worker and caller pipelines, rendered | 2 |
| `tests/support_adf.py` (new) | Scripted Azure: exact routes, audiences and results | 2 |
| `specs/sec-filing-index-ingestion-stage-6-spec.md` | §11 amendment | 3 |
| `infra/azure/sec-edgar-ingest/roles.json` (new) | The §5 role matrix | 4 |
| `infra/azure/sec-edgar-ingest/main.bicep`, `main.json` (new) | Subscription-scope definition and its committed compile | 4–7 |
| `infra/azure/sec-edgar-ingest/modules/*.bicep` (new) | Identities, registry, monitoring, storage, job, factory, alerts | 4, 5, 7 |
| `infra/azure/sec-edgar-ingest/modules/access/*.bicep` (new) | Role assignments per scope | 6 |
| `infra/azure/sec-edgar-ingest/alerts/*.kql` (new) | The ten §8 queries | 7 |
| `tests/support_template.py` (new) | Stdlib reader for the compiled template | 4 |
| `docs/runbooks/sec-edgar-azure-operations.md` (new) | Deployment, triggers, outcomes, alerts | 8 |
| `scripts/check-sec-edgar-ingest.sh` | Pipeline render and Bicep rebuild checks | 9 |

Test paths below are under `packages/sec-edgar-ingest/tests/`.

---

### Task 1: The ADF interpreter

The interpreter is the instrument behind spec §10. It models what the ADF documentation states:

- `@` expressions with `@@` escapes and `@{}` interpolation;
- dependency conditions, AND across edges and OR within one;
- the leaf rule for pipeline status;
- Until (children run, then the condition, then the timeout) and Switch;
- `startsWith` and `endsWith` that ignore case, and a `contains` that respects it;
- the `o` timestamp format.

Behaviour the documentation leaves open is a `Semantics` field: a missing property either throws or yields null; `if`, `and` and `or` are either lazy or eager; string `equals` either respects or ignores case. Anything else raises `AdfUnsupported`: an unknown function, `?.`, a bare identifier, a wrong arity or an unmodelled activity type. So does breaking a documented limit: 120 activities, 8,192 characters per expression, 200 KB per pipeline object, or 25 Switch cases. A pipeline that strays outside the subset therefore fails its tests.

**Files:**
- Create: `tests/adf_interpreter.py`
- Create: `tests/test_adf_interpreter.py`

**Interfaces:**
- Consumes: nothing from the package.
- Produces:
  - `Semantics(missing='throw'|'null', lazy: bool, equals_ignores_case: bool)` and `ALL_SEMANTICS` (all 8).
  - `PipelineRun(pipelines: dict, web: Callable[[Request], Response], semantics=Semantics(), faults=frozenset(), start=datetime, max_iterations=20000)`. Its `.run(name, parameters) -> Outcome(status, failures, variables, run_id)` returns the run. Its `.requests` are `Request(method, url, headers, body, resource, at)` records, and its `.trace` holds `(activity, status, output)` tuples.
  - `Response(status=200, body=dict, headers=dict)`; the errors `WebFailure`, `ExpressionError` and `AdfUnsupported`.
  - `validate_pipeline(definition)` and `walk_activities(activities)`; also `FUNCTIONS`, `Evaluator` and `Scope`.

- [ ] **Step 1: Write the failing tests**

`tests/test_adf_interpreter.py`:

```python
"""The ADF interpreter models only what the documentation states, and refuses everything else."""
from network_guard import install
install()

import unittest

from adf_interpreter import (ALL_SEMANTICS, AdfUnsupported, Evaluator, ExpressionError, PipelineRun, Response, Scope,
                             Semantics, validate_pipeline)


def evaluate(text, semantics=Semantics(), variables=None, parameters=None):
    run = PipelineRun({}, lambda request: Response(), semantics)
    run.variables, run.parameters = dict(variables or {}), dict(parameters or {})
    return Evaluator(run, Scope()).value(text)


def expression(text):
    return {'value': text, 'type': 'Expression'}


def setv(name, variable, value, *depends):
    return {'name': name, 'type': 'SetVariable', 'dependsOn': [{'activity': source, 'dependencyConditions': conditions}
                                                               for source, conditions in depends],
            'typeProperties': {'variableName': variable, 'value': value}}


def fail(name, *depends):
    return {'name': name, 'type': 'Fail', 'dependsOn': [{'activity': source, 'dependencyConditions': conditions}
                                                        for source, conditions in depends],
            'typeProperties': {'message': 'failed', 'errorCode': expression("@variables('code')")}}


def run(activities, variables=('code', 'mark'), faults=(), semantics=Semantics()):
    definition = {'activities': activities, 'variables': {name: {'type': 'String'} for name in variables}}
    validate_pipeline(definition)
    engine = PipelineRun({'p': definition}, lambda request: Response(), semantics, frozenset(faults))
    return engine.run('p', {}), engine


class ExpressionTests(unittest.TestCase):
    def test_literals_escapes_and_interpolation(self):
        self.assertEqual(evaluate("@concat('it''s', ' ', string(42))"), "it's 42")
        self.assertEqual(evaluate('@@not-an-expression'), '@not-an-expression')
        self.assertEqual(evaluate("plain"), 'plain')
        self.assertEqual(evaluate("a-@{variables('x')}-@{createArray(1, 2)}", variables={'x': 'b'}), 'a-b-[1,2]')
        self.assertEqual(evaluate("@createArray('a', variables('x'))", variables={'x': 'b'}), ['a', 'b'])
        self.assertEqual(evaluate({'nested': ["@variables('x')"], 'n': 1}, variables={'x': 'b'}), {'nested': ['b'], 'n': 1})

    def test_accessors_and_missing_values(self):
        value = {'a': {'b': [{'c': 'd'}]}}
        self.assertEqual(evaluate("@pipeline().parameters.v.a.b[0].c", parameters={'v': value}), 'd')
        self.assertEqual(evaluate("@pipeline().parameters.v['a']['b'][0]['c']", parameters={'v': value}), 'd')
        with self.assertRaises(ExpressionError):
            evaluate("@pipeline().parameters.v.a.missing", parameters={'v': value})
        self.assertIsNone(evaluate("@pipeline().parameters.v.a.missing.deeper", Semantics('null'),
                                   parameters={'v': value}))
        self.assertIsNone(evaluate("@pipeline().parameters.v.a.b[3]", Semantics('null'), parameters={'v': value}))
        with self.assertRaises(ExpressionError):
            evaluate("@pipeline().parameters.v.a.b.c", Semantics('null'), parameters={'v': value})

    def test_undocumented_behaviour_is_a_semantics_choice(self):
        failing = "@if(equals(1, 1), 'chosen', int('x'))"
        self.assertEqual(evaluate(failing, Semantics(lazy=True)), 'chosen')
        with self.assertRaises(ExpressionError):
            evaluate(failing, Semantics(lazy=False))
        self.assertEqual(evaluate("@or(equals(1, 1), int('x'))", Semantics(lazy=True)), True)
        with self.assertRaises(ExpressionError):
            evaluate("@or(equals(1, 1), equals(int('x'), 1))", Semantics(lazy=False))
        self.assertFalse(evaluate("@equals('Succeeded', 'succeeded')", Semantics(equals_ignores_case=False)))
        self.assertTrue(evaluate("@equals('Succeeded', 'succeeded')", Semantics(equals_ignores_case=True)))
        self.assertEqual(len(ALL_SEMANTICS), 8)

    def test_documented_case_rules(self):
        self.assertTrue(evaluate("@startsWith('HTTPS://Management.azure.com/x', 'https://management.azure.com/')"))
        self.assertTrue(evaluate("@endsWith('a/B', '/b')"))
        self.assertFalse(evaluate("@contains('Microsoft.App', 'microsoft.app')"))
        self.assertTrue(evaluate("@contains(createArray('a', 'b'), 'b')"))
        self.assertFalse(evaluate("@contains(createArray('a', 'b'), 'B')"))

    def test_time_functions_use_the_o_format(self):
        moment = evaluate("@addSeconds('2026-10-12T09:00:00.0000000Z', 3300)")
        self.assertEqual(moment, '2026-10-12T09:55:00.0000000Z')
        self.assertEqual(evaluate(f"@formatDateTime('{moment}', 'yyyy-MM-ddTHH:mm:ss')"), '2026-10-12T09:55:00')
        self.assertEqual(evaluate("@ticks('0001-01-01T00:00:01Z')"), 10_000_000)
        self.assertLess(evaluate("@ticks('2026-10-12T09:00:00Z')"), evaluate(f"@ticks('{moment}')"))
        with self.assertRaises(AdfUnsupported):
            evaluate("@formatDateTime('2026-10-12T09:00:00Z', 'o')")

    def test_conversions_are_strict(self):
        self.assertEqual(evaluate("@int('42')"), 42)
        self.assertEqual(evaluate("@string(json('{\"a\":[1]}'))"), '{"a":[1]}')
        for text in ("@int('4.2')", "@json('not json')", "@concat('a', 1)", "@string(equals(1, 1))", "@not('true')"):
            with self.subTest(text), self.assertRaises(ExpressionError):
                evaluate(text)

    def test_anything_outside_the_subset_is_refused(self):
        for text in ("@utcnow()", "@union(createArray(1, 2), createArray(3, 4))", "@createArray('one')",
                     "@and(true, false)", "@body('x')?.y", "@or(equals(1, 1), equals(1, 1), equals(1, 1))",
                     "@variables('undeclared')"):
            with self.subTest(text), self.assertRaises(AdfUnsupported):
                evaluate(text)


class ActivityTests(unittest.TestCase):
    def test_dependency_conditions_and_skips(self):
        outcome, engine = run([
            setv('A', 'code', 'a'),
            fail('B', ('A', ['Succeeded'])),
            setv('C', 'mark', 'after failure', ('B', ['Failed'])),
            setv('D', 'mark', 'never', ('B', ['Succeeded'])),
            setv('E', 'code', 'skip seen', ('D', ['Skipped'])),
        ])
        self.assertEqual([event[:2] for event in engine.trace],
                         [('A', 'Succeeded'), ('B', 'Failed'), ('C', 'Succeeded'), ('D', 'Skipped'), ('E', 'Succeeded')])
        self.assertEqual(outcome.variables['mark'], 'after failure')

    def test_the_leaf_rule_decides_pipeline_status(self):
        handled, _ = run([fail('A'), setv('B', 'mark', 'handled', ('A', ['Failed']))])
        self.assertEqual(handled.status, 'Succeeded')
        skipped_leaf, _ = run([fail('A'), setv('B', 'mark', 'x', ('A', ['Succeeded']))])
        self.assertEqual(skipped_leaf.status, 'Failed')
        completed, _ = run([fail('A'), setv('B', 'mark', 'x', ('A', ['Completed']))])
        self.assertEqual(completed.status, 'Succeeded')

    def test_fail_records_its_code_and_an_empty_code_is_not_a_string(self):
        outcome, _ = run([setv('A', 'code', 'execution_unknown'), fail('B', ('A', ['Succeeded']))])
        self.assertEqual([failure['errorCode'] for failure in outcome.failures], ['execution_unknown'])
        outcome, _ = run([fail('B')])
        self.assertEqual([failure['errorCode'] for failure in outcome.failures], ['ErrorCodeNotString'])

    def test_until_continues_after_an_inner_failure_and_times_out(self):
        loop = {'name': 'Loop', 'type': 'Until', 'typeProperties': {
            'expression': expression("@equals(variables('mark'), 'x')"), 'timeout': '0.00:01:00',
            'activities': [fail('Inner'), setv('Count', 'code', 'looped', ('Inner', ['Completed']))]}}
        outcome, engine = run([loop, setv('After', 'mark', 'ran', ('Loop', ['Completed']))])
        self.assertEqual(engine.trace[-2][:2], ('Loop', 'Failed'))
        self.assertEqual(outcome.variables['mark'], 'ran')
        self.assertGreater(sum(event[0] == 'Count' for event in engine.trace), 5)

    def test_a_fault_fails_an_activity_without_running_it(self):
        outcome, engine = run([setv('A', 'code', 'a'), setv('B', 'mark', 'b', ('A', ['Completed']))], faults={'A'})
        self.assertEqual((outcome.variables['code'], outcome.variables['mark']), ('', 'b'))

    def test_set_variable_keeps_the_declared_type(self):
        outcome, engine = run([setv('A', 'code', expression('@createArray(1, 2)'))])
        self.assertEqual((engine.trace[0][1], outcome.variables['code']), ('Failed', ''))


class ValidationTests(unittest.TestCase):
    def refused(self, activities, variables=('code', 'mark')):
        definition = {'activities': activities, 'variables': {name: {'type': 'String'} for name in variables}}
        with self.assertRaises(AdfUnsupported):
            validate_pipeline(definition)

    def test_documented_structural_rules(self):
        self.refused([setv('A', 'code', 'a'), setv('A', 'mark', 'b')])
        self.refused([setv('A', 'code', expression("@concat(variables('code'), 'x')"))])
        self.refused([setv('A', 'code', 'a'), setv('B', 'mark', 'b', ('A', ['Completed'])),
                      setv('C', 'mark', 'c', ('A', ['Succeeded']))])
        self.refused([setv('A', 'code', 'a', ('Elsewhere', ['Succeeded']))])
        self.refused([setv('A', 'undeclared', 'a')])
        self.refused([{'name': 'Copy', 'type': 'Copy', 'typeProperties': {}}])
        inner_if = {'name': 'Inner', 'type': 'IfCondition', 'typeProperties': {
            'expression': expression('@equals(1, 1)'), 'ifTrueActivities': []}}
        self.refused([{'name': 'Outer', 'type': 'Switch', 'typeProperties': {
            'on': expression("@variables('code')"), 'cases': [{'value': 'a', 'activities': [inner_if]}],
            'defaultActivities': []}}])
        self.refused([{'name': 'Outer', 'type': 'Switch', 'typeProperties': {
            'on': expression("@variables('code')"), 'cases': [{'value': 'a', 'activities': []}]}}])
        self.refused([{'name': 'Outer', 'type': 'Switch', 'typeProperties': {
            'expression': expression("@variables('code')"), 'defaultActivities': [],
            'cases': [{'value': 'a', 'activities': []}]}}])
        self.refused([{'name': 'Outer', 'type': 'Switch', 'typeProperties': {
            'on': expression("@variables('code')"), 'defaultActivities': [],
            'cases': [{'value': str(index), 'activities': []} for index in range(26)]}}])
        inner_until = {'name': 'Inner', 'type': 'Until', 'typeProperties': {
            'expression': expression('@equals(1, 1)'), 'activities': []}}
        self.refused([{'name': 'Outer', 'type': 'Until', 'typeProperties': {
            'expression': expression('@equals(1, 1)'), 'activities': [inner_until]}}])
        self.refused([setv(f'A{index}', 'code', 'a') for index in range(121)])
        self.refused([setv('A', 'code', expression('@concat(' + ', '.join(["'x'"] * 2100) + ')'))])
        self.refused([setv(f'A{index}', 'code', 'x' * 2000) for index in range(110)])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_adf_interpreter -v`
Expected: ERROR at import with `ModuleNotFoundError: No module named 'adf_interpreter'`.

- [ ] **Step 3: Write the interpreter**

`tests/adf_interpreter.py`:

```python
"""A deliberately strict interpreter for the subset of Azure Data Factory that the Stage 6 pipelines use.

It runs the committed pipeline JSON itself, not a restatement of it. Behaviour the ADF documentation leaves
open is a `Semantics` parameter, and the scenarios must reach the same outcome under every combination. A
function, activity type or property outside the subset raises `AdfUnsupported`, so the tests fail instead of
guessing.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from itertools import product
from typing import Callable

ACTIVITY_TYPES = frozenset({'WebActivity', 'Until', 'Wait', 'IfCondition', 'Switch', 'SetVariable',
                            'ExecutePipeline', 'Fail'})
CONTAINERS = {'Until': ('activities',), 'IfCondition': ('ifTrueActivities', 'ifFalseActivities'),
              'Switch': ('defaultActivities',)}
CONDITIONS = frozenset({'Succeeded', 'Failed', 'Skipped', 'Completed'})
VARIABLE_TYPES = {'String': str, 'Bool': bool, 'Array': list}
# Documented ADF limits: activities per pipeline (inner activities included), characters per expression,
# bytes per pipeline object, and cases per Switch.
MAX_ACTIVITIES = 120
MAX_EXPRESSION = 8_192
MAX_PIPELINE_BYTES = 200 * 1024
MAX_CASES = 25


class AdfUnsupported(Exception):
    """The definition uses something outside the modelled subset."""


class ExpressionError(Exception):
    """An expression fails at run time, which fails its activity."""


class WebFailure(Exception):
    """No usable HTTP response: a transport error, a status of 400 or more, or a body that is not a JSON object."""


class _Timeout(Exception):
    pass


@dataclass(frozen=True)
class Semantics:
    missing: str = 'throw'           # a missing property or index: 'throw' fails the activity, 'null' yields null
    lazy: bool = True                # if, and, or evaluate only the arguments they need
    equals_ignores_case: bool = False


ALL_SEMANTICS = tuple(Semantics(missing, lazy, folded)
                      for missing, lazy, folded in product(('throw', 'null'), (True, False), (False, True)))


# ---------------------------------------------------------------- expressions

_TOKEN = re.compile(r"\s*(?:(?P<string>'(?:[^']|'')*')|(?P<number>-?\d+)|(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
                    r"|(?P<punct>[(),.\[\]}]))")


def _tokens(text: str, start: int):
    position = start
    while True:
        match = _TOKEN.match(text, position)
        if match is None:
            rest = text[position:].strip()
            if rest:
                raise AdfUnsupported(f'cannot tokenize expression at {text[position:position + 20]!r}')
            yield ('end', None, len(text))
            return
        kind = match.lastgroup
        value = match.group(kind)
        yield (kind, value, match.end())
        if kind == 'punct' and value == '}':
            return
        position = match.end()


class _Parser:
    def __init__(self, text: str, start: int = 0):
        self.text = text
        self.stream = _tokens(text, start)
        self.current = next(self.stream)

    def take(self, kind=None, value=None):
        token = self.current
        if (kind and token[0] != kind) or (value and token[1] != value):
            raise AdfUnsupported(f'unexpected token {token[1]!r} in {self.text!r}')
        if token[0] != 'end' and token[1] != '}':
            self.current = next(self.stream)
        return token

    def expression(self):
        kind, value, _ = self.take()
        if kind == 'string':
            node = ('literal', value[1:-1].replace("''", "'"))
        elif kind == 'number':
            node = ('literal', int(value))
        elif kind == 'name':
            if self.current[1] != '(':
                raise AdfUnsupported(f'bare identifier {value!r} is outside the subset')
            self.take(value='(')
            arguments = []
            if self.current[1] != ')':
                arguments.append(self.expression())
                while self.current[1] == ',':
                    self.take(value=',')
                    arguments.append(self.expression())
            self.take(value=')')
            node = ('call', value, arguments)
        else:
            raise AdfUnsupported(f'unexpected token {value!r} in {self.text!r}')
        while self.current[1] in ('.', '['):
            if self.take()[1] == '.':
                node = ('property', node, self.take('name')[1])
            else:
                node = ('index', node, self.expression())
                self.take(value=']')
        return node


def parse(text: str):
    """Parse the body of an `@` expression."""
    parser = _Parser(text)
    node = parser.expression()
    if parser.current[0] != 'end':
        raise AdfUnsupported(f'trailing text in {text!r}')
    return node


def _segments(text: str):
    """A JSON string as ('literal', text) and ('expression', node, interpolated) segments."""
    if text.startswith('@@'):
        return [('literal', text[1:])]
    if text.startswith('@') and not text.startswith('@{'):
        return [('expression', parse(text[1:]), False)]
    segments, position = [], 0
    while (start := text.find('@{', position)) >= 0:
        segments.append(('literal', text[position:start]))
        parser = _Parser(text, start + 2)
        node = parser.expression()
        if parser.current[1] != '}':
            raise AdfUnsupported(f'unterminated interpolation in {text!r}')
        segments.append(('expression', node, True))
        position = parser.current[2]
    segments.append(('literal', text[position:]))
    return segments


def functions_used(node) -> set[str]:
    if node[0] == 'literal':
        return set()
    if node[0] == 'call':
        return {node[1]}.union(*(functions_used(argument) for argument in node[2]))
    return functions_used(node[1]) | (functions_used(node[2]) if node[0] == 'index' else set())


def _o_format(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f') + '0Z'


def _timestamp(value) -> datetime:
    if not isinstance(value, str):
        raise ExpressionError('timestamp must be a string')
    try:
        moment = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as error:
        raise ExpressionError(str(error)) from None
    if moment.tzinfo is None:
        raise ExpressionError('timestamp must carry a zone')
    return moment


def _text(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bool) or value is None:
        raise ExpressionError(f'no modelled string form for {value!r}')
    if isinstance(value, int):
        return str(value)
    return json.dumps(value, separators=(',', ':'), ensure_ascii=False)


def _require(value, kind, name):
    if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
        raise ExpressionError(f'{name} received {value!r}')
    return value


def _integer(value):
    if isinstance(value, str) and re.fullmatch(r'-?\d+', value):
        return int(value)
    return _require(value, int, 'int')


def _parse_json(value):
    if value is None:
        return {}
    try:
        return json.loads(_require(value, str, 'json'))
    except json.JSONDecodeError as error:
        raise ExpressionError(str(error)) from None


def _contains(collection, item):
    if isinstance(collection, str):
        return _require(item, str, 'contains') in collection
    if isinstance(collection, (list, dict)):
        return item in collection
    raise ExpressionError('contains needs a string, array or object')


def _length(value):
    return len(_require(value, (str, list), 'length'))


def _format(value, pattern):
    if pattern != 'yyyy-MM-ddTHH:mm:ss':
        raise AdfUnsupported(f'unmodelled format {pattern!r}')
    return _timestamp(value).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')


def _split(text, separator):
    if not _require(separator, str, 'split'):
        raise ExpressionError('split needs a separator')
    return _require(text, str, 'split').split(separator)


def _ticks(value):
    delta = _timestamp(value) - datetime(1, 1, 1, tzinfo=timezone.utc)
    return (delta.days * 86_400 + delta.seconds) * 10_000_000 + delta.microseconds * 10


def _folded(name):
    return lambda text, affix: getattr(_require(text, str, name).casefold(), name.lower())(
        _require(affix, str, name).casefold())


# Functions whose result depends only on their arguments. ADF documents startsWith and endsWith as
# case-insensitive and contains as case-sensitive; utcNow and addSeconds return the 'o' format.
PURE = {
    'concat': lambda *values: ''.join(_require(value, str, 'concat') for value in values),
    'not': lambda value: not _require(value, bool, 'not'),
    'add': lambda left, right: _require(left, int, 'add') + _require(right, int, 'add'),
    'max': lambda left, right: max(_require(left, int, 'max'), _require(right, int, 'max')),
    'less': lambda left, right: _require(left, int, 'less') < _require(right, int, 'less'),
    'greaterOrEquals': lambda left, right: _require(left, int, 'greaterOrEquals') >= _require(right, int, 'greaterOrEquals'),
    'string': _text,
    'int': _integer,
    'json': _parse_json,
    'contains': _contains,
    'coalesce': lambda *values: next((value for value in values if value is not None), None),
    'createArray': lambda *values: list(values),
    'addSeconds': lambda value, seconds: _o_format(_timestamp(value) + timedelta(seconds=_require(seconds, int, 'addSeconds'))),
    'ticks': _ticks,
    'startsWith': _folded('startsWith'),
    'endsWith': _folded('endsWith'),
    'toLower': lambda text: _require(text, str, 'toLower').lower(),
    'empty': lambda value: value is None or (isinstance(value, (str, list, dict)) and not value),
    'formatDateTime': _format,
    'split': _split,
    'length': _length,
}
# name -> (minimum, maximum) arity; None means unbounded
ARITY = {'concat': (1, None), 'equals': (2, 2), 'and': (2, 2), 'or': (2, 2), 'not': (1, 1), 'if': (3, 3),
         'add': (2, 2), 'max': (2, 2), 'less': (2, 2), 'greaterOrEquals': (2, 2), 'string': (1, 1),
         'int': (1, 1), 'json': (1, 1), 'contains': (2, 2), 'coalesce': (1, None), 'createArray': (2, None),
         'utcNow': (0, 0), 'addSeconds': (2, 2), 'ticks': (1, 1), 'startsWith': (2, 2), 'endsWith': (2, 2),
         'toLower': (1, 1), 'empty': (1, 1), 'formatDateTime': (2, 2), 'split': (2, 2), 'length': (1, 1),
         'variables': (1, 1), 'pipeline': (0, 0), 'activity': (1, 1)}
FUNCTIONS = frozenset(ARITY)


class Evaluator:
    def __init__(self, run: 'PipelineRun', scope: 'Scope'):
        self.run, self.scope, self.semantics = run, scope, run.semantics

    def value(self, value):
        """Evaluate a JSON value from an activity definition."""
        if isinstance(value, dict):
            if set(value) == {'value', 'type'} and value['type'] == 'Expression':
                return self.string(_require(value['value'], str, 'Expression value'))
            return {key: self.value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.value(item) for item in value]
        if isinstance(value, str):
            return self.string(value)
        return value

    def string(self, text: str):
        segments = _segments(text)
        if len(segments) == 1 and segments[0][0] == 'expression' and not segments[0][2]:
            return self.node(segments[0][1])
        if len(segments) == 1:
            return segments[0][1]
        return ''.join(item[1] if item[0] == 'literal' else _text(self.node(item[1])) for item in segments)

    def missing(self, what):
        if self.semantics.missing == 'throw':
            raise ExpressionError(f'missing {what}')
        return None

    def node(self, node):
        kind = node[0]
        if kind == 'literal':
            return node[1]
        if kind == 'property':
            base = self.node(node[1])
            if base is None:
                return self.missing(node[2])
            if not isinstance(base, dict):
                raise ExpressionError(f'property {node[2]!r} of a non-object')
            return base[node[2]] if node[2] in base else self.missing(node[2])
        if kind == 'index':
            base, key = self.node(node[1]), self.node(node[2])
            if base is None:
                return self.missing(key)
            if isinstance(base, list) and isinstance(key, int) and not isinstance(key, bool):
                return base[key] if 0 <= key < len(base) else self.missing(key)
            if isinstance(base, dict) and isinstance(key, str):
                return base[key] if key in base else self.missing(key)
            raise ExpressionError(f'cannot index {type(base).__name__} by {key!r}')
        return self.call(node[1], node[2])

    def call(self, name, arguments):
        if name not in ARITY:
            raise AdfUnsupported(f'function {name!r} is outside the subset')
        low, high = ARITY[name]
        if len(arguments) < low or (high is not None and len(arguments) > high):
            raise AdfUnsupported(f'{name} called with {len(arguments)} arguments')
        lazy = self.semantics.lazy
        if name == 'if':
            condition = _require(self.node(arguments[0]), bool, 'if')
            if lazy:
                return self.node(arguments[1] if condition else arguments[2])
            chosen, other = (arguments[1], arguments[2]) if condition else (arguments[2], arguments[1])
            self.node(other)
            return self.node(chosen)
        if name in ('and', 'or'):
            first = _require(self.node(arguments[0]), bool, name)
            if lazy and first == (name == 'or'):
                return first
            second = _require(self.node(arguments[1]), bool, name)
            return (first and second) if name == 'and' else (first or second)
        values = [self.node(argument) for argument in arguments]
        return PURE[name](*values) if name in PURE else getattr(self, '_' + name)(*values)

    def _equals(self, left, right):
        if isinstance(left, str) and isinstance(right, str) and self.semantics.equals_ignores_case:
            return left.casefold() == right.casefold()
        return isinstance(left, bool) == isinstance(right, bool) and left == right

    def _utcNow(self):
        return _o_format(self.run.clock)

    def _variables(self, name):
        if name not in self.run.variables:
            raise AdfUnsupported(f'undeclared variable {name!r}')
        return self.run.variables[name]

    def _pipeline(self):
        return {'parameters': self.run.parameters, 'RunId': self.run.run_id}

    def _activity(self, name):
        record = self.scope.lookup(name)
        if record is None:
            raise ExpressionError(f'activity {name!r} has not run in scope')
        return {'output': record['output']}


# ---------------------------------------------------------------- static checks

def walk_activities(activities, depth=()):
    """Every activity with the chain of container types above it."""
    for activity in activities:
        yield activity, depth
        for child_list in children(activity):
            yield from walk_activities(child_list, depth + (activity['type'],))


def children(activity):
    properties = activity.get('typeProperties', {})
    lists = [properties.get(key, []) for key in CONTAINERS.get(activity['type'], ())]
    if activity['type'] == 'Switch':
        lists.extend(case['activities'] for case in properties.get('cases', []))
    return lists


def expressions(activity):
    """(text, node) for every expression in an activity's own properties."""
    found = []

    def visit(value, key=None):
        if key in ('activities', 'ifTrueActivities', 'ifFalseActivities', 'defaultActivities'):
            return
        if isinstance(value, dict):
            if key == 'cases' or (activity['type'] == 'Switch' and set(value) == {'value', 'activities'}):
                return
            for name, item in value.items():
                visit(item, name)
        elif isinstance(value, list):
            for item in value:
                visit(item, key)
        elif isinstance(value, str):
            for segment in _segments(value):
                if segment[0] == 'expression':
                    found.append((value, segment[1]))

    visit(activity.get('typeProperties', {}))
    return found


def validate_pipeline(definition) -> None:
    """Raise AdfUnsupported where the definition leaves the subset or breaks a documented ADF rule."""
    activities = definition['activities']
    variables = definition.get('variables', {})
    for name, declaration in variables.items():
        if declaration.get('type') not in VARIABLE_TYPES:
            raise AdfUnsupported(f'variable {name!r} has an unsupported type')
    seen = set()
    total = 0
    for activity, depth in walk_activities(activities):
        total += 1
        name, kind = activity['name'], activity['type']
        if name in seen:
            raise AdfUnsupported(f'duplicate activity name {name!r}')
        seen.add(name)
        if kind not in ACTIVITY_TYPES:
            raise AdfUnsupported(f'activity type {kind!r} is outside the subset')
        if kind in ('IfCondition', 'Switch') and any(outer in ('IfCondition', 'Switch') for outer in depth):
            raise AdfUnsupported(f'{name!r}: If/Switch cannot nest inside If/Switch')
        if kind == 'Until' and 'Until' in depth:
            raise AdfUnsupported(f'{name!r}: Until allows one level of nesting')
        if kind == 'Switch':
            properties = activity['typeProperties']
            cases = properties.get('cases', [])
            if 'on' not in properties or not cases or len(cases) > MAX_CASES or 'defaultActivities' not in properties:
                raise AdfUnsupported(f'{name!r}: a Switch needs on, 1-25 cases and default activities')
            values = [case['value'] for case in cases]
            if len(set(values)) != len(values) or not all(isinstance(value, str) for value in values):
                raise AdfUnsupported(f'{name!r}: case values must be distinct strings')
        for text, node in expressions(activity):
            if len(text) > MAX_EXPRESSION:
                raise AdfUnsupported(f'{name!r} has an expression of {len(text)} characters')
            unknown = functions_used(node) - FUNCTIONS
            if unknown:
                raise AdfUnsupported(f'{name!r} uses {sorted(unknown)} in {text!r}')
            for found in re.findall(r"variables\('([^']*)'\)", text):
                if found not in variables:
                    raise AdfUnsupported(f'{name!r} reads undeclared variable {found!r}')
        if kind == 'SetVariable':
            target = activity['typeProperties']['variableName']
            if target not in variables:
                raise AdfUnsupported(f'{name!r} sets undeclared variable {target!r}')
            if f"variables('{target}')" in json.dumps(activity['typeProperties']['value']):
                raise AdfUnsupported(f'{name!r}: a Set Variable cannot reference its own variable')
    if total > MAX_ACTIVITIES:
        raise AdfUnsupported(f'{total} activities exceed the ADF limit of {MAX_ACTIVITIES}')
    if len(json.dumps(definition, separators=(',', ':')).encode()) > MAX_PIPELINE_BYTES:
        raise AdfUnsupported('the pipeline object exceeds the ADF limit of 200 KB')
    for container in [activities] + [child for activity, _ in walk_activities(activities)
                                     for child in children(activity)]:
        names = {activity['name'] for activity in container}
        outgoing: dict[str, set[str]] = {}
        for activity in container:
            for dependency in activity.get('dependsOn', []):
                source, conditions = dependency['activity'], set(dependency['dependencyConditions'])
                if source not in names:
                    raise AdfUnsupported(f"{activity['name']!r} depends on {source!r} outside its container")
                if not conditions or not conditions <= CONDITIONS:
                    raise AdfUnsupported(f"{activity['name']!r} has dependency conditions {sorted(conditions)}")
                outgoing.setdefault(source, set()).update(conditions)
        for source, conditions in outgoing.items():
            if 'Completed' in conditions and conditions & {'Succeeded', 'Failed'}:
                raise AdfUnsupported(f'{source!r}: an Upon Completion path cannot coexist with Success or Failure')


# ---------------------------------------------------------------- execution

@dataclass
class Request:
    method: str
    url: str
    headers: dict
    body: object
    resource: str | None
    at: datetime


@dataclass
class Response:
    status: int = 200
    body: object = field(default_factory=dict)
    headers: dict = field(default_factory=dict)


class Scope:
    def __init__(self, parent: 'Scope | None' = None):
        self.parent, self.records = parent, {}

    def lookup(self, name):
        scope = self
        while scope is not None:
            if name in scope.records:
                return scope.records[name]
            scope = scope.parent
        return None


def _timespan(text: str) -> timedelta:
    match = re.fullmatch(r'(?:(\d+)\.)?(\d{2}):(\d{2}):(\d{2})', text)
    if match is None:
        raise AdfUnsupported(f'timespan {text!r} is not d.hh:mm:ss')
    days, hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)


@dataclass
class Outcome:
    status: str
    failures: list
    variables: dict
    run_id: str


class PipelineRun:
    def __init__(self, pipelines: dict, web: Callable[[Request], Response], semantics: Semantics = Semantics(),
                 faults: frozenset = frozenset(), start: datetime = datetime(2026, 10, 12, 9, 0, tzinfo=timezone.utc),
                 max_iterations: int = 20_000):
        self.pipelines, self.web, self.semantics, self.faults = pipelines, web, semantics, frozenset(faults)
        self.clock, self.max_iterations, self.iterations = start, max_iterations, 0
        self.requests: list[Request] = []
        self.trace: list[tuple[str, str, object]] = []
        self.failures: list[dict] = []
        self.deadline: datetime | None = None
        self.runs = 0
        self.parameters: dict = {}
        self.variables: dict = {}
        self.declarations: dict = {}
        self.run_id = ''

    def run(self, name: str, parameters: dict) -> Outcome:
        definition = self.pipelines[name]
        declared = definition.get('parameters', {})
        if set(parameters) - set(declared):
            raise AdfUnsupported(f'undeclared parameters {sorted(set(parameters) - set(declared))}')
        values = {}
        for key, declaration in declared.items():
            if key in parameters:
                values[key] = parameters[key]
            elif 'defaultValue' in declaration:
                values[key] = declaration['defaultValue']
            else:
                raise AdfUnsupported(f'parameter {key!r} has no value')
        saved = (self.parameters, self.variables, self.declarations, self.run_id)
        self.runs += 1
        self.parameters = values
        self.declarations = definition.get('variables', {})
        self.variables = {key: declaration.get('defaultValue', [] if declaration['type'] == 'Array' else '')
                          for key, declaration in self.declarations.items()}
        self.run_id = f'00000000-0000-4000-8000-{self.runs:012d}'
        failures_before = len(self.failures)
        try:
            status = self.container(definition['activities'], Scope())
            return Outcome(status, self.failures[failures_before:], dict(self.variables), self.run_id)
        finally:
            self.parameters, self.variables, self.declarations, self.run_id = saved

    def container(self, activities, scope: Scope) -> str:
        statuses: dict[str, str] = {}
        pending = list(activities)
        while pending:
            for activity in pending:
                dependencies = activity.get('dependsOn', [])
                if all(item['activity'] in statuses for item in dependencies):
                    break
            else:
                raise AdfUnsupported('dependency cycle or unknown dependency')
            pending.remove(activity)
            if all(self.met(statuses[item['activity']], item['dependencyConditions']) for item in dependencies):
                statuses[activity['name']] = self.activity(activity, scope)
            else:
                statuses[activity['name']] = 'Skipped'
                self.trace.append((activity['name'], 'Skipped', None))
        return self.leaf_status(activities, statuses)

    @staticmethod
    def met(status, conditions):
        return any(condition == status or (condition == 'Completed' and status in ('Succeeded', 'Failed'))
                   for condition in conditions)

    @staticmethod
    def leaf_status(activities, statuses) -> str:
        """Pipeline result is success iff every evaluated leaf succeeds; a skipped leaf defers to its parents."""
        parents = {activity['name']: [item['activity'] for item in activity.get('dependsOn', [])]
                   for activity in activities}
        dependents = {source for names in parents.values() for source in names}
        evaluated, frontier = set(), [name for name in parents if name not in dependents]
        while frontier:
            name = frontier.pop()
            if statuses[name] == 'Skipped':
                frontier.extend(parents[name])
            else:
                evaluated.add(name)
        return 'Succeeded' if all(statuses[name] == 'Succeeded' for name in evaluated) else 'Failed'

    def tick(self, seconds: int = 1):
        if self.deadline is not None and self.clock + timedelta(seconds=seconds) > self.deadline:
            self.clock = self.deadline
            raise _Timeout()
        self.clock += timedelta(seconds=seconds)

    def activity(self, activity, scope: Scope) -> str:
        self.tick()
        name, kind = activity['name'], activity['type']
        output = None
        if name in self.faults:
            status = 'Failed'
        else:
            try:
                status, output = getattr(self, '_' + kind)(activity, scope)
            except (ExpressionError, WebFailure) as error:
                status, output = 'Failed', {'error': str(error)}
        scope.records[name] = {'status': status, 'output': output}
        self.trace.append((name, status, output))
        return status

    def evaluator(self, scope):
        return Evaluator(self, scope)

    def _SetVariable(self, activity, scope):
        properties = activity['typeProperties']
        name = properties['variableName']
        value = self.evaluator(scope).value(properties['value'])
        kind = VARIABLE_TYPES[self.declarations[name]['type']]
        if not isinstance(value, kind):
            raise ExpressionError(f'{name} is {kind.__name__}, not {value!r}')
        self.variables[name] = value
        return 'Succeeded', {'name': name, 'value': value}

    def _Wait(self, activity, scope):
        seconds = self.evaluator(scope).value(activity['typeProperties']['waitTimeInSeconds'])
        if not isinstance(seconds, int) or isinstance(seconds, bool) or seconds < 0:
            raise ExpressionError(f'wait of {seconds!r}')
        self.tick(seconds)
        return 'Succeeded', {}

    def _WebActivity(self, activity, scope):
        properties = activity['typeProperties']
        evaluate = self.evaluator(scope).value
        authentication = evaluate(properties.get('authentication', {}))
        request = Request(method=evaluate(properties['method']), url=evaluate(properties['url']),
                          headers=evaluate(properties.get('headers', {})),
                          body=evaluate(properties['body']) if 'body' in properties else None,
                          resource=authentication.get('resource') if authentication.get('type') == 'MSI' else None,
                          at=self.clock)
        self.requests.append(request)
        response = self.web(request)
        if response.status >= 400 or not isinstance(response.body, dict):
            raise WebFailure(f'{request.method} {request.url} gave {response.status}')
        return 'Succeeded', {**response.body, 'ADFWebActivityResponseHeaders': dict(response.headers)}

    def _Fail(self, activity, scope):
        evaluate = self.evaluator(scope).value
        properties = activity['typeProperties']
        code, message = evaluate(properties['errorCode']), evaluate(properties['message'])
        if not isinstance(code, str) or not code:
            code = 'ErrorCodeNotString'
        self.failures.append({'activity': activity['name'], 'errorCode': code, 'message': message})
        return 'Failed', {'errorCode': code, 'message': message}

    def _IfCondition(self, activity, scope):
        properties = activity['typeProperties']
        condition = self.evaluator(scope).value(properties['expression'])
        if not isinstance(condition, bool):
            raise ExpressionError('If needs a boolean')
        chosen = properties.get('ifTrueActivities' if condition else 'ifFalseActivities', [])
        return self.container(chosen, Scope(scope)), {}

    def _Switch(self, activity, scope):
        properties = activity['typeProperties']
        value = self.evaluator(scope).value(properties['on'])
        if not isinstance(value, str):
            raise ExpressionError('Switch needs a string')
        chosen = next((case['activities'] for case in properties['cases'] if case['value'] == value),
                      properties['defaultActivities'])
        return self.container(chosen, Scope(scope)), {}

    def _Until(self, activity, scope):
        properties = activity['typeProperties']
        outer = self.deadline
        own = self.clock + _timespan(properties.get('timeout', '7.00:00:00'))
        self.deadline = own if outer is None else min(outer, own)
        try:
            while True:
                self.iterations += 1
                if self.iterations > self.max_iterations:
                    raise AdfUnsupported('Until did not terminate within the iteration cap')
                status = self.container(properties['activities'], Scope(scope))
                done = self.evaluator(scope).value(properties['expression'])
                if not isinstance(done, bool):
                    raise ExpressionError('Until needs a boolean')
                if done:
                    return status, {}
        except _Timeout:
            if outer is not None and self.clock >= outer:
                raise
            return 'Failed', {'error': 'Until timed out'}
        finally:
            self.deadline = outer

    def _ExecutePipeline(self, activity, scope):
        properties = activity['typeProperties']
        if properties.get('waitOnCompletion') is not True:
            raise AdfUnsupported('only waitOnCompletion true is modelled')
        parameters = self.evaluator(scope).value(properties.get('parameters', {}))
        child = self.run(properties['pipeline']['referenceName'], parameters)
        return child.status, {'pipelineRunId': child.run_id}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_adf_interpreter -v`
Expected: PASS, 14 tests.

- [ ] **Step 5: Commit**

```bash
git add packages/sec-edgar-ingest/tests/adf_interpreter.py packages/sec-edgar-ingest/tests/test_adf_interpreter.py
git commit -m "test(infra): add a strict ADF pipeline interpreter for offline orchestration checks

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: The run-worker and caller pipelines

`pl-sec-edgar-run-worker` is one Until around a Switch on `phase`, followed by an If that fails the run unless `outcome` is `success`. The phases are `start`, `locate`, `observe`, `read` and `classify`. Each phase's first activity sets the conservative next phase, so a fault anywhere after it can only lead to classification. Launches are guarded twice:

- the Switch sends `start` to the refusing default case when the launch count has reached `maxLaunches`, or the previous launch is unclassified;
- only `classify` ever chooses `start`, and only for a `pending` outcome below the cap.

`outcome` is cleared before each start and is set only by a strict chain of Succeeded dependencies. A fault therefore leaves it empty, which is `execution_unknown`, or at its `result_mismatch` preset. It never leaves `success`. The three caller pipelines run run-worker with their command and their own run ID.

The scenario suite runs every §7.2 and §7.3 row under all eight semantics, including:

- every `EXIT_CODES` outcome under `Succeeded` and `Failed`;
- every invalid Location form;
- the deadline;
- the replay cap.

The fault suite fails each of the 47 activities in turn and checks four things:

- there are at most two starts;
- a second start follows only a classified `pending`;
- no fault turns a non-success into success;
- every Fail carries a non-empty error code.

**Files:**
- Create: `infra/azure/sec-edgar-ingest/pipelines/render.py`
- Create (rendered): `infra/azure/sec-edgar-ingest/pipelines/pl-sec-edgar-run-worker.json`, `pl-sec-edgar-backfill.json`, `pl-sec-edgar-daily.json`, `pl-sec-edgar-reconcile.json`
- Create: `tests/support_adf.py`
- Create: `tests/test_run_worker_pipeline.py`

**Interfaces:**
- Consumes:
  - Task 1's interpreter;
  - `results.EXIT_CODES`;
  - `cli._parser` (Plan 9's `--config-env` and optional `--execution-id`);
  - `RunContext`, `WorkflowResult` and `FORMAT_VERSION`.
- Produces:
  - `render.definitions() -> dict[str, dict]`, `render.rendered(definition) -> str` and `render.main()`.
  - The run-worker parameters, which main.bicep declares in Task 5. `support_adf.PARAMETER_TYPES` is their single list:
    - `command`, `runId`;
    - `containerName`, `imageRef`, `containerResources` (Object), `containerEnv` (Array);
    - `imageDigest`, `configSha256`, `jobPath`, `asyncPrefix`, `resultsUrl`;
    - `maxLaunches`, `pollSeconds`, `observeSeconds`, `workerSeconds` (Int).
  - `support_adf`:
    - `pipelines()`, `run_worker(launches, command, semantics, faults) -> WorkerRun`;
    - the scripting helpers `Launch`, `FakeAzure`, `started`, `accepted`, `operation` and `result`;
    - the constants `ABSENT`, `UNREADABLE`, `UNAVAILABLE`, `PIPELINES`, `IMAGE`, `ENV`, `RESOURCES`, `JOB` and `RUN_ID`.

- [ ] **Step 1: Write the scripted Azure**

`tests/support_adf.py`:

```python
"""Scripted Azure for the run-worker pipeline: every request must hit the exact host, route and audience."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from adf_interpreter import PipelineRun, Request, Response, Semantics, WebFailure

REPO = Path(__file__).resolve().parents[3]
PIPELINES = REPO / 'infra/azure/sec-edgar-ingest/pipelines'
SUBSCRIPTION = '3c92a216-8ed6-4897-b741-11ed287b8617'
JOB = (f'/subscriptions/{SUBSCRIPTION}/resourceGroups/rg-sec-edgar-dev-eastus'
       '/providers/Microsoft.App/jobs/job-sec-edgar-dev')
ARM = 'https://management.azure.com'
ARM_AUDIENCE = 'https://management.azure.com/'
STORAGE_AUDIENCE = 'https://storage.azure.com/'
ASYNC_PREFIX = f'{ARM}/subscriptions/{SUBSCRIPTION}/providers/Microsoft.App/locations/eastus/'
RESULTS = 'https://secedgardevb8617.blob.core.windows.net/results/runs/sec/'
DIGEST = 'sha256:' + '1' * 64
IMAGE = f'secedgardevb8617.azurecr.io/sec-edgar-ingest@{DIGEST}'
CONFIG_SHA256 = 'c' * 64
WORKER_CLIENT_ID = '11111111-2222-4333-8444-555555555555'
RESOURCES = {'cpu': 2, 'memory': '4Gi'}
ENV = [{'name': 'SEC_EDGAR_INGEST_WORKER_CLIENT_ID', 'value': WORKER_CLIENT_ID},
       {'name': 'SEC_EDGAR_INGEST_CONFIG', 'secretRef': 'ingest-config'}]
DEFAULTS = {'containerName': 'sec-edgar-ingest', 'imageRef': IMAGE, 'containerResources': RESOURCES,
            'containerEnv': ENV, 'imageDigest': DIGEST, 'configSha256': CONFIG_SHA256, 'jobPath': JOB,
            'asyncPrefix': ASYNC_PREFIX, 'resultsUrl': RESULTS, 'maxLaunches': 2, 'pollSeconds': 30,
            'observeSeconds': 4200, 'workerSeconds': 3300}
# Names and types match the parameters main.bicep declares on pl-sec-edgar-run-worker.
PARAMETER_TYPES = {'command': 'String', 'runId': 'String', 'containerName': 'String', 'imageRef': 'String',
                   'containerResources': 'Object', 'containerEnv': 'Array', 'imageDigest': 'String',
                   'configSha256': 'String', 'jobPath': 'String', 'asyncPrefix': 'String', 'resultsUrl': 'String',
                   'maxLaunches': 'Int', 'pollSeconds': 'Int', 'observeSeconds': 'Int', 'workerSeconds': 'Int'}
RUN_ID = '0f0e0d0c-0b0a-4908-8706-050403020100'
UNAVAILABLE = object()  # an execution GET that fails
ABSENT, UNREADABLE = object(), object()  # result blob states


def load(name: str) -> dict:
    return json.loads((PIPELINES / f'{name}.json').read_text())


def pipelines() -> dict:
    """The committed definitions, with run-worker's parameters declared as main.bicep declares them."""
    worker = load('pl-sec-edgar-run-worker')
    worker['parameters'] = {name: ({'type': kind, 'defaultValue': DEFAULTS[name]} if name in DEFAULTS
                                   else {'type': kind}) for name, kind in PARAMETER_TYPES.items()}
    return {'pl-sec-edgar-run-worker': worker,
            **{f'pl-sec-edgar-{command}': load(f'pl-sec-edgar-{command}')
               for command in ('backfill', 'daily', 'reconcile')}}


def execution_name(launch: int) -> str:
    return f'job-sec-edgar-dev-{launch:07d}'


def started(launch: int, **changes) -> Response:
    name = execution_name(launch)
    body = {'id': f'{JOB}/executions/{name}', 'name': name, **changes}
    return Response(200, {key: value for key, value in body.items() if value is not None})


def accepted(location: str | None = None, retry_after: str | None = '15', body=None) -> Response:
    headers = {}
    if location is not None:
        headers['Location'] = location
    if retry_after is not None:
        headers['Retry-After'] = retry_after
    return Response(202, {} if body is None else body, headers)


def operation(operation_id: str = 'op-1', route: str = 'containerappsjoboperationresults') -> str:
    return f'{ASYNC_PREFIX}{route}/{operation_id}?api-version=2026-07-01'


def result(command: str, launch: int, outcome: str, run_id: str = RUN_ID, context: dict | None = None) -> dict:
    """The fields of a worker result that the pipeline reads, matching launch `launch` unless `context` overrides."""
    return {'format_version': 'sec-workflow-result-v1', 'outcome': outcome, 'ended_at': '2026-10-12T09:30:00+00:00',
            'context': {'run_id': run_id, 'command': command, 'attempt_id': f'launch-{launch}',
                        'execution_id': execution_name(launch), 'image_digest': DIGEST,
                        'config_sha256': CONFIG_SHA256, **(context or {})}}


@dataclass
class Launch:
    """What Azure does with one start: its start response, Location polls, execution states and result."""
    outcome: object = 'success'          # a result outcome name, a result dict, ABSENT or UNREADABLE
    states: tuple = ('Succeeded',)       # successive execution GETs; the last repeats; UNAVAILABLE fails
    start: object = None                 # a Response or WebFailure; None is a 200 naming the execution
    locate: tuple = ()                   # successive Location GET responses; the last repeats
    image: str = IMAGE
    context: dict = field(default_factory=dict)
    retry_after: str | None = None       # Retry-After on execution GETs


class FakeAzure:
    def __init__(self, command: str, launches, run_id: str = RUN_ID):
        self.command, self.launches, self.run_id, self.posts = command, list(launches), run_id, 0
        self.polls = {'locate': 0, 'observe': 0}

    @property
    def current(self) -> Launch:
        return self.launches[self.posts - 1]

    def __call__(self, request: Request) -> Response:
        if request.method == 'POST':
            assert (request.url, request.resource) == (f'{ARM}{JOB}/start?api-version=2026-07-01', ARM_AUDIENCE), request
            assert request.headers == {'Content-Type': 'application/json'}, request.headers
            self.posts += 1
            assert self.posts <= len(self.launches), f'unscripted launch {self.posts}'
            self.polls = {'locate': 0, 'observe': 0}
            launch = self.current
            response = launch.start if launch.start is not None else started(self.posts)
            if isinstance(response, Exception):
                raise response
            return response
        assert request.method == 'GET' and self.posts, request
        launch, name = self.current, execution_name(self.posts)
        if request.url == f'{ARM}{JOB}/executions/{name}?api-version=2026-07-01':
            assert request.resource == ARM_AUDIENCE and request.headers == {}, request
            state = launch.states[min(self.polls['observe'], len(launch.states) - 1)]
            self.polls['observe'] += 1
            if state is UNAVAILABLE:
                raise WebFailure('execution GET unavailable')
            body = {'id': f'{JOB}/executions/{name}', 'name': name, 'properties': {
                'status': state, 'template': {'containers': [{'name': 'sec-edgar-ingest', 'image': launch.image}]}}}
            if state is None:
                del body['properties']['status']
            headers = {} if launch.retry_after is None else {'Retry-After': launch.retry_after}
            return Response(200, body, headers)
        start = launch.start
        if isinstance(start, Response) and request.url == start.headers.get('Location'):
            assert request.resource == ARM_AUDIENCE and request.headers == {}, request
            assert launch.locate, 'unscripted Location poll'
            response = launch.locate[min(self.polls['locate'], len(launch.locate) - 1)]
            self.polls['locate'] += 1
            if isinstance(response, Exception):
                raise response
            return response
        expected = f'{RESULTS}{self.run_id}/{self.command}/launch-{self.posts}/result.json'
        assert request.url == expected, f'unexpected request {request.method} {request.url}'
        assert request.resource == STORAGE_AUDIENCE and request.headers == {'x-ms-version': '2026-04-06'}, request
        if launch.outcome is ABSENT:
            raise WebFailure('404 BlobNotFound')
        if launch.outcome is UNREADABLE:
            return Response(200, 'not a JSON object')
        body = launch.outcome if isinstance(launch.outcome, dict) else result(
            self.command, self.posts, launch.outcome, self.run_id, launch.context)
        return Response(200, body, {'Content-Type': 'application/json'})


@dataclass
class WorkerRun:
    outcome: str            # 'success' or the Fail activity's error code
    status: str
    posts: int
    requests: list
    variables: dict
    trace: list
    failures: list


def run_worker(launches, command: str = 'daily', semantics: Semantics = Semantics(), faults=(),
               parameters=None) -> WorkerRun:
    azure = FakeAzure(command, launches)
    engine = PipelineRun(pipelines(), azure, semantics, frozenset(faults))
    outcome = engine.run('pl-sec-edgar-run-worker', {'command': command, 'runId': RUN_ID, **(parameters or {})})
    codes = [failure['errorCode'] for failure in outcome.failures]
    assert len(codes) <= 1, codes
    if outcome.status == 'Succeeded':
        assert not codes
    label = 'success' if outcome.status == 'Succeeded' else (codes[0] if codes else None)
    return WorkerRun(label, outcome.status, azure.posts, engine.requests, outcome.variables, engine.trace,
                     outcome.failures)
```

- [ ] **Step 2: Write the failing tests**

`tests/test_run_worker_pipeline.py`:

```python
"""The committed run-worker pipeline, run by the ADF interpreter against scripted Azure (spec §7, §10)."""
from network_guard import install
install()

import importlib.util
import unittest
from dataclasses import fields
from datetime import datetime, timedelta

from adf_interpreter import ALL_SEMANTICS, PipelineRun, Response, Semantics, WebFailure, validate_pipeline, walk_activities
from support_adf import (ABSENT, ARM_AUDIENCE, ASYNC_PREFIX, ENV, IMAGE, JOB, PIPELINES, RESOURCES, RUN_ID,
                         STORAGE_AUDIENCE, SUBSCRIPTION, UNAVAILABLE, UNREADABLE, FakeAzure, Launch, accepted,
                         execution_name, load, operation, pipelines, result, run_worker, started)
from sec_edgar_ingest.cli import _parser
from sec_edgar_ingest.models import RunContext
from sec_edgar_ingest.results import EXIT_CODES
from sec_edgar_ingest.workflows.contracts import FORMAT_VERSION, WorkflowResult


def expected_outcome(outcome: str, state: str) -> str:
    """Spec §7.3 for a matching result: what the pipeline must end with."""
    if EXIT_CODES[outcome] == 0:
        return 'success' if state == 'Succeeded' else 'result_mismatch'
    if EXIT_CODES[outcome] == 11:
        return 'stale'
    return outcome


SCENARIOS = {
    # §7.1 start responses
    'a 200 start is observed to success': ([Launch()], 'success', 1),
    'a failed start is unknown': ([Launch(start=WebFailure('timeout'))], 'execution_unknown', 1),
    'a refused start is unknown': ([Launch(start=Response(409, {'error': {'code': 'Conflict'}}))],
                                   'execution_unknown', 1),
    'a start naming another job is unknown': (
        [Launch(start=started(1, id=f'{JOB}-other/executions/{execution_name(1)}'))], 'execution_unknown', 1),
    'a start without a name is unknown': ([Launch(start=started(1, name=None))], 'execution_unknown', 1),
    'a start without an id is unknown': ([Launch(start=started(1, id=None))], 'execution_unknown', 1),
    'a start naming a nested path is unknown': (
        [Launch(start=started(1, name='a/b', id=f'{JOB}/executions/a/b'))], 'execution_unknown', 1),
    'a 202 without a Location is unknown': ([Launch(start=accepted())], 'execution_unknown', 1),
    'a 202 Location is followed to the execution': (
        [Launch(start=accepted(operation()), locate=(accepted(None, '10'), started(1)))], 'success', 1),
    'a 202 status-route Location is followed': (
        [Launch(start=accepted(operation(route='containerappsjoboperationstatuses')), locate=(started(1),))],
        'success', 1),
    'a failed Location poll keeps locating': (
        [Launch(start=accepted(operation()), locate=(WebFailure('503'), started(1)))], 'success', 1),
    'a Location that never names the execution is unknown': (
        [Launch(start=accepted(operation()), locate=(accepted(None),))], 'execution_unknown', 1),
    'a Location naming another job is unknown': (
        [Launch(start=accepted(operation()), locate=(started(1, id=f'{JOB}-other/executions/{execution_name(1)}'),))],
        'execution_unknown', 1),
    'an operation status is not an execution reference': (
        [Launch(start=accepted(operation()), locate=(Response(200, {
            'id': f'{ASYNC_PREFIX}containerappsjoboperationstatuses/op-1', 'name': 'op-1', 'status': 'Succeeded'}),))],
        'execution_unknown', 1),
    # §7.2 observation
    'running and processing keep polling': ([Launch(states=('Processing', 'Running', 'Running', 'Succeeded'))],
                                            'success', 1),
    'a failed GET keeps polling': ([Launch(states=(UNAVAILABLE, 'Running', UNAVAILABLE, 'Succeeded'))], 'success', 1),
    'a missing status keeps polling': ([Launch(states=(None, 'Succeeded'))], 'success', 1),
    'never terminal by the deadline is unknown': ([Launch(states=('Running',))], 'execution_unknown', 1),
    'every GET failing is unknown': ([Launch(states=(UNAVAILABLE,))], 'execution_unknown', 1),
    'degraded is unknown': ([Launch(states=('Running', 'Degraded'))], 'execution_unknown', 1),
    'unknown is unknown': ([Launch(states=('Unknown',))], 'execution_unknown', 1),
    'an unrecognized state is unknown': ([Launch(states=('Suspended',))], 'execution_unknown', 1),
    'stopped is stopped': ([Launch(states=('Running', 'Stopped'))], 'execution_stopped', 1),
    'another image is a mismatch': ([Launch(image=IMAGE.replace('1' * 64, '2' * 64))], 'execution_mismatch', 1),
    # §7.3 results
    'an absent result is missing': ([Launch(outcome=ABSENT)], 'result_missing', 1),
    'an unreadable result is missing': ([Launch(outcome=UNREADABLE)], 'result_missing', 1),
    'an absent result after Failed is missing': ([Launch(states=('Failed',), outcome=ABSENT)], 'result_missing', 1),
    'another format is a mismatch': ([Launch(outcome={**result('daily', 1, 'success'),
                                                      'format_version': 'sec-workflow-result-v2'})],
                                     'result_mismatch', 1),
    'an outcome outside EXIT_CODES is a mismatch': ([Launch(outcome='finished')], 'result_mismatch', 1),
    'a result without an outcome is a mismatch': (
        [Launch(outcome={key: value for key, value in result('daily', 1, 'success').items() if key != 'outcome'})],
        'result_mismatch', 1),
    'a result without a context is a mismatch': (
        [Launch(outcome={key: value for key, value in result('daily', 1, 'success').items() if key != 'context'})],
        'result_mismatch', 1),
    # §7.3 replay
    'pending relaunches once': ([Launch(outcome='pending'), Launch()], 'success', 2),
    'pending on a Failed execution relaunches': ([Launch(states=('Failed',), outcome='pending'), Launch()],
                                                 'success', 2),
    'pending at the replay cap stays pending': ([Launch(outcome='pending'), Launch(outcome='pending')], 'pending', 2),
    'a relaunch that cannot start is unknown': ([Launch(outcome='pending'), Launch(start=WebFailure('timeout'))],
                                                'execution_unknown', 2),
    'a relaunch is classified on its own result': ([Launch(outcome='pending'), Launch(outcome='awaiting_approval')],
                                                   'awaiting_approval', 2),
}
for field_name, wrong in (('run_id', 'another-run'), ('command', 'reconcile'), ('attempt_id', 'launch-2'),
                          ('execution_id', 'job-sec-edgar-dev-9999999'), ('image_digest', 'sha256:' + '2' * 64),
                          ('config_sha256', 'd' * 64)):
    SCENARIOS[f'a result with another {field_name} is a mismatch'] = (
        [Launch(context={field_name: wrong})], 'result_mismatch', 1)

INVALID_LOCATIONS = {
    'http': operation().replace('https://', 'http://'),
    'another host': operation().replace('management.azure.com', 'management.azure.com.example.net'),
    'userinfo': operation().replace('https://management.azure.com', 'https://management.azure.com@example.net'),
    'a port': operation().replace('management.azure.com', 'management.azure.com:8443'),
    'another subscription': operation().replace(SUBSCRIPTION, '00000000-0000-4000-8000-000000000000'),
    'another region': operation().replace('/locations/eastus/', '/locations/westus/'),
    'another route': operation(route='containerappsoperationresults'),
    'no API version': operation().split('?')[0],
    'another API version': operation().replace('2026-07-01', '2025-01-01'),
    'a preview API version': operation().replace('2026-07-01', '2026-07-01-preview'),
    'a fragment': operation() + '#x',
    'a second query': operation() + '?x=1',
    'a dot segment': operation('..'),
    'an encoded segment': operation('op%2F..%2Fx'),
    'an extra segment': operation('op-1/extra'),
    'no operation id': operation(''),
}


class RunWorkerScenarioTests(unittest.TestCase):
    def check(self, launches, expected, posts, command='daily'):
        for semantics in ALL_SEMANTICS:
            with self.subTest(semantics=semantics):
                run = run_worker(launches, command, semantics)
                self.assertEqual((run.outcome, run.posts), (expected, posts))
        return run

    def test_every_scenario_under_every_reading_of_the_documentation(self):
        for name, (launches, expected, posts) in SCENARIOS.items():
            with self.subTest(name):
                self.check(launches, expected, posts)

    def test_every_exit_code_outcome_is_classified_by_name(self):
        for outcome in EXIT_CODES:
            for state in ('Succeeded', 'Failed'):
                with self.subTest(outcome=outcome, state=state):
                    if outcome == 'pending':
                        self.check([Launch(states=(state,), outcome='pending'), Launch()], 'success', 2)
                    else:
                        self.check([Launch(states=(state,), outcome=outcome)], expected_outcome(outcome, state), 1)

    def test_an_invalid_location_is_never_requested(self):
        for label, location in INVALID_LOCATIONS.items():
            with self.subTest(label):
                run = self.check([Launch(start=accepted(location), locate=(started(1),))], 'execution_unknown', 1)
                self.assertEqual([request.method for request in run.requests], ['POST'])

    def test_unknown_starts_make_no_further_request(self):
        for launches in ([Launch(start=WebFailure('timeout'))], [Launch(start=started(1, name=None))]):
            run = self.check(launches, 'execution_unknown', 1)
            self.assertEqual([request.method for request in run.requests], ['POST'])

    def test_the_start_carries_the_job_container_and_the_launch_arguments(self):
        run = run_worker([Launch(outcome='pending'), Launch()])
        posts = [request for request in run.requests if request.method == 'POST']
        self.assertEqual(len(posts), 2)
        for launch, request in enumerate(posts, start=1):
            container, = request.body['containers']
            self.assertEqual({key: container[key] for key in ('name', 'image', 'resources', 'env')},
                             {'name': 'sec-edgar-ingest', 'image': IMAGE, 'resources': RESOURCES, 'env': ENV})
            arguments = _parser().parse_args(container['args'])
            self.assertEqual((arguments.command, arguments.config_env, arguments.config, arguments.run_id,
                              arguments.attempt_id, arguments.execution_id),
                             ('daily', 'SEC_EDGAR_INGEST_CONFIG', None, RUN_ID, f'launch-{launch}', None))
            deadline = datetime.fromisoformat(arguments.deadline)
            self.assertEqual(arguments.deadline, deadline.strftime('%Y-%m-%dT%H:%M:%SZ'))
            self.assertLessEqual(abs(deadline - (request.at + timedelta(seconds=3300))), timedelta(seconds=2))

    def test_polling_waits_thirty_seconds_or_a_longer_retry_after(self):
        for retry_after, low in ((None, 30), ('5', 30), ('120', 120), ('soon', 30)):
            with self.subTest(retry_after=retry_after):
                run = run_worker([Launch(states=('Running', 'Running', 'Succeeded'), retry_after=retry_after)])
                times = [request.at for request in run.requests if '/executions/' in request.url]
                gaps = [(later - earlier).total_seconds() for earlier, later in zip(times[1:], times[2:])]
                self.assertTrue(gaps and all(low <= gap < low + 15 for gap in gaps), gaps)
        run = run_worker([Launch(start=accepted(operation(), retry_after='90'), locate=(started(1),))])
        post, located = run.requests[0], run.requests[1]
        self.assertGreaterEqual((located.at - post.at).total_seconds(), 90)

    def test_observation_stops_at_the_deadline_and_never_cancels(self):
        run = run_worker([Launch(states=('Running',))])
        post, *gets = run.requests
        self.assertTrue(all(request.method == 'GET' and '/executions/' in request.url for request in gets))
        self.assertLess((gets[-1].at - post.at).total_seconds(), 4200 + 40)
        self.assertGreater((gets[-1].at - post.at).total_seconds(), 4200 - 40)
        self.assertNotIn('stop', ' '.join(request.url for request in run.requests))

    def test_the_callers_pass_their_run_id_and_command(self):
        for command in ('backfill', 'daily', 'reconcile'):
            for launch, expected in ((Launch(), 'Succeeded'), (Launch(outcome='awaiting_approval'), 'Failed')):
                with self.subTest(command=command, expected=expected):
                    caller_run_id = '00000000-0000-4000-8000-000000000001'
                    azure = FakeAzure(command, [launch], run_id=caller_run_id)
                    engine = PipelineRun(pipelines(), azure)
                    outcome = engine.run(f'pl-sec-edgar-{command}', {})
                    self.assertEqual((outcome.run_id, outcome.status, azure.posts), (caller_run_id, expected, 1))
                    arguments = engine.requests[0].body['containers'][0]['args']
                    self.assertEqual((arguments[0], arguments[arguments.index('--run-id') + 1]),
                                     (command, caller_run_id))


FAULT_BASES = {
    'success': lambda: [Launch()],
    'pending then success': lambda: [Launch(outcome='pending'), Launch()],
    'located': lambda: [Launch(start=accepted(operation()), locate=(started(1),))],
    'awaiting approval': lambda: [Launch(outcome='awaiting_approval')],
    'stopped': lambda: [Launch(states=('Stopped',))],
}


class RunWorkerFaultTests(unittest.TestCase):
    def test_a_fault_in_any_activity_never_relaunches_blindly_or_succeeds_falsely(self):
        names = [activity['name'] for activity, _ in walk_activities(load('pl-sec-edgar-run-worker')['activities'])]
        for base, launches in FAULT_BASES.items():
            clean = run_worker(launches())
            for name in names:
                for semantics in (Semantics(), Semantics('null', False, True)):
                    with self.subTest(base=base, fault=name, semantics=semantics):
                        run = run_worker(launches(), semantics=semantics, faults={name})
                        self.assertLessEqual(run.posts, 2)
                        if run.outcome == 'success':
                            self.assertEqual(clean.outcome, 'success')
                        for failure in run.failures:
                            self.assertNotIn(failure['errorCode'], ('', 'ErrorCodeNotString'))
                        if run.status == 'Failed' and name not in ('Check outcome', 'Fail run'):
                            self.assertEqual(len(run.failures), 1)
                        starts = [index for index, event in enumerate(run.trace)
                                  if event[:2] == ('Start job', 'Succeeded') or event[:2] == ('Start job', 'Failed')]
                        for second in starts[1:]:
                            classified = [event[2]['value'] for event in run.trace[:second]
                                          if event[:2] == ('Classify outcome', 'Succeeded')]
                            self.assertEqual(classified[-1:], ['pending'])


class RunWorkerDefinitionTests(unittest.TestCase):
    def test_the_committed_json_is_the_rendered_source(self):
        spec = importlib.util.spec_from_file_location('pipeline_render', PIPELINES / 'render.py')
        render = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(render)
        definitions = render.definitions()
        self.assertEqual(sorted(path.stem for path in PIPELINES.glob('*.json')), sorted(definitions))
        for name, definition in definitions.items():
            self.assertEqual((PIPELINES / f'{name}.json').read_text(), render.rendered(definition), name)

    def test_no_string_needs_arm_escaping(self):
        def strings(value):
            if isinstance(value, dict):
                return [item for child in value.values() for item in strings(child)]
            if isinstance(value, list):
                return [item for child in value for item in strings(child)]
            return [value] if isinstance(value, str) else []
        for name in pipelines():
            self.assertFalse([text for text in strings(load(name)) if text.startswith('[')], name)

    def test_the_definitions_stay_inside_the_modelled_subset(self):
        for name, definition in pipelines().items():
            with self.subTest(name):
                validate_pipeline(definition)

    def test_web_activities_never_retry_or_follow_async_and_use_their_audience(self):
        expected = {'Start job': ('POST', ARM_AUDIENCE), 'Get operation': ('GET', ARM_AUDIENCE),
                    'Get execution': ('GET', ARM_AUDIENCE), 'Get result': ('GET', STORAGE_AUDIENCE)}
        found = {}
        for activity, _ in walk_activities(load('pl-sec-edgar-run-worker')['activities']):
            if activity['type'] == 'WebActivity':
                properties = activity['typeProperties']
                self.assertEqual((activity['policy']['retry'], properties['turnOffAsync'],
                                  properties['httpRequestTimeout'], properties['authentication']['type']),
                                 (0, True, '00:01:00', 'MSI'))
                found[activity['name']] = (properties['method'], properties['authentication']['resource'])
        self.assertEqual(found, expected)

    def test_the_outcome_vocabularies_are_the_exit_code_table(self):
        variables = load('pl-sec-edgar-run-worker')['variables']
        self.assertEqual(variables['knownOutcomes']['defaultValue'], list(EXIT_CODES))
        self.assertEqual(variables['exitZeroOutcomes']['defaultValue'],
                         [name for name, code in EXIT_CODES.items() if code == 0])
        self.assertEqual(variables['staleOutcomes']['defaultValue'],
                         [name for name, code in EXIT_CODES.items() if code == 11])

    def test_the_result_fields_read_are_the_worker_result_contract(self):
        text = str(load('pl-sec-edgar-run-worker'))
        context = {field.name for field in fields(RunContext)}
        for name in ('run_id', 'command', 'attempt_id', 'execution_id', 'image_digest', 'config_sha256'):
            self.assertIn(f".context.{name}", text)
            self.assertIn(name, context)
        self.assertTrue({'format_version', 'context', 'outcome'} <= {field.name for field in fields(WorkflowResult)})
        self.assertIn(f"'{FORMAT_VERSION}'", text)

    def test_the_until_budget_covers_every_launch(self):
        until = load('pl-sec-edgar-run-worker')['activities'][0]
        self.assertEqual((until['type'], until['typeProperties']['timeout']), ('Until', '0.03:00:00'))
        self.assertGreaterEqual(3 * 3600, 2 * (4200 + 600))

    def test_the_callers_each_run_the_worker_with_their_command(self):
        for command in ('backfill', 'daily', 'reconcile'):
            activity, = load(f'pl-sec-edgar-{command}')['activities']
            self.assertEqual(activity['typeProperties'], {
                'pipeline': {'referenceName': 'pl-sec-edgar-run-worker', 'type': 'PipelineReference'},
                'waitOnCompletion': True,
                'parameters': {'command': command, 'runId': {'value': '@pipeline().RunId', 'type': 'Expression'}}})


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_run_worker_pipeline -v`
Expected: every test ERRORs with `FileNotFoundError` naming `infra/azure/sec-edgar-ingest/pipelines/pl-sec-edgar-run-worker.json` or `render.py`.

- [ ] **Step 4: Write the pipeline source**

`infra/azure/sec-edgar-ingest/pipelines/render.py`:

```python
"""Authoring source for the ADF pipeline JSON beside this file (spec §7). Offline; it calls nothing.

Run `uv run --offline --frozen --package sec-edgar-ingest python infra/azure/sec-edgar-ingest/pipelines/render.py`
after editing. The JSON it writes is what Bicep deploys and what the offline interpreter tests run; a test
fails when the two differ.
"""
from __future__ import annotations

import json
from pathlib import Path

from sec_edgar_ingest.results import EXIT_CODES

HERE = Path(__file__).resolve().parent
ARM = 'https://management.azure.com/'
STORAGE = 'https://storage.azure.com/'
WEB_POLICY = {'timeout': '0.00:10:00', 'retry': 0, 'retryIntervalInSeconds': 30, 'secureOutput': False,
              'secureInput': False}
COMMANDS = ('backfill', 'daily', 'reconcile')


def expression(text: str) -> dict:
    return {'value': text, 'type': 'Expression'}


def after(name: str, *conditions: str) -> dict:
    return {'activity': name, 'dependencyConditions': list(conditions or ('Succeeded',))}


def assign(name: str, variable: str, value: str, *depends: dict) -> dict:
    activity = {'name': name, 'type': 'SetVariable'}
    if depends:
        activity['dependsOn'] = list(depends)
    activity['typeProperties'] = {'variableName': variable,
                                  'value': expression(value) if value.startswith('@') else value}
    return activity


def web(name: str, method: str, url: str, resource: str, *depends: dict, headers=None, body=None) -> dict:
    properties = {'method': method, 'url': expression(url)}
    if headers is not None:
        properties['headers'] = headers
    if body is not None:
        properties['body'] = body
    properties.update({'httpRequestTimeout': '00:01:00', 'turnOffAsync': True,
                       'authentication': {'type': 'MSI', 'resource': resource}})
    return {'name': name, 'type': 'WebActivity', 'dependsOn': list(depends), 'policy': WEB_POLICY,
            'typeProperties': properties}


def wait(name: str, *depends: dict) -> dict:
    return {'name': name, 'type': 'Wait', 'dependsOn': list(depends),
            'typeProperties': {'waitTimeInSeconds': expression("@int(variables('waitSeconds'))")}}


BEFORE_DEADLINE = ("less(ticks(utcNow()), ticks(addSeconds(variables('launchedAt'), "
                   "pipeline().parameters.observeSeconds)))")
STATE = "variables('state')"
RESULT = "json(variables('result'))"
LOCATION = "activity('Start job').output.ADFWebActivityResponseHeaders['Location']"
LOCATION_PATH = f"split({LOCATION}, '?')[0]"
# §7.1: only an HTTPS management.azure.com Location on the selected async route, one operation segment,
# no dot or encoded segments, no fragment and exactly the selected API version.
LOCATION_VALID = (
    f"and(and(or(startsWith({LOCATION}, concat(pipeline().parameters.asyncPrefix, "
    f"'containerappsjoboperationresults/')), startsWith({LOCATION}, concat(pipeline().parameters.asyncPrefix, "
    f"'containerappsjoboperationstatuses/'))), equals(length(split({LOCATION}, '?')), 2)), "
    f"and(and(equals(length(split({LOCATION_PATH}, '/')), add(length(split(pipeline().parameters.asyncPrefix, "
    f"'/')), 1)), not(or(endsWith({LOCATION_PATH}, '/'), or(contains({LOCATION_PATH}, '..'), "
    f"contains({LOCATION_PATH}, '%'))))), and(not(contains({LOCATION}, '#')), "
    f"contains(split(split({LOCATION}, '?')[1], '&'), 'api-version=2026-07-01'))))")


def retry_after(activity: str) -> str:
    """D-18: the 30 s poll base, or a longer Retry-After. An absent or unreadable header fails the read."""
    return (f"@string(max(pipeline().parameters.pollSeconds, int(activity('{activity}')"
            ".output.ADFWebActivityResponseHeaders['Retry-After'])))")


def execution_reference(activity: str) -> tuple[str, str]:
    """A response names an execution only when its id is exactly that name under this job."""
    output = f"activity('{activity}').output"
    name = f'{output}.name'
    valid = (f"and(and(not(empty({name})), equals(toLower({output}.id), toLower(concat(pipeline().parameters.jobPath, "
             f"'/executions/', {name})))), and(not(or(contains({name}, '/'), contains({name}, '?'))), "
             f"not(or(contains({name}, '#'), contains({name}, '%')))))")
    return valid, name


START_VALID, START_NAME = execution_reference('Start job')
LOCATED_VALID, LOCATED_NAME = execution_reference('Get operation')

START_BODY = {'containers': [{
    'name': '@pipeline().parameters.containerName',
    'image': '@pipeline().parameters.imageRef',
    'resources': '@pipeline().parameters.containerResources',
    'env': '@pipeline().parameters.containerEnv',
    'args': ("@createArray(pipeline().parameters.command, '--config-env', 'SEC_EDGAR_INGEST_CONFIG', "
             "'--run-id', pipeline().parameters.runId, '--attempt-id', concat('launch-', variables('launch')), "
             "'--deadline', concat(formatDateTime(addSeconds(variables('launchedAt'), "
             "pipeline().parameters.workerSeconds), 'yyyy-MM-ddTHH:mm:ss'), 'Z'))"),
}]}

# Each phase first sets the conservative next phase; a fault anywhere after it can only end in
# classification, never in another launch.
START = [
    assign('Start begins', 'nextPhase', 'classify'),
    assign('Count launch', 'nextLaunch', "@string(add(int(variables('launch')), 1))", after('Start begins')),
    assign('Set launch', 'launch', "@variables('nextLaunch')", after('Count launch')),
    assign('Clear outcome', 'outcome', '', after('Set launch')),
    assign('Clear execution name', 'executionName', '', after('Clear outcome')),
    assign('Clear location', 'location', '', after('Clear execution name')),
    assign('Clear state', 'state', '', after('Clear location')),
    assign('Clear image', 'image', '', after('Clear state')),
    assign('Clear result', 'result', '', after('Clear image')),
    assign('Set start wait', 'waitSeconds', '@string(pipeline().parameters.pollSeconds)', after('Clear result')),
    assign('Stamp launch', 'launchedAt', '@utcNow()', after('Set start wait')),
    web('Start job', 'POST',
        "@concat('https://management.azure.com', pipeline().parameters.jobPath, '/start?api-version=2026-07-01')",
        ARM, after('Stamp launch'), headers={'Content-Type': 'application/json'}, body=START_BODY),
    assign('Read start wait', 'waitSeconds', retry_after('Start job'), after('Start job')),
    assign('Read start location', 'location', f"@if({LOCATION_VALID}, {LOCATION}, '')",
           after('Read start wait', 'Completed')),
    assign('Read start name', 'executionName', f"@if(and(empty(variables('location')), {START_VALID}), {START_NAME}, '')",
           after('Read start location', 'Completed')),
    assign('After start', 'nextPhase', "@if(not(empty(variables('executionName'))), 'observe', "
                                       "if(empty(variables('location')), 'classify', 'locate'))",
           after('Read start name', 'Completed')),
]

LOCATE = [
    assign('Locate begins', 'nextPhase', 'classify'),
    wait('Wait to locate', after('Locate begins')),
    assign('Reset locate wait', 'waitSeconds', '@string(pipeline().parameters.pollSeconds)', after('Wait to locate')),
    web('Get operation', 'GET', "@variables('location')", ARM, after('Reset locate wait')),
    assign('Read locate wait', 'waitSeconds', retry_after('Get operation'), after('Get operation')),
    assign('Read located name', 'executionName', f"@if({LOCATED_VALID}, {LOCATED_NAME}, '')",
           after('Read locate wait', 'Completed')),
    assign('After locate', 'nextPhase', f"@if(not(empty(variables('executionName'))), 'observe', "
                                        f"if({BEFORE_DEADLINE}, 'locate', 'classify'))",
           after('Wait to locate'), after('Read located name', 'Completed', 'Skipped')),
]

OBSERVE = [
    assign('Observe begins', 'nextPhase', 'classify'),
    wait('Wait to observe', after('Observe begins')),
    assign('Reset observe wait', 'waitSeconds', '@string(pipeline().parameters.pollSeconds)', after('Wait to observe')),
    web('Get execution', 'GET', "@concat('https://management.azure.com', pipeline().parameters.jobPath, "
                                "'/executions/', variables('executionName'), '?api-version=2026-07-01')",
        ARM, after('Reset observe wait')),
    assign('Read observe wait', 'waitSeconds', retry_after('Get execution'), after('Get execution')),
    assign('Read state', 'state', "@activity('Get execution').output.properties.status",
           after('Read observe wait', 'Completed')),
    assign('Read image', 'image', "@activity('Get execution').output.properties.template.containers[0].image",
           after('Read state', 'Completed')),
    assign('After observe', 'nextPhase',
           f"@if(or(equals({STATE}, 'Succeeded'), equals({STATE}, 'Failed')), 'read', "
           f"if(and(or(empty({STATE}), or(equals({STATE}, 'Running'), equals({STATE}, 'Processing'))), "
           f"{BEFORE_DEADLINE}), 'observe', 'classify'))",
           after('Wait to observe'), after('Read image', 'Completed', 'Skipped')),
]

READ = [
    assign('Read begins', 'nextPhase', 'classify'),
    web('Get result', 'GET', "@concat(pipeline().parameters.resultsUrl, pipeline().parameters.runId, '/', "
                             "pipeline().parameters.command, '/launch-', variables('launch'), '/result.json')",
        STORAGE, after('Read begins'), headers={'x-ms-version': '2026-04-06'}),
    assign('Keep result', 'result', "@string(activity('Get result').output)", after('Get result')),
]

# §7.3. The execution decides first; a result is read only when the execution allows it. Any fault
# leaves `outcome` empty (execution_unknown) or `resultOutcome` at its result_mismatch preset.
CLASSIFY = [
    assign('Classify begins', 'nextPhase', 'done'),
    assign('Classify execution', 'executionOutcome',
           f"@if(not(or(or(equals({STATE}, 'Succeeded'), equals({STATE}, 'Failed')), equals({STATE}, 'Stopped'))), "
           f"'execution_unknown', if(equals({STATE}, 'Stopped'), 'execution_stopped', "
           f"if(not(equals(variables('image'), pipeline().parameters.imageRef)), 'execution_mismatch', "
           f"if(empty(variables('result')), 'result_missing', ''))))",
           after('Classify begins')),
    assign('Preset result outcome', 'resultOutcome', 'result_mismatch', after('Classify execution')),
    assign('Classify result', 'resultOutcome',
           f"@if(and(and(and(equals({RESULT}.format_version, 'sec-workflow-result-v1'), "
           f"equals({RESULT}.context.run_id, pipeline().parameters.runId)), "
           f"and(equals({RESULT}.context.command, pipeline().parameters.command), "
           f"equals({RESULT}.context.attempt_id, concat('launch-', variables('launch'))))), "
           f"and(and(equals({RESULT}.context.execution_id, variables('executionName')), "
           f"equals({RESULT}.context.image_digest, pipeline().parameters.imageDigest)), "
           f"and(equals({RESULT}.context.config_sha256, pipeline().parameters.configSha256), "
           f"contains(variables('knownOutcomes'), {RESULT}.outcome)))), "
           f"if(contains(variables('exitZeroOutcomes'), {RESULT}.outcome), "
           f"if(equals({STATE}, 'Succeeded'), 'success', 'result_mismatch'), "
           f"if(contains(variables('staleOutcomes'), {RESULT}.outcome), 'stale', {RESULT}.outcome)), "
           f"'result_mismatch')",
           after('Preset result outcome')),
    assign('Classify outcome', 'outcome', "@if(empty(variables('executionOutcome')), variables('resultOutcome'), "
                                          "variables('executionOutcome'))",
           after('Classify result', 'Completed')),
    assign('Mark classified', 'classified', "@variables('launch')", after('Classify outcome')),
    assign('Classify next', 'nextPhase', "@if(and(equals(variables('outcome'), 'pending'), "
                                         "less(int(variables('launch')), pipeline().parameters.maxLaunches)), "
                                         "'start', 'done')",
           after('Mark classified')),
]

# A launch starts only from 'start', within the cap, and only once the previous launch is classified.
PHASE = ("@if(and(equals(variables('phase'), 'start'), or(greaterOrEquals(int(variables('launch')), "
         "pipeline().parameters.maxLaunches), not(equals(variables('launch'), variables('classified'))))), "
         "'refuse', variables('phase'))")
OUTCOME_CODE = "if(empty(variables('outcome')), 'execution_unknown', variables('outcome'))"
STRING_VARIABLES = (('phase', 'start'), ('nextPhase', ''), ('launch', '0'), ('nextLaunch', '0'), ('classified', '0'),
                    ('launchedAt', ''), ('executionName', ''), ('location', ''), ('state', ''), ('image', ''),
                    ('waitSeconds', ''), ('result', ''), ('executionOutcome', ''), ('resultOutcome', ''),
                    ('outcome', ''))


def run_worker() -> dict:
    """pl-sec-edgar-run-worker without its parameters, which main.bicep declares with their defaults."""
    phases = {'name': 'Launch phase', 'type': 'Switch', 'typeProperties': {
        'on': expression(PHASE),
        'cases': [{'value': 'start', 'activities': START}, {'value': 'locate', 'activities': LOCATE},
                  {'value': 'observe', 'activities': OBSERVE}, {'value': 'read', 'activities': READ},
                  {'value': 'classify', 'activities': CLASSIFY}],
        'defaultActivities': [assign('Stop launches', 'nextPhase', 'done')]}}
    return {
        'activities': [
            {'name': 'Run launches', 'type': 'Until', 'typeProperties': {
                'expression': expression("@equals(variables('phase'), 'done')"),
                'timeout': '0.03:00:00',
                'activities': [phases, assign('Advance', 'phase', "@variables('nextPhase')",
                                              after('Launch phase', 'Completed'))]}},
            {'name': 'Check outcome', 'type': 'IfCondition', 'dependsOn': [after('Run launches', 'Completed')],
             'typeProperties': {
                 'expression': expression("@equals(variables('outcome'), 'success')"),
                 'ifTrueActivities': [],
                 'ifFalseActivities': [{'name': 'Fail run', 'type': 'Fail', 'typeProperties': {
                     'message': expression(f"@concat('pl-sec-edgar-run-worker ', pipeline().parameters.command, "
                                           f"' launch-', variables('launch'), ' ended ', {OUTCOME_CODE})"),
                     'errorCode': expression(f'@{OUTCOME_CODE}')}}]}},
        ],
        'variables': {
            **{name: {'type': 'String', 'defaultValue': default} for name, default in STRING_VARIABLES},
            'knownOutcomes': {'type': 'Array', 'defaultValue': list(EXIT_CODES)},
            'exitZeroOutcomes': {'type': 'Array', 'defaultValue': [name for name, code in EXIT_CODES.items() if code == 0]},
            'staleOutcomes': {'type': 'Array', 'defaultValue': [name for name, code in EXIT_CODES.items() if code == 11]},
        },
    }


def caller(command: str) -> dict:
    return {'activities': [{'name': 'Run worker', 'type': 'ExecutePipeline', 'typeProperties': {
        'pipeline': {'referenceName': 'pl-sec-edgar-run-worker', 'type': 'PipelineReference'},
        'waitOnCompletion': True,
        'parameters': {'command': command, 'runId': expression('@pipeline().RunId')}}}]}


def definitions() -> dict[str, dict]:
    return {'pl-sec-edgar-run-worker': run_worker(), **{f'pl-sec-edgar-{command}': caller(command) for command in COMMANDS}}


def rendered(definition: dict) -> str:
    return json.dumps(definition, indent=2) + '\n'


def main() -> None:
    for name, definition in definitions().items():
        (HERE / f'{name}.json').write_text(rendered(definition))


if __name__ == '__main__':
    main()
```

- [ ] **Step 5: Render the JSON**

Run: `uv run --offline --frozen --package sec-edgar-ingest python infra/azure/sec-edgar-ingest/pipelines/render.py && wc -l infra/azure/sec-edgar-ingest/pipelines/*.json`
Expected: run-worker 1,006 lines, and each caller 22 lines.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_run_worker_pipeline -v`
Expected: PASS, 17 tests, in about 10 s. Then run `test_adf_interpreter` again: PASS.

- [ ] **Step 7: Commit**

```bash
git add infra/azure/sec-edgar-ingest/pipelines packages/sec-edgar-ingest/tests/support_adf.py packages/sec-edgar-ingest/tests/test_run_worker_pipeline.py
git commit -m "feat(infra): add the run-worker and caller pipelines with offline scenario and fault suites

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Spec amendment — the start-body assumption

This task applies only if the owner approves it at plan review (Settled item 4). If the owner declines, drop the task. Nothing else changes: the start body is the same, and Stage 7 then proves it only within the existing S7-06 start receipts.

**Files:**
- Modify: `specs/sec-filing-index-ingestion-stage-6-spec.md` (§11, "Assumptions Stage 6 adds to the Stage 7 checks"; the status line is untouched)

- [ ] **Step 1: Apply the amendment**

Replace:

```text
- S7-06: an override's `env` `secretRef` resolves against the job's secrets (§4).
```

with:

```text
- S7-06: an override's `env` `secretRef` resolves against the job's secrets (§4).
- S7-06: ADF evaluates the nested expressions in the start body's container to native values. Any other evaluation cannot yield a matching result, so the pipeline ends in a non-success outcome and never relaunches (§7.3). (owner, plan 10, 2026-10-12)
```

- [ ] **Step 2: Commit**

```bash
git add specs/sec-filing-index-ingestion-stage-6-spec.md
git commit -m "docs(specs): record the start-body evaluation as a Stage 7 assumption

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Bicep, the role matrix and the shared resources

**Files:**
- Create: `infra/azure/sec-edgar-ingest/roles.json`
- Create: `infra/azure/sec-edgar-ingest/main.bicep`
- Create: `infra/azure/sec-edgar-ingest/modules/identities.bicep`, `registry.bicep`, `monitoring.bicep`, `storage.bicep`
- Create (compiled): `infra/azure/sec-edgar-ingest/main.json`
- Create: `tests/support_template.py`, `tests/test_azure_roles.py`, `tests/test_azure_template.py`

**Interfaces:**
- Consumes: `support_adf.PARAMETER_TYPES` (Task 2).
- Produces:
  - `roles.json` with:
    - `definitions`, each `{roleName, description, actions, dataActions}`;
    - `builtins` (`AcrPull` only);
    - `assignments`, each `{principal, role, scope}`. The principal is `adf`, `worker`, `pull` or `operator`. The scope is `job`, `registry`, `subscription`, `container:<name>` or `table:<name>`.
  - main.bicep's variables `names`, `containers`, `tables`, `roles`, `roleIds`, `config` and `registryServer`.
  - The modules `identities` (outputs `workerId`, `workerClientId`, `workerPrincipalId`, `pullId`, `pullPrincipalId`), `registry`, `monitoring` (outputs `workspaceId`, `actionGroupId`) and `storage`.
  - `support_template`: `INFRA`, `REPO`, `CONTAINERS`, `TABLES`, `load`, `template`, `nodes`, `resources`, `deployment`, `module` and `text`.

- [ ] **Step 1: Install Bicep 0.38.33 (D1)**

These commands are tool installs only. They do not log in, select a subscription or call Azure management.

```bash
AZURE_CORE_COLLECT_TELEMETRY=false az version --query '"azure-cli"' -o tsv
AZURE_CORE_COLLECT_TELEMETRY=false az bicep install --version v0.38.33
~/.azure/bin/bicep --version
```

Expected: `2.90.0`, then the install, then `Bicep CLI version 0.38.33 (…)`. If the CLI is not 2.90.0, or the Bicep version differs, stop and report: both are F1 pins.

- [ ] **Step 2: Write the failing role-matrix test**

`tests/test_azure_roles.py`:

```python
"""roles.json is the spec §5 role matrix, exactly; the template deploys only what it lists."""
from network_guard import install
install()

import unittest

from support_template import CONTAINERS, TABLES, load

B = 'Microsoft.Storage/storageAccounts/blobServices/containers/blobs'
T = 'Microsoft.Storage/storageAccounts/tableServices/tables/entities'
ROLES = {
    'SecEdgar Job Controller': ({'Microsoft.App/jobs/read', 'Microsoft.App/jobs/start/action',
                                 'Microsoft.App/jobs/execution/read', 'Microsoft.App/jobs/executions/read'}, set()),
    'SecEdgar Job Async Observer': ({'Microsoft.App/locations/containerappsjoboperationresults/read',
                                     'Microsoft.App/locations/containerappsjoboperationstatuses/read'}, set()),
    'SecEdgar Blob Reader': (set(), {f'{B}/read'}),
    'SecEdgar Blob Writer': (set(), {f'{B}/read', f'{B}/write'}),
    'SecEdgar Entity Reader': (set(), {f'{T}/read'}),
    'SecEdgar Entity Writer': (set(), {f'{T}/read', f'{T}/add/action', f'{T}/update/action'}),
}


def grants(principal, role, *scopes):
    return {(principal, role, scope) for scope in scopes}


GRANTS = (grants('adf', 'SecEdgar Job Controller', 'job')
          | grants('adf', 'SecEdgar Job Async Observer', 'subscription')
          | grants('adf', 'SecEdgar Blob Reader', 'container:results')
          | grants('worker', 'SecEdgar Blob Writer', *(f'container:{name}' for name in (
              'raw', 'worksets', 'results', 'quarantine', 'generations', 'manifests', 'locks')))
          | grants('worker', 'SecEdgar Blob Reader', 'container:approvals')
          | grants('worker', 'SecEdgar Entity Writer', 'table:SourceState', 'table:Attempts', 'table:ActivePointers')
          | grants('worker', 'SecEdgar Entity Reader', 'table:Approvals')
          | grants('pull', 'AcrPull', 'registry')
          | grants('operator', 'SecEdgar Blob Reader', *(f'container:{name}' for name in (
              'locks', 'worksets', 'generations', 'manifests', 'approvals')))
          | grants('operator', 'SecEdgar Blob Writer', 'container:approvals')
          | grants('operator', 'SecEdgar Entity Reader', 'table:SourceState')
          | grants('operator', 'SecEdgar Entity Writer', 'table:ActivePointers', 'table:Approvals'))


class RoleMatrixTests(unittest.TestCase):
    def setUp(self):
        self.roles = load('roles.json')

    def test_custom_roles_carry_only_the_listed_permissions(self):
        found = {role['roleName']: (set(role['actions']), set(role['dataActions'])) for role in self.roles['definitions']}
        self.assertEqual(found, ROLES)
        for role in self.roles['definitions']:
            self.assertEqual(len(role['actions']) + len(role['dataActions']),
                             len(set(role['actions'])) + len(set(role['dataActions'])))
            self.assertTrue(role['description'])

    def test_the_only_built_in_role_is_acr_pull(self):
        self.assertEqual(self.roles['builtins'], {'AcrPull': '7f951dda-4ed3-4680-a7ca-43fe172d538d'})

    def test_assignments_are_the_principal_table(self):
        listed = [(item['principal'], item['role'], item['scope']) for item in self.roles['assignments']]
        self.assertEqual(len(listed), len(set(listed)))
        self.assertEqual(set(listed), GRANTS)
        self.assertTrue(all(set(item) == {'principal', 'role', 'scope'} for item in self.roles['assignments']))

    def test_every_scope_key_is_one_the_template_handles(self):
        handled = {'job', 'registry', 'subscription', *(f'container:{name}' for name in CONTAINERS),
                   *(f'table:{name}' for name in TABLES)}
        self.assertLessEqual({item['scope'] for item in self.roles['assignments']}, handled)

    def test_the_worker_never_writes_approvals(self):
        writes = {(role, scope) for principal, role, scope in GRANTS if principal == 'worker'}
        self.assertNotIn(('SecEdgar Blob Writer', 'container:approvals'), writes)
        self.assertNotIn(('SecEdgar Entity Writer', 'table:Approvals'), writes)

    def test_no_wildcard_or_secret_listing_permission(self):
        for role in self.roles['definitions']:
            for permission in role['actions'] + role['dataActions']:
                self.assertNotIn('*', permission)
                self.assertNotRegex(permission.lower(), r'list(keys|secrets|credentials)')


if __name__ == '__main__':
    unittest.main()
```

`tests/support_template.py`:

```python
"""Read the committed infrastructure definitions with the stdlib alone (spec §10)."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
INFRA = REPO / 'infra/azure/sec-edgar-ingest'
CONTAINERS = ('raw', 'worksets', 'quarantine', 'locks', 'results', 'generations', 'manifests', 'approvals')
TABLES = ('SourceState', 'Attempts', 'ActivePointers', 'Approvals')


def load(relative: str):
    return json.loads((INFRA / relative).read_text())


def template() -> dict:
    return load('main.json')


def nodes(value):
    """Every JSON object in a value, depth first."""
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from nodes(item)
    elif isinstance(value, list):
        for item in value:
            yield from nodes(item)


def resources(value, kind: str | None = None) -> list[dict]:
    """ARM resources anywhere in the tree, nested deployments included, whether Bicep lists or keys them."""
    return [node for node in nodes(value) if isinstance(node.get('type'), str) and 'apiVersion' in node
            and (kind is None or node['type'] == kind)]


def deployment(value, name: str) -> dict:
    found = [node for node in resources(value, 'Microsoft.Resources/deployments') if node.get('name') == name]
    assert len(found) == 1, (name, len(found))
    return found[0]


def module(value, name: str) -> dict:
    """The compiled template of the module deployed under `name`."""
    return deployment(value, name)['properties']['template']


def text(value) -> str:
    return json.dumps(value, sort_keys=True)
```

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_azure_roles -v`
Expected: ERROR, `FileNotFoundError` for `roles.json`.

- [ ] **Step 3: Write the role matrix**

`infra/azure/sec-edgar-ingest/roles.json` lists the spec §5 tables. `B` and `T` are written out in full:

```json
{
  "definitions": [
    {
      "roleName": "SecEdgar Job Controller",
      "description": "Start and read the sec-edgar-ingest job and its executions.",
      "actions": [
        "Microsoft.App/jobs/read",
        "Microsoft.App/jobs/start/action",
        "Microsoft.App/jobs/execution/read",
        "Microsoft.App/jobs/executions/read"
      ],
      "dataActions": []
    },
    {
      "roleName": "SecEdgar Job Async Observer",
      "description": "Read Container Apps job start operations for the sec-edgar-ingest job.",
      "actions": [
        "Microsoft.App/locations/containerappsjoboperationresults/read",
        "Microsoft.App/locations/containerappsjoboperationstatuses/read"
      ],
      "dataActions": []
    },
    {
      "roleName": "SecEdgar Blob Reader",
      "description": "Read blobs in one sec-edgar-ingest container.",
      "actions": [],
      "dataActions": [
        "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read"
      ]
    },
    {
      "roleName": "SecEdgar Blob Writer",
      "description": "Read and write blobs in one sec-edgar-ingest container.",
      "actions": [],
      "dataActions": [
        "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
        "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write"
      ]
    },
    {
      "roleName": "SecEdgar Entity Reader",
      "description": "Read entities in one sec-edgar-ingest table.",
      "actions": [],
      "dataActions": [
        "Microsoft.Storage/storageAccounts/tableServices/tables/entities/read"
      ]
    },
    {
      "roleName": "SecEdgar Entity Writer",
      "description": "Read, add and update entities in one sec-edgar-ingest table.",
      "actions": [],
      "dataActions": [
        "Microsoft.Storage/storageAccounts/tableServices/tables/entities/read",
        "Microsoft.Storage/storageAccounts/tableServices/tables/entities/add/action",
        "Microsoft.Storage/storageAccounts/tableServices/tables/entities/update/action"
      ]
    }
  ],
  "builtins": {
    "AcrPull": "7f951dda-4ed3-4680-a7ca-43fe172d538d"
  },
  "assignments": [
    {"principal": "adf", "role": "SecEdgar Job Controller", "scope": "job"},
    {"principal": "adf", "role": "SecEdgar Job Async Observer", "scope": "subscription"},
    {"principal": "adf", "role": "SecEdgar Blob Reader", "scope": "container:results"},
    {"principal": "worker", "role": "SecEdgar Blob Writer", "scope": "container:raw"},
    {"principal": "worker", "role": "SecEdgar Blob Writer", "scope": "container:worksets"},
    {"principal": "worker", "role": "SecEdgar Blob Writer", "scope": "container:results"},
    {"principal": "worker", "role": "SecEdgar Blob Writer", "scope": "container:quarantine"},
    {"principal": "worker", "role": "SecEdgar Blob Writer", "scope": "container:generations"},
    {"principal": "worker", "role": "SecEdgar Blob Writer", "scope": "container:manifests"},
    {"principal": "worker", "role": "SecEdgar Blob Writer", "scope": "container:locks"},
    {"principal": "worker", "role": "SecEdgar Blob Reader", "scope": "container:approvals"},
    {"principal": "worker", "role": "SecEdgar Entity Writer", "scope": "table:SourceState"},
    {"principal": "worker", "role": "SecEdgar Entity Writer", "scope": "table:Attempts"},
    {"principal": "worker", "role": "SecEdgar Entity Writer", "scope": "table:ActivePointers"},
    {"principal": "worker", "role": "SecEdgar Entity Reader", "scope": "table:Approvals"},
    {"principal": "pull", "role": "AcrPull", "scope": "registry"},
    {"principal": "operator", "role": "SecEdgar Blob Reader", "scope": "container:locks"},
    {"principal": "operator", "role": "SecEdgar Blob Reader", "scope": "container:worksets"},
    {"principal": "operator", "role": "SecEdgar Blob Reader", "scope": "container:generations"},
    {"principal": "operator", "role": "SecEdgar Blob Reader", "scope": "container:manifests"},
    {"principal": "operator", "role": "SecEdgar Blob Reader", "scope": "container:approvals"},
    {"principal": "operator", "role": "SecEdgar Blob Writer", "scope": "container:approvals"},
    {"principal": "operator", "role": "SecEdgar Entity Reader", "scope": "table:SourceState"},
    {"principal": "operator", "role": "SecEdgar Entity Writer", "scope": "table:ActivePointers"},
    {"principal": "operator", "role": "SecEdgar Entity Writer", "scope": "table:Approvals"}
  ]
}
```

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_azure_roles -v`
Expected: PASS, 6 tests.

- [ ] **Step 4: Write the failing template tests**

`tests/test_azure_template.py`; Tasks 5 and 6 add classes to it:

```python
"""The committed compiled template (main.json) deploys exactly the spec §5 and §9 definitions (spec §10)."""
from network_guard import install
install()

import json
import re
import unittest

from support_adf import PARAMETER_TYPES
from support_template import CONTAINERS, INFRA, TABLES, deployment, load, module, nodes, resources, template, text

API_VERSIONS = {
    'Microsoft.Resources/resourceGroups': '2024-03-01',
    'Microsoft.Authorization/roleDefinitions': '2022-04-01',
    'Microsoft.Authorization/roleAssignments': '2022-04-01',
    'Microsoft.ManagedIdentity/userAssignedIdentities': '2024-11-30',
    'Microsoft.ContainerRegistry/registries': '2025-11-01',
    'Microsoft.OperationalInsights/workspaces': '2025-07-01',
    'Microsoft.Insights/actionGroups': '2023-01-01',
    'Microsoft.Insights/diagnosticSettings': '2021-05-01-preview',
    'Microsoft.Insights/scheduledQueryRules': '2023-12-01',
    'Microsoft.Storage/storageAccounts': '2025-06-01',
    'Microsoft.Storage/storageAccounts/blobServices': '2025-06-01',
    'Microsoft.Storage/storageAccounts/blobServices/containers': '2025-06-01',
    'Microsoft.Storage/storageAccounts/tableServices': '2025-06-01',
    'Microsoft.Storage/storageAccounts/tableServices/tables': '2025-06-01',
    'Microsoft.App/managedEnvironments': '2026-07-01',
    'Microsoft.App/jobs': '2026-07-01',
    'Microsoft.DataFactory/factories': '2018-06-01',
    'Microsoft.DataFactory/factories/pipelines': '2018-06-01',
    'Microsoft.DataFactory/factories/triggers': '2018-06-01',
}
NAMES = {'group': 'rg-sec-edgar-dev-eastus', 'environment': 'cae-sec-edgar-dev-eastus', 'job': 'job-sec-edgar-dev',
         'factory': 'adf-sec-edgar-dev', 'workspace': 'law-sec-edgar-dev', 'actionGroup': 'ag-sec-edgar-dev',
         'storage': 'secedgardevb8617', 'registry': 'secedgardevb8617', 'worker': 'id-sec-edgar-dev-worker',
         'pull': 'id-sec-edgar-dev-pull'}
AZURE_CONFIG = INFRA / 'config/sec-edgar-ingest.azure.template.json'


def named(value, kind: str, name: str) -> dict:
    """The one resource of `kind` whose (possibly expression) name mentions `name`."""
    found = [resource for resource in resources(value, kind) if f"'{name}'" in resource['name'] or resource['name'] == name]
    assert len(found) == 1, (kind, name, len(found))
    return found[0]


class SharedResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = template()

    def test_parameters_have_no_defaults_except_the_region(self):
        parameters = self.template['parameters']
        self.assertEqual(set(parameters), {'location', 'configJson', 'configSha256', 'operatorPrincipalId',
                                           'dailyStartTime', 'reconcileStartTime'})
        self.assertEqual((parameters['location']['defaultValue'], parameters['location']['allowedValues']),
                         ('eastus', ['eastus', 'eastus2', 'centralus']))
        for name in set(parameters) - {'location'}:
            self.assertEqual(parameters[name]['type'], 'string', name)
            self.assertNotIn('defaultValue', parameters[name], name)
        self.assertEqual((parameters['configSha256']['minLength'], parameters['configSha256']['maxLength']), (64, 64))
        for name in ('dailyStartTime', 'reconcileStartTime'):
            # yyyy-MM-ddTHH:mm:ss is 19 characters; a trailing Z, an offset or fractions cannot fit.
            self.assertEqual((parameters[name]['minLength'], parameters[name]['maxLength']), (19, 19))

    def test_every_resource_uses_its_selected_api_version(self):
        for resource in resources(self.template):
            if resource['type'] != 'Microsoft.Resources/deployments':
                self.assertEqual(resource['apiVersion'], API_VERSIONS.get(resource['type']), resource['type'])

    def test_names_collections_and_roles_are_the_committed_ones(self):
        variables = self.template['variables']
        self.assertEqual(variables['names'], NAMES)
        self.assertEqual((variables['containers'], variables['tables']), (list(CONTAINERS), list(TABLES)))
        self.assertEqual(variables['roles'], load('roles.json'))
        group, = resources(self.template, 'Microsoft.Resources/resourceGroups')
        self.assertEqual(group['name'], "[variables('names').group]")

    def test_custom_roles_come_from_roles_json_at_subscription_scope(self):
        definition, = resources(self.template, 'Microsoft.Authorization/roleDefinitions')
        self.assertEqual(definition['copy']['count'], "[length(variables('roles').definitions)]")
        properties = definition['properties']
        self.assertEqual((properties['type'], properties['assignableScopes']), ('CustomRole', ['[subscription().id]']))
        permissions, = properties['permissions']
        self.assertEqual((permissions['notActions'], permissions['notDataActions']), ([], []))
        self.assertIn("variables('roles').definitions[copyIndex()]", text(properties))

    def test_storage_is_entra_only_hns_zrs_with_the_spec_containers_and_tables(self):
        storage = module(self.template, 'storage')
        account, = resources(storage, 'Microsoft.Storage/storageAccounts')
        self.assertEqual((account['kind'], account['sku']), ('StorageV2', {'name': 'Standard_ZRS'}))
        self.assertEqual(account['properties'], {
            'accessTier': 'Hot', 'isHnsEnabled': True, 'allowBlobPublicAccess': False, 'allowSharedKeyAccess': False,
            'defaultToOAuthAuthentication': True, 'minimumTlsVersion': 'TLS1_2', 'publicNetworkAccess': 'Enabled',
            'supportsHttpsTrafficOnly': True})
        parameters = deployment(self.template, 'storage')['properties']['parameters']
        self.assertEqual((parameters['containers'], parameters['tables']),
                         ({'value': "[variables('containers')]"}, {'value': "[variables('tables')]"}))
        container, = resources(storage, 'Microsoft.Storage/storageAccounts/blobServices/containers')
        self.assertEqual(container['properties'], {'publicAccess': 'None'})
        self.assertEqual(container['copy']['count'], "[length(parameters('containers'))]")
        table, = resources(storage, 'Microsoft.Storage/storageAccounts/tableServices/tables')
        self.assertEqual(table['copy']['count'], "[length(parameters('tables'))]")

    def test_registry_is_basic_classic_rbac_with_arm_token_pulls(self):
        registry, = resources(module(self.template, 'registry'), 'Microsoft.ContainerRegistry/registries')
        self.assertEqual(registry['sku'], {'name': 'Basic'})
        self.assertEqual(registry['properties'], {
            'adminUserEnabled': False, 'anonymousPullEnabled': False, 'publicNetworkAccess': 'Enabled',
            'roleAssignmentMode': 'LegacyRegistryPermissions',
            'policies': {'azureADAuthenticationAsArmPolicy': {'status': 'enabled'}}})

    def test_monitoring_keeps_ninety_days_and_mails_the_operator(self):
        monitoring = module(self.template, 'monitoring')
        workspace, = resources(monitoring, 'Microsoft.OperationalInsights/workspaces')
        self.assertEqual(workspace['properties'], {'sku': {'name': 'PerGB2018'}, 'retentionInDays': 90})
        group, = resources(monitoring, 'Microsoft.Insights/actionGroups')
        self.assertEqual(group['location'], 'Global')
        receiver, = group['properties']['emailReceivers']
        self.assertEqual(receiver, {'name': 'operator', 'emailAddress': "[parameters('email')]",
                                    'useCommonAlertSchema': True})
        self.assertEqual(deployment(self.template, 'monitoring')['properties']['parameters']['email'],
                         {'value': 'mason.lowell@mac.com'})

    def test_two_user_assigned_identities(self):
        identities = module(self.template, 'identities')
        self.assertEqual(len(resources(identities, 'Microsoft.ManagedIdentity/userAssignedIdentities')), 2)
        parameters = deployment(self.template, 'identities')['properties']['parameters']
        self.assertEqual((parameters['workerName'], parameters['pullName']),
                         ({'value': "[variables('names').worker]"}, {'value': "[variables('names').pull]"}))


if __name__ == '__main__':
    unittest.main()
```

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_azure_template -v`
Expected: ERROR in `setUpClass`, `FileNotFoundError` for `main.json`.

- [ ] **Step 5: Write main.bicep and the shared modules**

`infra/azure/sec-edgar-ingest/main.bicep`; Tasks 5–7 append to it:

```bicep
// Stage 6 deployment definition (spec §9). Subscription scope: the resource group and the custom roles;
// every other resource lives in a resource-group module. Nothing here starts a trigger or a job.
targetScope = 'subscription'

@description('Region for every regional resource, in F1 region order.')
@allowed([
  'eastus'
  'eastus2'
  'centralus'
])
param location string = 'eastus'

@description('Canonical Azure config rendered by python -m sec_edgar_ingest.deployment (spec §4).')
param configJson string

@description('config_sha256 of configJson, from the same render.')
@minLength(64)
@maxLength(64)
param configSha256 string

@description('Entra object ID of the operator, Lowell Mason (spec §5).')
param operatorPrincipalId string

@description('First daily trigger time: Eastern local yyyy-MM-ddTHH:mm:ss, without Z (spec §7.4).')
@minLength(19)
@maxLength(19)
param dailyStartTime string

@description('First reconciliation trigger time: Eastern local yyyy-MM-ddTHH:mm:ss, without Z (spec §7.4).')
@minLength(19)
@maxLength(19)
param reconcileStartTime string

// F1 D-02 and D-03.
var names = {
  group: 'rg-sec-edgar-dev-eastus'
  environment: 'cae-sec-edgar-dev-eastus'
  job: 'job-sec-edgar-dev'
  factory: 'adf-sec-edgar-dev'
  workspace: 'law-sec-edgar-dev'
  actionGroup: 'ag-sec-edgar-dev'
  storage: 'secedgardevb8617'
  registry: 'secedgardevb8617'
  worker: 'id-sec-edgar-dev-worker'
  pull: 'id-sec-edgar-dev-pull'
}
var containers = [
  'raw'
  'worksets'
  'quarantine'
  'locks'
  'results'
  'generations'
  'manifests'
  'approvals'
]
var tables = [
  'SourceState'
  'Attempts'
  'ActivePointers'
  'Approvals'
]
var roles = loadJsonContent('roles.json')
var roleIds = union(toObject(roles.definitions, role => role.roleName, role => guid(subscription().id, role.roleName)), roles.builtins)
var config = json(configJson)
var registryServer = '${names.registry}.azurecr.io'

resource group 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: names.group
  location: location
}

resource roleDefinitions 'Microsoft.Authorization/roleDefinitions@2022-04-01' = [for role in roles.definitions: {
  name: guid(subscription().id, role.roleName)
  properties: {
    roleName: role.roleName
    description: role.description
    type: 'CustomRole'
    permissions: [
      {
        actions: role.actions
        notActions: []
        dataActions: role.dataActions
        notDataActions: []
      }
    ]
    assignableScopes: [
      subscription().id
    ]
  }
}]

module identities 'modules/identities.bicep' = {
  name: 'identities'
  scope: group
  params: {
    location: location
    workerName: names.worker
    pullName: names.pull
  }
}

module registry 'modules/registry.bicep' = {
  name: 'registry'
  scope: group
  params: {
    location: location
    name: names.registry
  }
}

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  scope: group
  params: {
    location: location
    workspaceName: names.workspace
    actionGroupName: names.actionGroup
    email: 'mason.lowell@mac.com'
  }
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  scope: group
  params: {
    location: location
    name: names.storage
    containers: containers
    tables: tables
  }
}
```

`infra/azure/sec-edgar-ingest/modules/identities.bicep`:

```bicep
// The worker identity (storage access) and the pull identity (registry access only) (spec §5).
param location string
param workerName string
param pullName string

resource worker 'Microsoft.ManagedIdentity/userAssignedIdentities@2024-11-30' = {
  name: workerName
  location: location
}

resource pull 'Microsoft.ManagedIdentity/userAssignedIdentities@2024-11-30' = {
  name: pullName
  location: location
}

output workerId string = worker.id
output workerClientId string = worker.properties.clientId
output workerPrincipalId string = worker.properties.principalId
output pullId string = pull.id
output pullPrincipalId string = pull.properties.principalId
```

`infra/azure/sec-edgar-ingest/modules/registry.bicep`:

```bicep
// F1 D-05/D-06: dedicated Basic registry, classic RBAC, ARM-token authentication for managed-identity pulls.
param location string
param name string

resource registry 'Microsoft.ContainerRegistry/registries@2025-11-01' = {
  name: name
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
    anonymousPullEnabled: false
    publicNetworkAccess: 'Enabled'
    roleAssignmentMode: 'LegacyRegistryPermissions'
    policies: {
      azureADAuthenticationAsArmPolicy: {
        status: 'enabled'
      }
    }
  }
}
```

`infra/azure/sec-edgar-ingest/modules/monitoring.bicep`:

```bicep
// The workspace every log lands in and the action group every alert notifies (spec §8).
param location string
param workspaceName string
param actionGroupName string
param email string

resource workspace 'Microsoft.OperationalInsights/workspaces@2025-07-01' = {
  name: workspaceName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 90
  }
}

resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: actionGroupName
  location: 'Global'
  properties: {
    groupShortName: 'secedgar'
    enabled: true
    emailReceivers: [
      {
        name: 'operator'
        emailAddress: email
        useCommonAlertSchema: true
      }
    ]
  }
}

output workspaceId string = workspace.id
output actionGroupId string = actionGroup.id
```

`infra/azure/sec-edgar-ingest/modules/storage.bicep`:

```bicep
// One HNS StorageV2 account; Entra-only access over public HTTPS (spec §9).
param location string
param name string
param containers array
param tables array

resource account 'Microsoft.Storage/storageAccounts@2025-06-01' = {
  name: name
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_ZRS'
  }
  properties: {
    accessTier: 'Hot'
    isHnsEnabled: true
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Enabled'
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2025-06-01' = {
  parent: account
  name: 'default'
}

resource blobContainers 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = [for container in containers: {
  parent: blobService
  name: container
  properties: {
    publicAccess: 'None'
  }
}]

resource tableService 'Microsoft.Storage/storageAccounts/tableServices@2025-06-01' = {
  parent: account
  name: 'default'
}

resource accountTables 'Microsoft.Storage/storageAccounts/tableServices/tables@2025-06-01' = [for table in tables: {
  parent: tableService
  name: table
}]
```

- [ ] **Step 6: Compile**

Run: `~/.azure/bin/bicep build infra/azure/sec-edgar-ingest/main.bicep --outfile infra/azure/sec-edgar-ingest/main.json`

Expected: exit 0. Warnings are allowed; list each one in the task report. The expected warnings are:

- unused parameters, until Tasks 5–6 use them;
- `no-hardcoded-env-urls`;
- `BCP081`, if this Bicep build carries no type for one of the F1 API versions.

Any error stops the task: fix the Bicep, not the test.

- [ ] **Step 7: Run the tests to verify they pass**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_azure_template -v`
Expected: PASS, 8 tests.

The template tests were written before Bicep could be run (D1). An assertion may fail only because Bicep 0.38.33 emits an equivalent shape: a resource keyed by symbolic name, or an expression spelled differently. In that case:

- change only the locator, or the expected expression string, to the emitted one;
- keep what the assertion requires;
- record a one-line deviation in the task report.

If the compiled meaning is wrong, fix the Bicep.

- [ ] **Step 8: Commit**

```bash
git add infra/azure/sec-edgar-ingest/roles.json infra/azure/sec-edgar-ingest/main.bicep infra/azure/sec-edgar-ingest/main.json infra/azure/sec-edgar-ingest/modules packages/sec-edgar-ingest/tests/support_template.py packages/sec-edgar-ingest/tests/test_azure_roles.py packages/sec-edgar-ingest/tests/test_azure_template.py
git commit -m "feat(infra): add the role matrix, shared Azure resources and the compiled template

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: The job, the factory, its pipelines and stopped triggers

One `container` object in main.bicep is both the job's container and the defaults of the run-worker container parameters. The start override can therefore differ from the job only by its arguments (spec §7.1). The job image derives from the config's digest, so the image and the config cannot disagree (spec §4).

**Files:**
- Create: `infra/azure/sec-edgar-ingest/modules/job.bicep`, `modules/factory.bicep`
- Modify: `infra/azure/sec-edgar-ingest/main.bicep` (append), `main.json` (recompile)
- Modify: `tests/test_azure_template.py` (add `JobAndFactoryTests`)

**Interfaces:**
- Consumes:
  - Task 2's pipeline JSON, loaded with `loadJsonContent`;
  - Task 4's `identities` and `monitoring` outputs;
  - Plan 9's config template (`jobs.replica_retry_limit`, `orchestration.transient_replays`).
- Produces:
  - the modules `job` (output `jobId`) and `factory` (output `principalId`);
  - the triggers `tr-sec-edgar-daily` and `tr-sec-edgar-reconcile`.

- [ ] **Step 1: Write the failing tests**

Add this class to `tests/test_azure_template.py`, above `if __name__ == '__main__':`:

```python
class JobAndFactoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = template()
        cls.factory = module(cls.template, 'factory')
        cls.config = json.loads(AZURE_CONFIG.read_text())

    def test_the_job_is_manual_with_the_accepted_values_and_no_volumes(self):
        job_module = module(self.template, 'job')
        job, = resources(job_module, 'Microsoft.App/jobs')
        configuration = job['properties']['configuration']
        self.assertEqual(set(configuration), {'triggerType', 'replicaTimeout', 'replicaRetryLimit',
                                              'manualTriggerConfig', 'secrets', 'registries'})
        self.assertEqual((configuration['triggerType'], configuration['replicaTimeout'],
                          configuration['replicaRetryLimit'], configuration['manualTriggerConfig']),
                         ('Manual', 3600, self.config['jobs']['replica_retry_limit'],
                          {'parallelism': 1, 'replicaCompletionCount': 1}))
        self.assertEqual(configuration['secrets'], [{'name': 'ingest-config', 'value': "[parameters('configJson')]"}])
        self.assertEqual(configuration['registries'], [{'server': "[parameters('registryServer')]",
                                                        'identity': "[parameters('pullIdentityId')]"}])
        self.assertEqual(job['properties']['template'], {'containers': ["[parameters('container')]"]})
        self.assertEqual((job['identity']['type'], len(job['identity']['userAssignedIdentities'])), ('UserAssigned', 2))
        self.assertEqual(job['properties']['workloadProfileName'], 'Consumption')
        self.assertNotIn('volume', text(job_module).lower())
        environment, = resources(job_module, 'Microsoft.App/managedEnvironments')
        self.assertEqual(environment['properties'], {
            'appLogsConfiguration': {'destination': 'azure-monitor'},
            'workloadProfiles': [{'name': 'Consumption', 'workloadProfileType': 'Consumption'}]})

    def test_the_start_override_is_the_job_container(self):
        job_container = deployment(self.template, 'job')['properties']['parameters']['container']
        self.assertEqual(deployment(self.template, 'factory')['properties']['parameters']['container'], job_container)
        value = job_container['value']
        self.assertEqual((value['name'], value['resources']), ('sec-edgar-ingest', {'cpu': 2, 'memory': '4Gi'}))
        self.assertEqual(value['env'][1], {'name': 'SEC_EDGAR_INGEST_CONFIG', 'secretRef': 'ingest-config'})
        self.assertEqual(value['env'][0]['name'], 'SEC_EDGAR_INGEST_WORKER_CLIENT_ID')
        self.assertIn('workerClientId', value['env'][0]['value'])
        self.assertEqual(len(value['env']), 2)
        self.assertIn('sec-edgar-ingest@', value['image'])
        self.assertIn('worker.image_digest', value['image'])
        self.assertEqual(self.template['variables']['registryServer'], "[format('{0}.azurecr.io', variables('names').registry)]")
        worker = named(self.factory, 'Microsoft.DataFactory/factories/pipelines', 'pl-sec-edgar-run-worker')
        defaults = {name: declaration.get('defaultValue') for name, declaration in worker['properties']['parameters'].items()}
        for parameter, key in (('containerName', 'name'), ('imageRef', 'image'), ('containerResources', 'resources'),
                               ('containerEnv', 'env')):
            self.assertEqual(defaults[parameter], f"[parameters('container').{key}]")

    def test_run_worker_is_the_committed_json_with_the_declared_parameters(self):
        worker = named(self.factory, 'Microsoft.DataFactory/factories/pipelines', 'pl-sec-edgar-run-worker')
        parameters = worker['properties']['parameters']
        self.assertEqual({name: declaration['type'] for name, declaration in parameters.items()}, PARAMETER_TYPES)
        self.assertEqual({name: parameters[name].get('defaultValue') for name in
                          ('command', 'runId', 'pollSeconds', 'observeSeconds', 'workerSeconds')},
                         {'command': None, 'runId': None, 'pollSeconds': 30, 'observeSeconds': 4200, 'workerSeconds': 3300})
        everything = list(nodes(self.template))
        self.assertIn(load('pipelines/pl-sec-edgar-run-worker.json'), everything)
        for command in ('backfill', 'daily', 'reconcile'):
            self.assertIn(load(f'pipelines/pl-sec-edgar-{command}.json'), everything)
        passed = deployment(self.template, 'factory')['properties']['parameters']
        self.assertEqual(passed['configSha256'], {'value': "[parameters('configSha256')]"})
        for name, fragments in (('imageDigest', ('worker.image_digest',)), ('maxLaunches', ('transient_replays',)),
                                ('jobPath', ('jobId',)), ('resultsUrl', ('blob_endpoint', '/results/runs/sec/')),
                                ('asyncPrefix', ('https://management.azure.com/subscriptions/',
                                                 '/providers/Microsoft.App/locations/'))):
            for fragment in fragments:
                self.assertIn(fragment, passed[name]['value'], name)
        self.assertEqual(1 + self.config['orchestration']['transient_replays'], 2)

    def test_triggers_are_the_eastern_recurrences_and_deploy_stopped(self):
        expected = {
            'tr-sec-edgar-daily': ('pl-sec-edgar-daily', {'frequency': 'Day', 'interval': 1,
                                   'startTime': "[parameters('dailyStartTime')]", 'timeZone': 'Eastern Standard Time',
                                   'schedule': {'hours': [5], 'minutes': [0]}}),
            'tr-sec-edgar-reconcile': ('pl-sec-edgar-reconcile', {'frequency': 'Week', 'interval': 1,
                                       'startTime': "[parameters('reconcileStartTime')]",
                                       'timeZone': 'Eastern Standard Time',
                                       'schedule': {'weekDays': ['Sunday'], 'hours': [6], 'minutes': [0]}}),
        }
        self.assertEqual(len(resources(self.factory, 'Microsoft.DataFactory/factories/triggers')), 2)
        for name, (pipeline, recurrence) in expected.items():
            trigger = named(self.factory, 'Microsoft.DataFactory/factories/triggers', name)
            self.assertEqual(trigger['properties'], {
                'type': 'ScheduleTrigger',
                'pipelines': [{'pipelineReference': {'referenceName': pipeline, 'type': 'PipelineReference'}}],
                'typeProperties': {'recurrence': recurrence}})
        body = text(self.template)
        self.assertNotIn('runtimeState', body)
        self.assertFalse([resource for resource in resources(self.template) if 'deploymentScripts' in resource['type']])
        passed = deployment(self.template, 'factory')['properties']['parameters']
        self.assertEqual((passed['dailyStartTime'], passed['reconcileStartTime']),
                         ({'value': "[parameters('dailyStartTime')]"}, {'value': "[parameters('reconcileStartTime')]"}))

    def test_job_and_factory_logs_go_to_the_workspace_as_resource_specific_tables(self):
        expected = {'job': ['ContainerAppConsoleLogs', 'ContainerAppSystemLogs'],
                    'factory': ['ActivityRuns', 'PipelineRuns', 'TriggerRuns']}
        for name, categories in expected.items():
            setting, = resources(module(self.template, name), 'Microsoft.Insights/diagnosticSettings')
            self.assertEqual(setting['properties'], {
                'workspaceId': "[parameters('workspaceId')]", 'logAnalyticsDestinationType': 'Dedicated',
                'logs': [{'category': category, 'enabled': True} for category in categories]})
        factory, = resources(self.factory, 'Microsoft.DataFactory/factories')
        self.assertEqual(factory['identity'], {'type': 'SystemAssigned'})
```

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_azure_template.JobAndFactoryTests -v`
Expected: ERROR in `setUpClass`, `AssertionError: ('factory', 0)`.

- [ ] **Step 2: Write the job and factory modules**

`infra/azure/sec-edgar-ingest/modules/job.bicep`:

```bicep
// The Manual job and its Consumption environment (spec §2, §4, §9). It has no schedule and no volumes; the
// config reaches the container only as the ingest-config secret.
param location string
param environmentName string
param jobName string
param workspaceId string

@description('The job container; ADF starts it with the same container plus arguments.')
param container object

@description('Canonical config, stored as the ingest-config secret.')
param configJson string

param workerIdentityId string
param pullIdentityId string
param registryServer string

resource managedEnvironment 'Microsoft.App/managedEnvironments@2026-07-01' = {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'azure-monitor'
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

resource environmentLogs 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'to-law-sec-edgar-dev'
  scope: managedEnvironment
  properties: {
    workspaceId: workspaceId
    logAnalyticsDestinationType: 'Dedicated'
    logs: [
      {
        category: 'ContainerAppConsoleLogs'
        enabled: true
      }
      {
        category: 'ContainerAppSystemLogs'
        enabled: true
      }
    ]
  }
}

resource job 'Microsoft.App/jobs@2026-07-01' = {
  name: jobName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${workerIdentityId}': {}
      '${pullIdentityId}': {}
    }
  }
  properties: {
    environmentId: managedEnvironment.id
    workloadProfileName: 'Consumption'
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 3600
      replicaRetryLimit: 0
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
      secrets: [
        {
          name: 'ingest-config'
          value: configJson
        }
      ]
      registries: [
        {
          server: registryServer
          identity: pullIdentityId
        }
      ]
    }
    template: {
      containers: [
        container
      ]
    }
  }
}

output jobId string = job.id
```

`infra/azure/sec-edgar-ingest/modules/factory.bicep`:

```bicep
// The factory, its pipelines and its stopped triggers (spec §7). Pipeline activities come from the committed
// JSON; the run-worker parameters and their defaults are declared here.
param location string
param name string
param workspaceId string

@description('The job container; the start override repeats it with arguments (spec §7.1).')
param container object

param imageDigest string
param configSha256 string
param jobPath string
param asyncPrefix string
param resultsUrl string
param maxLaunches int

@description('Eastern local yyyy-MM-ddTHH:mm:ss, without Z.')
param dailyStartTime string

@description('Eastern local yyyy-MM-ddTHH:mm:ss, without Z.')
param reconcileStartTime string

var runWorker = loadJsonContent('../pipelines/pl-sec-edgar-run-worker.json')
var callers = [
  {
    name: 'pl-sec-edgar-backfill'
    definition: loadJsonContent('../pipelines/pl-sec-edgar-backfill.json')
  }
  {
    name: 'pl-sec-edgar-daily'
    definition: loadJsonContent('../pipelines/pl-sec-edgar-daily.json')
  }
  {
    name: 'pl-sec-edgar-reconcile'
    definition: loadJsonContent('../pipelines/pl-sec-edgar-reconcile.json')
  }
]

resource factory 'Microsoft.DataFactory/factories@2018-06-01' = {
  name: name
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {}
}

resource factoryLogs 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'to-law-sec-edgar-dev'
  scope: factory
  properties: {
    workspaceId: workspaceId
    logAnalyticsDestinationType: 'Dedicated'
    logs: [
      {
        category: 'ActivityRuns'
        enabled: true
      }
      {
        category: 'PipelineRuns'
        enabled: true
      }
      {
        category: 'TriggerRuns'
        enabled: true
      }
    ]
  }
}

resource runWorkerPipeline 'Microsoft.DataFactory/factories/pipelines@2018-06-01' = {
  parent: factory
  name: 'pl-sec-edgar-run-worker'
  properties: {
    activities: runWorker.activities
    variables: runWorker.variables
    parameters: {
      command: {
        type: 'String'
      }
      runId: {
        type: 'String'
      }
      containerName: {
        type: 'String'
        defaultValue: container.name
      }
      imageRef: {
        type: 'String'
        defaultValue: container.image
      }
      containerResources: {
        type: 'Object'
        defaultValue: container.resources
      }
      containerEnv: {
        type: 'Array'
        defaultValue: container.env
      }
      imageDigest: {
        type: 'String'
        defaultValue: imageDigest
      }
      configSha256: {
        type: 'String'
        defaultValue: configSha256
      }
      jobPath: {
        type: 'String'
        defaultValue: jobPath
      }
      asyncPrefix: {
        type: 'String'
        defaultValue: asyncPrefix
      }
      resultsUrl: {
        type: 'String'
        defaultValue: resultsUrl
      }
      maxLaunches: {
        type: 'Int'
        defaultValue: maxLaunches
      }
      pollSeconds: {
        type: 'Int'
        defaultValue: 30
      }
      observeSeconds: {
        type: 'Int'
        defaultValue: 4200
      }
      workerSeconds: {
        type: 'Int'
        defaultValue: 3300
      }
    }
  }
}

resource callerPipelines 'Microsoft.DataFactory/factories/pipelines@2018-06-01' = [for caller in callers: {
  parent: factory
  name: caller.name
  properties: caller.definition
  dependsOn: [
    runWorkerPipeline
  ]
}]

// Triggers deploy stopped: the schema has no settable runtimeState and nothing here starts them (spec §7.4).
resource dailyTrigger 'Microsoft.DataFactory/factories/triggers@2018-06-01' = {
  parent: factory
  name: 'tr-sec-edgar-daily'
  properties: {
    type: 'ScheduleTrigger'
    pipelines: [
      {
        pipelineReference: {
          referenceName: 'pl-sec-edgar-daily'
          type: 'PipelineReference'
        }
      }
    ]
    typeProperties: {
      recurrence: {
        frequency: 'Day'
        interval: 1
        startTime: dailyStartTime
        timeZone: 'Eastern Standard Time'
        schedule: {
          hours: [
            5
          ]
          minutes: [
            0
          ]
        }
      }
    }
  }
  dependsOn: [
    callerPipelines
  ]
}

resource reconcileTrigger 'Microsoft.DataFactory/factories/triggers@2018-06-01' = {
  parent: factory
  name: 'tr-sec-edgar-reconcile'
  properties: {
    type: 'ScheduleTrigger'
    pipelines: [
      {
        pipelineReference: {
          referenceName: 'pl-sec-edgar-reconcile'
          type: 'PipelineReference'
        }
      }
    ]
    typeProperties: {
      recurrence: {
        frequency: 'Week'
        interval: 1
        startTime: reconcileStartTime
        timeZone: 'Eastern Standard Time'
        schedule: {
          weekDays: [
            'Sunday'
          ]
          hours: [
            6
          ]
          minutes: [
            0
          ]
        }
      }
    }
  }
  dependsOn: [
    callerPipelines
  ]
}

output principalId string = factory.identity.principalId
```

- [ ] **Step 3: Append the container, job and factory to main.bicep**

Append after a blank line:

```bicep
// The job container. ADF's start override repeats it with arguments added (spec §4, §7.1).
var container = {
  name: 'sec-edgar-ingest'
  image: '${registryServer}/sec-edgar-ingest@${config.worker.image_digest}'
  resources: {
    cpu: 2
    memory: '4Gi'
  }
  env: [
    {
      name: 'SEC_EDGAR_INGEST_WORKER_CLIENT_ID'
      value: identities.outputs.workerClientId
    }
    {
      name: 'SEC_EDGAR_INGEST_CONFIG'
      secretRef: 'ingest-config'
    }
  ]
}

module job 'modules/job.bicep' = {
  name: 'job'
  scope: group
  params: {
    location: location
    environmentName: names.environment
    jobName: names.job
    workspaceId: monitoring.outputs.workspaceId
    container: container
    configJson: configJson
    workerIdentityId: identities.outputs.workerId
    pullIdentityId: identities.outputs.pullId
    registryServer: registryServer
  }
}

module factory 'modules/factory.bicep' = {
  name: 'factory'
  scope: group
  params: {
    location: location
    name: names.factory
    workspaceId: monitoring.outputs.workspaceId
    container: container
    imageDigest: config.worker.image_digest
    configSha256: configSha256
    jobPath: job.outputs.jobId
    asyncPrefix: 'https://management.azure.com/subscriptions/${subscription().subscriptionId}/providers/Microsoft.App/locations/${location}/'
    resultsUrl: '${config.storage.blob_endpoint}/results/runs/sec/'
    maxLaunches: 1 + config.orchestration.transient_replays
    dailyStartTime: dailyStartTime
    reconcileStartTime: reconcileStartTime
  }
}
```

- [ ] **Step 4: Compile and run the tests**

Run: `~/.azure/bin/bicep build infra/azure/sec-edgar-ingest/main.bicep --outfile infra/azure/sec-edgar-ingest/main.json`

Then run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_azure_template -v`

Expected: exit 0, then PASS, 13 tests. Task 4 Step 6 governs warnings, and Task 4 Step 7 governs any difference in emitted shape.

- [ ] **Step 5: Commit**

```bash
git add infra/azure/sec-edgar-ingest/main.bicep infra/azure/sec-edgar-ingest/main.json infra/azure/sec-edgar-ingest/modules/job.bicep infra/azure/sec-edgar-ingest/modules/factory.bicep packages/sec-edgar-ingest/tests/test_azure_template.py
git commit -m "feat(infra): add the manual job, the factory pipelines and the stopped Eastern triggers

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Role assignments

Each `roles.json` scope is granted by one small module that declares that scope's resource as `existing` and assigns the grants filtered to its scope key. The modules cover:

- each Blob container;
- each table;
- the job and the registry;
- the subscription, for the async observer.

The role definition ID is `guid(subscription().id, roleName)` for a custom role, or the `AcrPull` built-in. Assignment names include the principal ID, so a replaced identity gets a new assignment rather than a conflicting update.

**Files:**
- Create: `infra/azure/sec-edgar-ingest/modules/access/container.bicep`, `table.bicep`, `job.bicep`, `registry.bicep`, `subscription.bicep`
- Modify: `infra/azure/sec-edgar-ingest/main.bicep` (append), `main.json` (recompile)
- Modify: `tests/test_azure_template.py` (add `AccessTests`)

**Interfaces:**
- Consumes:
  - `roles.json`, `roleIds` and `names` (Task 4);
  - the `factory.principalId` and `identities` outputs (Tasks 4–5);
  - the `operatorPrincipalId` parameter.
- Produces: the deployments `access-job`, `access-registry` and `access-subscription`, and the loops `containerAccess` and `tableAccess`.

- [ ] **Step 1: Write the failing tests**

Add this class to `tests/test_azure_template.py`, above `if __name__ == '__main__':`:

```python
class AccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = template()

    def access_modules(self):
        single = [deployment(self.template, name) for name in ('access-job', 'access-registry', 'access-subscription')]
        looped = [item for item in resources(self.template, 'Microsoft.Resources/deployments')
                  if item.get('copy', {}).get('name') in ('containerAccess', 'tableAccess')]
        return single + looped

    def test_every_scope_is_granted_through_one_access_module(self):
        loops = {item['copy']['name']: item for item in resources(self.template, 'Microsoft.Resources/deployments')
                 if 'copy' in item}
        self.assertEqual(loops['containerAccess']['copy']['count'], "[length(variables('containers'))]")
        self.assertEqual(loops['tableAccess']['copy']['count'], "[length(variables('tables'))]")
        self.assertIn("'container:{0}'", text(loops['containerAccess']['properties']['parameters']['scopeKey']))
        self.assertIn("'table:{0}'", text(loops['tableAccess']['properties']['parameters']['scopeKey']))
        modules = self.access_modules()
        self.assertEqual(len(modules), 5)
        for item in modules:
            parameters = item['properties']['parameters']
            self.assertEqual(parameters['assignments'], {'value': "[variables('roles').assignments]"})
            self.assertEqual(set(parameters['principals']['value']), {'adf', 'worker', 'pull', 'operator'})
            self.assertEqual(parameters['principals']['value']['operator'], "[parameters('operatorPrincipalId')]")
            grant, = resources(item['properties']['template'], 'Microsoft.Authorization/roleAssignments')
            body = text(grant['properties'])
            for fragment in ("parameters('roleIds')", "parameters('principals')", "'operator'", "'User'",
                             "'ServicePrincipal'"):
                self.assertIn(fragment, body)

    def test_no_broad_or_secret_bearing_permission_anywhere(self):
        body = text(self.template)
        for forbidden in ('listKeys', 'listSecrets', 'listCredentials', 'Owner', 'Contributor', '"*"', '/*"'):
            self.assertNotIn(forbidden, body)
        literal_role_ids = set(re.findall(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', body))
        self.assertEqual(literal_role_ids, {'7f951dda-4ed3-4680-a7ca-43fe172d538d'})
```

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_azure_template.AccessTests -v`
Expected: FAIL or ERROR: `KeyError: 'containerAccess'` and `AssertionError: ('access-job', 0)`.

- [ ] **Step 2: Write the access modules**

`infra/azure/sec-edgar-ingest/modules/access/container.bicep`:

```bicep
// The roles.json grants whose scope is one Blob container (spec §5).
param storageName string
param containerName string

@description('The roles.json scope key handled here, container:<name>.')
param scopeKey string

param assignments array
param roleIds object
param principals object

resource account 'Microsoft.Storage/storageAccounts@2025-06-01' existing = {
  name: storageName
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2025-06-01' existing = {
  parent: account
  name: 'default'
}

resource container 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' existing = {
  parent: blobService
  name: containerName
}

resource grants 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for grant in filter(assignments, item => item.scope == scopeKey): {
  name: guid(container.id, principals[grant.principal], grant.role)
  scope: container
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds[grant.role])
    principalId: principals[grant.principal]
    principalType: grant.principal == 'operator' ? 'User' : 'ServicePrincipal'
  }
}]
```

`infra/azure/sec-edgar-ingest/modules/access/table.bicep`:

```bicep
// The roles.json grants whose scope is one table (spec §5).
param storageName string
param tableName string

@description('The roles.json scope key handled here, table:<name>.')
param scopeKey string

param assignments array
param roleIds object
param principals object

resource account 'Microsoft.Storage/storageAccounts@2025-06-01' existing = {
  name: storageName
}

resource tableService 'Microsoft.Storage/storageAccounts/tableServices@2025-06-01' existing = {
  parent: account
  name: 'default'
}

resource table 'Microsoft.Storage/storageAccounts/tableServices/tables@2025-06-01' existing = {
  parent: tableService
  name: tableName
}

resource grants 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for grant in filter(assignments, item => item.scope == scopeKey): {
  name: guid(table.id, principals[grant.principal], grant.role)
  scope: table
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds[grant.role])
    principalId: principals[grant.principal]
    principalType: grant.principal == 'operator' ? 'User' : 'ServicePrincipal'
  }
}]
```

`infra/azure/sec-edgar-ingest/modules/access/job.bicep`:

```bicep
// The roles.json grants whose scope is the job (spec §5).
param jobName string
param assignments array
param roleIds object
param principals object

resource job 'Microsoft.App/jobs@2026-07-01' existing = {
  name: jobName
}

resource grants 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for grant in filter(assignments, item => item.scope == 'job'): {
  name: guid(job.id, principals[grant.principal], grant.role)
  scope: job
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds[grant.role])
    principalId: principals[grant.principal]
    principalType: grant.principal == 'operator' ? 'User' : 'ServicePrincipal'
  }
}]
```

`infra/azure/sec-edgar-ingest/modules/access/registry.bicep`:

```bicep
// The roles.json grants whose scope is the registry (spec §5).
param registryName string
param assignments array
param roleIds object
param principals object

resource registry 'Microsoft.ContainerRegistry/registries@2025-11-01' existing = {
  name: registryName
}

resource grants 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for grant in filter(assignments, item => item.scope == 'registry'): {
  name: guid(registry.id, principals[grant.principal], grant.role)
  scope: registry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds[grant.role])
    principalId: principals[grant.principal]
    principalType: grant.principal == 'operator' ? 'User' : 'ServicePrincipal'
  }
}]
```

`infra/azure/sec-edgar-ingest/modules/access/subscription.bicep`:

```bicep
// The roles.json grants whose scope is the subscription: the async observer, whose operation routes sit
// outside the job's ancestry (spec §5).
targetScope = 'subscription'

param assignments array
param roleIds object
param principals object

resource grants 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for grant in filter(assignments, item => item.scope == 'subscription'): {
  name: guid(subscription().id, principals[grant.principal], grant.role)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds[grant.role])
    principalId: principals[grant.principal]
    principalType: grant.principal == 'operator' ? 'User' : 'ServicePrincipal'
  }
}]
```

- [ ] **Step 3: Append the principals and access modules to main.bicep**

Append after a blank line:

```bicep
// Who each roles.json principal is.
var principals = {
  adf: factory.outputs.principalId
  worker: identities.outputs.workerPrincipalId
  pull: identities.outputs.pullPrincipalId
  operator: operatorPrincipalId
}

module containerAccess 'modules/access/container.bicep' = [for name in containers: {
  name: 'access-container-${name}'
  scope: group
  params: {
    storageName: names.storage
    containerName: name
    scopeKey: 'container:${name}'
    assignments: roles.assignments
    roleIds: roleIds
    principals: principals
  }
  dependsOn: [
    storage
    roleDefinitions
  ]
}]

module tableAccess 'modules/access/table.bicep' = [for name in tables: {
  name: 'access-table-${name}'
  scope: group
  params: {
    storageName: names.storage
    tableName: name
    scopeKey: 'table:${name}'
    assignments: roles.assignments
    roleIds: roleIds
    principals: principals
  }
  dependsOn: [
    storage
    roleDefinitions
  ]
}]

module jobAccess 'modules/access/job.bicep' = {
  name: 'access-job'
  scope: group
  params: {
    jobName: names.job
    assignments: roles.assignments
    roleIds: roleIds
    principals: principals
  }
  dependsOn: [
    job
    roleDefinitions
  ]
}

module registryAccess 'modules/access/registry.bicep' = {
  name: 'access-registry'
  scope: group
  params: {
    registryName: names.registry
    assignments: roles.assignments
    roleIds: roleIds
    principals: principals
  }
  dependsOn: [
    registry
    roleDefinitions
  ]
}

module subscriptionAccess 'modules/access/subscription.bicep' = {
  name: 'access-subscription'
  params: {
    assignments: roles.assignments
    roleIds: roleIds
    principals: principals
  }
  dependsOn: [
    roleDefinitions
  ]
}
```

- [ ] **Step 4: Compile and run the tests**

Run: `~/.azure/bin/bicep build infra/azure/sec-edgar-ingest/main.bicep --outfile infra/azure/sec-edgar-ingest/main.json`

Then run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_azure_template -v` and the same command for `test_azure_roles`.

Expected: exit 0, then PASS, 15 tests and 6 tests. No unused-parameter warning remains.

- [ ] **Step 5: Commit**

```bash
git add infra/azure/sec-edgar-ingest/main.bicep infra/azure/sec-edgar-ingest/main.json infra/azure/sec-edgar-ingest/modules/access packages/sec-edgar-ingest/tests/test_azure_template.py
git commit -m "feat(infra): grant the spec role matrix through per-scope access modules

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Alerts

Spec §8 defines ten log-search alerts over `law-sec-edgar-dev`.

- The two ADF alerts read `ADFActivityRun` rows of run-worker's Fail activity.
- The worker alerts read the structured events in `ContainerAppConsoleLogs`. `command_finished` and `command_error` carry `fields.outcome`, and `workflow_summary` carries Plan 9's summary fields.
- The staleness alerts deploy disabled.

A vocabulary test confines every quoted literal and every `entry.*` path to:

- events that `log_event` calls emit;
- `SUMMARY_FIELDS`;
- `RunContext` fields;
- `EXIT_CODES`;
- the pipeline's own error codes.

**Files:**
- Create: `infra/azure/sec-edgar-ingest/alerts/*.kql` (ten files)
- Create: `infra/azure/sec-edgar-ingest/modules/alerts.bicep`
- Modify: `infra/azure/sec-edgar-ingest/main.bicep` (append), `main.json` (recompile)
- Create: `tests/test_azure_alerts.py`

**Interfaces:**
- Consumes:
  - `SUMMARY_FIELDS` and the `workflow_summary` event (Plan 9);
  - the `command_finished` and `command_error` events (shipped);
  - run-worker's `Fail run` error codes (Task 2);
  - the `monitoring` outputs (Task 4).
- Produces: the `alerts` module, and the names `alert-sec-edgar-<slug>` for the ten slugs in `EXPECTED`.

- [ ] **Step 1: Write the failing tests**

`tests/test_azure_alerts.py`; Task 8 adds a class to it:

```python
"""Alert queries name only what the worker and pipelines emit; staleness alerts deploy disabled (spec §8, §10)."""
from network_guard import install
install()

import re
import unittest
from dataclasses import fields

from support_template import INFRA, REPO, module, resources, template
from sec_edgar_ingest.models import RunContext
from sec_edgar_ingest.results import EXIT_CODES
from sec_edgar_ingest.workflows.summary import SUMMARY_FIELDS

SOURCE = REPO / 'packages/sec-edgar-ingest/src/sec_edgar_ingest'
RUN_WORKER = (INFRA / 'pipelines/pl-sec-edgar-run-worker.json').read_text()
# What each spec §8 row requires its query to say.
EXPECTED = {
    'failed-job': ('ADFActivityRun', '!in ("awaiting_approval", "execution_unknown")'),
    'ambiguous-start': ('ADFActivityRun', 'ErrorCode == "execution_unknown"'),
    'lease-failure': ('== "ownership_lost"', 'member_outcomes.ownership_lost) > 0'),
    'access-block': ('== "access_blocked"', 'member_outcomes.access_blocked) > 0'),
    'retry-exhausted': ('member_outcomes.retry_exhausted) > 0',),
    'quarantine': ('== "quarantined"', 'member_outcomes.quarantined) > 0'),
    'publication-conflict': ('== "publication_conflict"', 'member_outcomes.publication_conflict) > 0'),
    'pending-approval': ('fields.pending_approvals) > 0',),
    'reconcile-staleness': ('fields.last_successful_reconcile_at', 'isnull(last) or last < ago(8d)'),
    'daily-staleness': ('ago(30h)', 'entry.context.command) == "daily"', 'fields.discovery_complete', 'found == 0'),
}
STALENESS = {'alert-sec-edgar-reconcile-staleness', 'alert-sec-edgar-daily-staleness'}
PIPELINE_ONLY = {'execution_unknown', 'execution_stopped', 'execution_mismatch', 'result_missing', 'result_mismatch',
                 'stale'}


def queries() -> dict[str, str]:
    return {path.stem: path.read_text() for path in sorted((INFRA / 'alerts').glob('*.kql'))}


def emitted_events() -> set[str]:
    code = '\n'.join(path.read_text() for path in SOURCE.rglob('*.py'))
    return set(re.findall(r"log_event\([^,()]+, '([a-z_]+)'", code))


class AlertQueryTests(unittest.TestCase):
    def test_each_spec_alert_has_its_query(self):
        found = queries()
        self.assertEqual(set(found), set(EXPECTED))
        for slug, phrases in EXPECTED.items():
            for phrase in phrases:
                self.assertIn(phrase, found[slug], slug)

    def test_queries_name_only_emitted_events_fields_and_outcomes(self):
        events = emitted_events()
        self.assertLessEqual({'command_finished', 'command_error', 'workflow_summary'}, events)
        for code in PIPELINE_ONLY:
            self.assertIn(f"'{code}'", RUN_WORKER)
        self.assertIn('job: \'job-sec-edgar-dev\'', (INFRA / 'main.bicep').read_text())
        self.assertIn('"type": "Fail"', RUN_WORKER)
        literals = events | set(EXIT_CODES) | PIPELINE_ONLY | {'pl-sec-edgar-run-worker', 'Fail', 'Failed',
                                                               'job-sec-edgar-dev', 'daily'}
        context = {field.name for field in fields(RunContext)}
        for slug, query in queries().items():
            with self.subTest(slug):
                self.assertLessEqual(set(re.findall(r'"([^"]*)"', query)), literals)
                for path in re.findall(r'entry((?:\.\w+)+)', query):
                    root, *rest = path.strip('.').split('.')
                    self.assertIn(root, ('event', 'fields', 'context'), path)
                    if root == 'event':
                        self.assertEqual(rest, [], path)
                    elif root == 'context':
                        self.assertTrue(len(rest) == 1 and rest[0] in context, path)
                    elif rest[:1] == ['member_outcomes']:
                        self.assertTrue(len(rest) == 2 and rest[1] in EXIT_CODES, path)
                    else:
                        self.assertTrue(len(rest) == 1 and rest[0] in SUMMARY_FIELDS, path)


class AlertDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.alerts_module = module(template(), 'alerts')
        self.alerts = {alert['name']: alert for alert in self.alerts_module['variables']['alerts']}

    def test_every_alert_deploys_its_committed_query(self):
        self.assertEqual(set(self.alerts), {f'alert-sec-edgar-{slug}' for slug in EXPECTED})
        for slug, query in queries().items():
            self.assertEqual(self.alerts[f'alert-sec-edgar-{slug}']['query'], query)

    def test_only_the_staleness_alerts_deploy_disabled_and_stateful(self):
        self.assertEqual({name for name, alert in self.alerts.items() if not alert['enabled']}, STALENESS)
        self.assertEqual({name for name, alert in self.alerts.items() if alert['stateful']}, STALENESS)
        for name, alert in self.alerts.items():
            expected = ('PT1H', 'P2D') if name in STALENESS else ('PT15M', 'PT30M')
            self.assertEqual((alert['frequency'], alert['window']), expected, name)

    def test_rules_count_any_row_and_notify_the_action_group(self):
        rule, = resources(self.alerts_module, 'Microsoft.Insights/scheduledQueryRules')
        criterion, = rule['properties']['criteria']['allOf']
        self.assertEqual((rule['kind'], criterion['operator'], criterion['threshold'], criterion['timeAggregation']),
                         ('LogAlert', 'GreaterThan', 0, 'Count'))
        self.assertEqual(rule['properties']['actions'], {'actionGroups': ["[parameters('actionGroupId')]"]})
        self.assertEqual(rule['properties']['scopes'], ["[parameters('workspaceId')]"])


if __name__ == '__main__':
    unittest.main()
```

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_azure_alerts -v`
Expected: `test_each_spec_alert_has_its_query` FAILs (no `.kql` files); the deployment tests ERROR with `AssertionError: ('alerts', 0)`.

- [ ] **Step 2: Write the queries**

`infra/azure/sec-edgar-ingest/alerts/failed-job.kql`:

```kusto
// A run-worker pipeline ended in its Fail activity with an outcome other than the gated and ambiguous ones.
ADFActivityRun
| where PipelineName == "pl-sec-edgar-run-worker" and ActivityType == "Fail" and Status == "Failed"
| where ErrorCode !in ("awaiting_approval", "execution_unknown")
| project TimeGenerated, PipelineRunId, ErrorCode, ErrorMessage
```

`alerts/ambiguous-start.kql`:

```kusto
// A run-worker pipeline could not resolve its execution: no relaunch happened; recover by hand.
ADFActivityRun
| where PipelineName == "pl-sec-edgar-run-worker" and ActivityType == "Fail" and Status == "Failed"
| where ErrorCode == "execution_unknown"
| project TimeGenerated, PipelineRunId, ErrorCode, ErrorMessage
```

`alerts/lease-failure.kql`:

```kusto
// A worker lost its lease. The row names the execution.
ContainerAppConsoleLogs
| where JobName == "job-sec-edgar-dev"
| extend entry = parse_json(Log)
| where tostring(entry.event) in ("command_finished", "command_error", "workflow_summary")
| where tostring(entry.fields.outcome) == "ownership_lost" or toint(entry.fields.member_outcomes.ownership_lost) > 0
| project TimeGenerated, ExecutionName = tostring(entry.context.execution_id), Log
```

`alerts/access-block.kql`:

```kusto
// The SEC blocked access. The row names the execution.
ContainerAppConsoleLogs
| where JobName == "job-sec-edgar-dev"
| extend entry = parse_json(Log)
| where tostring(entry.event) in ("command_finished", "command_error", "workflow_summary")
| where tostring(entry.fields.outcome) == "access_blocked" or toint(entry.fields.member_outcomes.access_blocked) > 0
| project TimeGenerated, ExecutionName = tostring(entry.context.execution_id), Log
```

`alerts/retry-exhausted.kql`:

```kusto
// A workflow exhausted the retry budget of at least one member.
ContainerAppConsoleLogs
| where JobName == "job-sec-edgar-dev"
| extend entry = parse_json(Log)
| where tostring(entry.event) == "workflow_summary"
| where tostring(entry.fields.outcome) == "retry_exhausted" or toint(entry.fields.member_outcomes.retry_exhausted) > 0
| project TimeGenerated, ExecutionName = tostring(entry.context.execution_id), Log
```

`alerts/quarantine.kql`:

```kusto
// A source was quarantined. The row names the execution.
ContainerAppConsoleLogs
| where JobName == "job-sec-edgar-dev"
| extend entry = parse_json(Log)
| where tostring(entry.event) in ("command_finished", "command_error", "workflow_summary")
| where tostring(entry.fields.outcome) == "quarantined" or toint(entry.fields.member_outcomes.quarantined) > 0
| project TimeGenerated, ExecutionName = tostring(entry.context.execution_id), Log
```

`alerts/publication-conflict.kql`:

```kusto
// A publication conflict is unresolved. The row names the execution.
ContainerAppConsoleLogs
| where JobName == "job-sec-edgar-dev"
| extend entry = parse_json(Log)
| where tostring(entry.event) in ("command_finished", "command_error", "workflow_summary")
| where tostring(entry.fields.outcome) == "publication_conflict" or toint(entry.fields.member_outcomes.publication_conflict) > 0
| project TimeGenerated, ExecutionName = tostring(entry.context.execution_id), Log
```

`alerts/pending-approval.kql`:

```kusto
// Every run that leaves a withdrawal candidate pending approval (owner decision Q4: on every run).
ContainerAppConsoleLogs
| where JobName == "job-sec-edgar-dev"
| extend entry = parse_json(Log)
| where tostring(entry.event) == "workflow_summary"
| where toint(entry.fields.pending_approvals) > 0
| project TimeGenerated, ExecutionName = tostring(entry.context.execution_id), Log
```

`alerts/reconcile-staleness.kql`:

```kusto
// The latest summary in the two-day window reports no successful reconciliation in eight days.
ContainerAppConsoleLogs
| where JobName == "job-sec-edgar-dev"
| extend entry = parse_json(Log)
| where tostring(entry.event) == "workflow_summary"
| summarize arg_max(TimeGenerated, entry)
| extend last = todatetime(entry.fields.last_successful_reconcile_at)
| where isnull(last) or last < ago(8d)
```

`alerts/daily-staleness.kql`:

```kusto
// No daily summary with complete discovery in the last 30 hours.
let found = toscalar(ContainerAppConsoleLogs
    | where TimeGenerated > ago(30h) and JobName == "job-sec-edgar-dev"
    | extend entry = parse_json(Log)
    | where tostring(entry.event) == "workflow_summary"
    | where tostring(entry.context.command) == "daily" and tobool(entry.fields.discovery_complete)
    | count);
print found
| where found == 0
```

- [ ] **Step 3: Write the alerts module and append it to main.bicep**

`infra/azure/sec-edgar-ingest/modules/alerts.bicep`:

```bicep
// Log search alerts over law-sec-edgar-dev (spec §8). Per-run alerts are stateless and overlap their
// windows, so an event ingested up to 15 minutes late still alerts. The staleness alerts are stateful and
// deploy disabled until Stage 8 enables them with their triggers.
param location string
param workspaceId string
param actionGroupId string

var alerts = [
  {
    name: 'alert-sec-edgar-failed-job'
    description: 'A run-worker pipeline failed with an outcome other than awaiting_approval or execution_unknown.'
    severity: 1
    enabled: true
    stateful: false
    frequency: 'PT15M'
    window: 'PT30M'
    query: loadTextContent('../alerts/failed-job.kql')
  }
  {
    name: 'alert-sec-edgar-ambiguous-start'
    description: 'A run-worker pipeline ended execution_unknown; no relaunch happened.'
    severity: 1
    enabled: true
    stateful: false
    frequency: 'PT15M'
    window: 'PT30M'
    query: loadTextContent('../alerts/ambiguous-start.kql')
  }
  {
    name: 'alert-sec-edgar-lease-failure'
    description: 'A worker lost its lease (ownership_lost).'
    severity: 1
    enabled: true
    stateful: false
    frequency: 'PT15M'
    window: 'PT30M'
    query: loadTextContent('../alerts/lease-failure.kql')
  }
  {
    name: 'alert-sec-edgar-access-block'
    description: 'The SEC blocked access (access_blocked).'
    severity: 1
    enabled: true
    stateful: false
    frequency: 'PT15M'
    window: 'PT30M'
    query: loadTextContent('../alerts/access-block.kql')
  }
  {
    name: 'alert-sec-edgar-retry-exhausted'
    description: 'A workflow exhausted the retry budget of a member.'
    severity: 2
    enabled: true
    stateful: false
    frequency: 'PT15M'
    window: 'PT30M'
    query: loadTextContent('../alerts/retry-exhausted.kql')
  }
  {
    name: 'alert-sec-edgar-quarantine'
    description: 'A source or workflow was quarantined.'
    severity: 2
    enabled: true
    stateful: false
    frequency: 'PT15M'
    window: 'PT30M'
    query: loadTextContent('../alerts/quarantine.kql')
  }
  {
    name: 'alert-sec-edgar-publication-conflict'
    description: 'A publication conflict is unresolved.'
    severity: 1
    enabled: true
    stateful: false
    frequency: 'PT15M'
    window: 'PT30M'
    query: loadTextContent('../alerts/publication-conflict.kql')
  }
  {
    name: 'alert-sec-edgar-pending-approval'
    description: 'A withdrawal candidate is pending approval.'
    severity: 2
    enabled: true
    stateful: false
    frequency: 'PT15M'
    window: 'PT30M'
    query: loadTextContent('../alerts/pending-approval.kql')
  }
  {
    name: 'alert-sec-edgar-reconcile-staleness'
    description: 'No successful reconciliation in eight days. Enabled with the reconcile trigger (Stage 8).'
    severity: 2
    enabled: false
    stateful: true
    frequency: 'PT1H'
    window: 'P2D'
    query: loadTextContent('../alerts/reconcile-staleness.kql')
  }
  {
    name: 'alert-sec-edgar-daily-staleness'
    description: 'No daily run with complete discovery in 30 hours. Enabled with the daily trigger (Stage 8).'
    severity: 2
    enabled: false
    stateful: true
    frequency: 'PT1H'
    window: 'P2D'
    query: loadTextContent('../alerts/daily-staleness.kql')
  }
]

resource rules 'Microsoft.Insights/scheduledQueryRules@2023-12-01' = [for alert in alerts: {
  name: alert.name
  location: location
  kind: 'LogAlert'
  properties: {
    displayName: alert.name
    description: alert.description
    severity: alert.severity
    enabled: alert.enabled
    scopes: [
      workspaceId
    ]
    evaluationFrequency: alert.frequency
    windowSize: alert.window
    criteria: {
      allOf: [
        {
          query: alert.query
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 0
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    autoMitigate: alert.stateful
    skipQueryValidation: true
    actions: {
      actionGroups: [
        actionGroupId
      ]
    }
  }
}]
```

Append to `main.bicep` after a blank line:

```bicep
module alerts 'modules/alerts.bicep' = {
  name: 'alerts'
  scope: group
  params: {
    location: location
    workspaceId: monitoring.outputs.workspaceId
    actionGroupId: monitoring.outputs.actionGroupId
  }
}
```

- [ ] **Step 4: Compile and run the tests**

Run: `~/.azure/bin/bicep build infra/azure/sec-edgar-ingest/main.bicep --outfile infra/azure/sec-edgar-ingest/main.json`

Then run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_azure_alerts -v`, and the same command for `test_azure_template`.

Expected: exit 0, then PASS (5 tests), then PASS (15 tests).

- [ ] **Step 5: Commit**

```bash
git add infra/azure/sec-edgar-ingest/alerts infra/azure/sec-edgar-ingest/modules/alerts.bicep infra/azure/sec-edgar-ingest/main.bicep infra/azure/sec-edgar-ingest/main.json packages/sec-edgar-ingest/tests/test_azure_alerts.py
git commit -m "feat(infra): add the spec alerts with staleness deployed disabled

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: The operations runbook

**Files:**
- Create: `docs/runbooks/sec-edgar-azure-operations.md`
- Modify: `tests/test_azure_alerts.py` (add `OperationsRunbookTests`)

**Interfaces:**
- Consumes:
  - Plan 9's renderer (`python -m sec_edgar_ingest.deployment`) and its approval runbook;
  - every name defined in Tasks 2–7.
- Produces: the runbook that Stage 7 exercises.

- [ ] **Step 1: Write the failing test**

Add this class to `tests/test_azure_alerts.py`, above `if __name__ == '__main__':`:

```python
class OperationsRunbookTests(unittest.TestCase):
    def test_the_runbook_covers_every_alert_and_pipeline_outcome(self):
        runbook = (REPO / 'docs/runbooks/sec-edgar-azure-operations.md').read_text()
        for slug in EXPECTED:
            self.assertIn(f'`alert-sec-edgar-{slug}`', runbook)
        for code in PIPELINE_ONLY | {'success', 'awaiting_approval', 'pending'}:
            self.assertIn(f'| `{code}` |', runbook)
        for phrase in ('reserved/not_run', 'deploy stopped', 'launch-<n>', 'Never start a launch by hand'):
            self.assertIn(phrase, runbook)
```

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_azure_alerts.OperationsRunbookTests -v`
Expected: ERROR, `FileNotFoundError` for the runbook.

- [ ] **Step 2: Write the runbook**

`docs/runbooks/sec-edgar-azure-operations.md`:

````markdown
# Azure deployment and orchestration

Stage 6 defines the Azure deployment; nothing here has run against Azure. Every command below is for Stage 7 or later, under that stage's own authorization. All 22 Stage 7 integrated checks remain reserved/not_run, and Stage 7 verifies each command before relying on it.

The definitions live in `infra/azure/sec-edgar-ingest/`:

- `main.bicep` and `modules/` define everything.
- `main.json` is the committed compile, built with Bicep 0.38.33. Deploy that file.
- `roles.json` is the role matrix.
- `pipelines/*.json` are the ADF pipelines, rendered by `pipelines/render.py`.
- `alerts/*.kql` are the alert queries.
- `config/` holds the Azure config template.

## What a deployment creates

| Resource | Name | Notes |
|---|---|---|
| Resource group | `rg-sec-edgar-dev-eastus` | |
| Custom roles | `SecEdgar Job Controller`, `SecEdgar Job Async Observer`, `SecEdgar Blob Reader`, `SecEdgar Blob Writer`, `SecEdgar Entity Reader`, `SecEdgar Entity Writer` | Subscription-assignable; the grants are in `roles.json` |
| Identities | `id-sec-edgar-dev-worker`, `id-sec-edgar-dev-pull` | The worker reaches storage; the pull identity reaches only the registry |
| Registry | `secedgardevb8617` | Basic; admin user, anonymous pull and keys off |
| Storage | `secedgardevb8617` | HNS, ZRS, Entra only; 8 containers, 4 tables |
| Workspace and action group | `law-sec-edgar-dev`, `ag-sec-edgar-dev` | 90-day retention; email to the operator |
| Container Apps | `cae-sec-edgar-dev-eastus`, `job-sec-edgar-dev` | Manual job, no schedule, no volumes |
| Data Factory | `adf-sec-edgar-dev` | Four pipelines and two triggers; the triggers deploy stopped |
| Alerts | `alert-sec-edgar-*` | Ten; the two staleness alerts deploy disabled |

## Deploy (Stage 7)

1. Render the config for the release digest that S7-05 published:

   ```bash
   uv run --offline --frozen --package sec-edgar-ingest python -m sec_edgar_ingest.deployment --template infra/azure/sec-edgar-ingest/config/sec-edgar-ingest.azure.template.json --image-digest sha256:<release digest> --provenance <S7-05 build reference> --out-dir /tmp/sec-edgar-release
   ```

2. Rebuild the template and check it matches the committed compile:

   ```bash
   ~/.azure/bin/bicep build infra/azure/sec-edgar-ingest/main.bicep --outfile /tmp/sec-edgar-release/main.json
   cmp /tmp/sec-edgar-release/main.json infra/azure/sec-edgar-ingest/main.json
   ```

3. Confirm that no execution is in flight. A config or digest change redeploys the job, and an attempt begun under the old pair fails on replay with `Conflict`. Both checks must list nothing:
   - executions of `job-sec-edgar-dev` in `Running` or `Processing`;
   - `pl-sec-edgar-*` pipeline runs `InProgress`.

4. Validate, run what-if, then deploy at subscription scope. Use the same parameters for all three:

   ```bash
   az deployment sub what-if --location eastus --template-file infra/azure/sec-edgar-ingest/main.json --parameters @/tmp/sec-edgar-release/main.parameters.json operatorPrincipalId=<operator object ID> dailyStartTime=<yyyy-MM-ddTHH:mm:ss> reconcileStartTime=<yyyy-MM-ddTHH:mm:ss>
   ```

   The two start times are Eastern local times without `Z`; the template rejects any other length.

Bootstrap authority (D-04) is a Stage 7 prerequisite, outside the template.

## Triggers and staleness alerts (Stage 8)

Triggers deploy stopped and nothing in the template starts them. Stage 8 starts `tr-sec-edgar-daily` and `tr-sec-edgar-reconcile`. With each trigger it enables the matching staleness alert: `alert-sec-edgar-daily-staleness` and `alert-sec-edgar-reconcile-staleness`. Record each step.

ADF rejects an update to a started trigger. Any redeploy after Stage 8 therefore:

1. stops both triggers;
2. deploys;
3. starts both triggers again.

Record all three steps.

`pl-sec-edgar-backfill` has no trigger. Run it by hand as a bounded campaign.

## Pipeline outcomes

Each `pl-sec-edgar-<command>` pipeline runs `pl-sec-edgar-run-worker`. Every launch is attempt `launch-<n>` of the calling pipeline's run ID. The worker writes `results/runs/sec/<run ID>/<command>/launch-<n>/result.json`. Only `success` ends a pipeline Succeeded. Every other outcome ends in the `Fail run` activity, whose error code is the outcome:

| Error code | Meaning | First response |
|---|---|---|
| `success` | The execution succeeded and its matching result has an exit-0 outcome | None |
| `awaiting_approval` | The run is gated on a withdrawal | Review it with `candidates`; see the reconciliation and approval runbook |
| `execution_unknown` | No execution name could be resolved, the state was unknown, or the 4,200 s observation deadline passed. Nothing was relaunched | Recover by hand (below) |
| `execution_stopped` | The execution was stopped | Find who stopped it; the next run is a new attempt |
| `execution_mismatch` | The execution ran an image other than the pinned digest | Compare the job image with the rendered config |
| `result_missing` | The execution ended with no readable result | Read the execution's console log |
| `result_mismatch` | The result does not match the launch, or an exit-0 outcome came from a `Failed` execution | Compare the result's context with the launch |
| `stale` | An approval or rollback was stale (exit 11) | Re-run `candidates` or `history` |
| `pending` | The second launch was still pending | The next scheduled run continues |
| Any other `EXIT_CODES` name | The worker's own outcome | See the acquisition and publication runbooks |

**Recovering `execution_unknown`.** Read `results/runs/sec/<run ID>/<command>/launch-<n>/result.json` first. If it exists, its `context.execution_id` names the execution. Otherwise, the only valid evidence is a job execution whose arguments carry that exact `--run-id` and `--attempt-id`. Never infer the execution from the newest one or from timing. While such an execution is running, wait. Never start a launch by hand under the same run ID. The next scheduled run uses a new run ID.

## Alerts

All alerts mail `ag-sec-edgar-dev`. Per-run alerts run every 15 minutes over a 30-minute window, so one event can mail twice and an event ingested up to 15 minutes late still mails.

| Alert | Fires on | First response |
|---|---|---|
| `alert-sec-edgar-failed-job` | A run-worker Fail other than `awaiting_approval` and `execution_unknown` | The pipeline outcomes table above |
| `alert-sec-edgar-ambiguous-start` | `execution_unknown` | Recover by hand (above) |
| `alert-sec-edgar-lease-failure` | `ownership_lost` | Check for a second worker; see the acquisition runbook |
| `alert-sec-edgar-access-block` | `access_blocked` | Stop the triggers; review SEC access before resuming |
| `alert-sec-edgar-retry-exhausted` | `member_outcomes.retry_exhausted` above 0 | The next run revisits the member; repeated alerts need review |
| `alert-sec-edgar-quarantine` | Quarantined members or outcome | See the acquisition runbook's quarantine section |
| `alert-sec-edgar-publication-conflict` | `publication_conflict` | See the publication runbook |
| `alert-sec-edgar-pending-approval` | `pending_approvals` above 0, on every run | Review `candidates` |
| `alert-sec-edgar-reconcile-staleness` | The latest summary shows no successful reconciliation in 8 days | Disabled until Stage 8. Check the reconcile trigger and the last reconcile outcome |
| `alert-sec-edgar-daily-staleness` | No daily summary with complete discovery in 30 h | Disabled until Stage 8. Check the daily trigger and the last daily outcome |

## Reported, not alerted

The three figures below are separate from the alerts. A weekend with no new files is `no_new_sources`, not stale ingestion. Read each from the latest daily `workflow_summary`:

```kusto
ContainerAppConsoleLogs
| where JobName == "job-sec-edgar-dev"
| extend entry = parse_json(Log)
| where tostring(entry.event) == "workflow_summary" and tostring(entry.context.command) == "daily"
| summarize arg_max(TimeGenerated, entry)
| project TimeGenerated, discovery_complete = entry.fields.discovery_complete, boundary_after = entry.fields.boundary_after, oldest_unresolved_period = entry.fields.oldest_unresolved_period, last_successful_reconcile_at = entry.fields.last_successful_reconcile_at
```

- Discovery age is the age of `boundary_after`.
- The oldest listed-but-unpublished source is `oldest_unresolved_period`.
- The last successful reconciliation is `last_successful_reconcile_at`.
````

- [ ] **Step 3: Run the test to verify it passes**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_azure_alerts -v`
Expected: PASS, 6 tests.

- [ ] **Step 4: Commit**

```bash
git add docs/runbooks/sec-edgar-azure-operations.md packages/sec-edgar-ingest/tests/test_azure_alerts.py
git commit -m "docs(runbooks): add the Azure deployment, trigger, outcome and alert runbook

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Plan exit

**Files:**
- Modify: `scripts/check-sec-edgar-ingest.sh`

- [ ] **Step 1: Add the pipeline-render and Bicep checks**

Append to `scripts/check-sec-edgar-ingest.sh`:

```sh
# The pipeline JSON is its rendered source, and main.json is its pinned compile (spec §9).
uv run --offline --frozen --package sec-edgar-ingest python infra/azure/sec-edgar-ingest/pipelines/render.py
git diff --exit-code -- infra/azure/sec-edgar-ingest/pipelines
bicep="${BICEP:-$HOME/.azure/bin/bicep}"
"$bicep" --version | grep -q '^Bicep CLI version 0\.38\.33 '
compiled="$(mktemp -d)"
"$bicep" build infra/azure/sec-edgar-ingest/main.bicep --outfile "$compiled/main.json"
cmp "$compiled/main.json" infra/azure/sec-edgar-ingest/main.json
rm -r "$compiled"
```

- [ ] **Step 2: Run the full plan-exit checks**

Run: `scripts/check-sec-edgar-ingest.sh`

Expected: exit 0, with each of these holding:

- the full offline suite passes (`OK`);
- the wheel and sdist build offline;
- help prints for every command;
- `--version` prints `0.1.0`;
- `compileall` is quiet;
- `git diff --check` is clean;
- the pipeline render leaves no diff;
- the Bicep rebuild equals the committed `main.json`.

- [ ] **Step 3: Confirm no forbidden activity or edits**

```bash
git diff --stat 9d7ea225..HEAD -- specs/evidence specs/plans/completed specs/plans/4-sec-filing-index-ingestion-stage-4-spec.md specs/plans/5-sec-filing-index-ingestion-stage-4-spec.md specs/sec-filing-index-ingestion-stage-4-spec.md conf
grep -rn "runtimeState\|listKeys\|listSecrets" infra/azure/sec-edgar-ingest --include=*.bicep --include=*.json
```

Expected: both print nothing. A command that ran against Azure would also be a stop condition. This plan has none: every `az` command above is a local tool install or version query.

- [ ] **Step 4: Commit**

```bash
git add scripts/check-sec-edgar-ingest.sh
git commit -m "chore(ingest): check the pipeline render and the pinned Bicep compile at plan exit

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Then run the final whole-branch review (subagent-driven-development), followed by the Plan Completion Protocol.

- **Roadmap stamp.** This plan carries the `Roadmap:` line, so step 3a applies. Write `## Handoff to later stages` with bullets for Stages 7 and 8. Each bullet names:
  - the deployment inputs;
  - the parameters and outputs;
  - the pipeline outcome codes;
  - the alert names and the two disabled alerts;
  - every Stage 7 assumption in spec §11.

  Then tick Stage 6 in the roadmap with the stamp.
- **Deferred items.** Plan 9 already closed the Stage 6 items; the ticking pass runs anyway.
- **Retirement.** Plan 9 retires first. This plan's retirement then retires the spec to `specs/completed/` in the same commit, because no live plan implements it any more.
