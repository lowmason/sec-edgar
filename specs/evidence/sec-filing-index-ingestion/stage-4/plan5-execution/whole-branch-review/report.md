# Independent whole-branch review

Reviewed base: `fe95642bddf006f3d2d6cb3ccc57e595d75dc4cd` (actual merge base).
Reviewed head: `fc938385de277ef1cb1d5b5862a606ecb7244d9b` (original stable clean execution tree).
Reviewer: independent `whole_branch_review` Codex agent; native code-reviewer role and Sonnet/Opus aliases unavailable. No alias/provider claim is made. No second opinion or subagents were dispatched.

This is the original review of the head above. Subsequent fixes do not change this review's identity or retroactively discharge its findings.

## Strengths

- The implementation composes the shipped discovery, collection, transformation and publication boundaries. Collection retains original acquisition settings and raw bindings; ETL uses current pinned parser/schema settings.
- Original parent/session/listing provenance is checked through actual ancestor traversal and immutable receipt bytes. Singleton projections preserve incomplete-parent history, and malformed legacy units are isolated without adopting recursive projections.
- Current completion, historical captures and unfinished publication repair are distinct. Repair obligations retain their original call authority and affected quarters; resolutions verify exact source membership and publication artifacts.
- Member receipts validate child order, input/output chains, context, versions, outcome, progress flags, gaps and quarter captures. Whole-source parser quarantine remains strict, while failed transport prefixes do not become terminal source quarantine.
- The installed proof verifies the complete applicable lock graph, exact installed distribution set, source/wheel/installed bytes and a real transitive-version refusal. Native proof exercises twelve actual process deaths and recovery boundaries.
- I inspected the retained final command outputs: 618 tests passed in 884.423 seconds; build/help/version/compile/whitespace/native/installed commands exited 0. Those results are valid evidence for the reviewed head, although the probes below expose missing refusal cases.

## Issues

### Critical (Must Fix)

None identified.

### Important (Should Fix)

1. **[P1] Discovery failures can be omitted from validated selection/report classification**

   File: `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/results.py:147`, with the checked-child read at line 157 and parent validation at line 189 (line numbers at reviewed head).

   `_validate_selection` decodes `discovery_error`, reads any durable discovery child, and validates the parent/required-directory capture, but does not require the authoritative discovery gaps to remain in `selection['gaps']`. `_validate_report` subsequently requires only the gaps present in that selection. Consequently, a coherently altered selection can suppress discovery failure and produce an accepted success classification.

   I confirmed two cases using actual guarded fixture discovery:

   - `AcquisitionState.finish_discovery` raised `RuntimeError`, leaving a begun child without a durable result. Selection contained `halted=True`, an `internal_error` discovery error, no parent and no members. Removing only `selection['gaps']` allowed `freeze_selection -> run_workflow -> write_workflow_result -> read_workflow_result` to accept `no_new_sources`, with zero report gaps.
   - An empty daily Q4 listing returned 404, producing a durable checked discovery result and a parent with one `discovery_failed` required directory. Removing only `selection['gaps']` again produced an accepted `no_new_sources` report; the failed directory remained in the report.

   This violates the requirement that `no_new_sources` requires successful required listings, and undermines the report's role as checked coverage authority.

   **Fix:** Bind discovery gaps and failure classification to the checked durable result or validated original unfinished-child capture. Retain required-directory failure authority in historical selection/report validation. Refuse complete outcomes when discovery is absent, halted or incomplete. Cover both durable-result and missing-result omission cases; an absent-parent check alone does not address the durable 404 case.

2. **[P2] Receipt-less pending members can fabricate progress and quarter operations**

   File: `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/results.py:333` (line number at reviewed head).

   The `descriptor is None` branch checks only that `child_refs` is empty and the outcome belongs to `PENDING`. It does not enforce the actual undispatched shape emitted by the runner.

   A focused probe created an actual deadline-undispatched two-member report, changed the first pending member to `downloaded=True` and `transformed=True`, and recomputed the reducer counters. Both writing and reading the report accepted `receipt=None`, `child_refs=()`, `snapshot_ref=None`, `transformed_ref=None`, `downloaded_sources=1`, `transformed_sources=1`, with zero Processing rows.

   Neighboring probes also accepted a nonexistent `transformed_ref` and a fabricated `published` quarter, increasing `published_quarters` to 1 without a publish child or manifest read. Wrong selected source/parent identities were already refused, and a nonexistent snapshot reference was refused.

   This does not make the pending source complete, but it permits durable reports to invent downloaded, transformed and published progress.

   **Fix:** Require the canonical undispatched shape for receipt-less members: no progress flags, snapshot/transformed/child references or quarter outcomes; exact selected identity/current versions; and the appropriate pending/deferred error authority. Add rejection tests that recompute structural counters so the tests exercise evidence validation rather than only reducer consistency.

### Minor (Nice to Have)

None raised.

## Recommendations

Fix both authority omissions before technical acceptance. Keep the existing historical object-only replay and index-repair behavior: corrections should validate captured original evidence without making completed reports depend on mutable current discovery or publication indexes.

Run the focused refusal regressions first, then refresh the relevant workflow tests and final verification/proof artifacts because runtime report validation will change. Preserve the original successful and failing evidence.

## Assessment

**Ready to merge? With fixes.**

**Reasoning:** The source processing, strict quarantine, publication repair and provenance architecture are sound, and the retained offline verification is substantial. The two reproduced report-validation gaps must be resolved because they allow durable coverage/progress claims that contradict their retained child evidence.

Review covered all changed runtime modules, CLI/discovery changes, their shipped ETL/reader interactions, workflow test suites and harnesses, proof/lock verifier, operator documentation, specification/plan constraints and retained final command evidence. I reviewed in separate passes and ran only focused network-guarded probes in temporary directories with bytecode writes disabled. No checkout, index, HEAD, branch or worktree changes were made during the review; no subagents, network access or broad test reruns were used. These review records were retained later at the controller's explicit request, with no runtime changes.

The external gates remain separate: owner review of final actual coverage and the disposition of the absent former planning checkout are pending. Task 10's explicit owner approval does not discharge those gates. All 22 Stage 7 checks remain `reserved/not_run`; this review authorizes no merge, push, cleanup, deployment or activation.

## Focused probe reproduction and observed outputs

The original probes ran as quoted Python heredocs through the execution tool from `/Users/lowell/.codex/worktrees/sec-edgar-stage4-plan5/sec-edgar`, using `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -`. Each explicitly inserted only the repository's test/source paths, installed `network_guard`, and constructed temporary fixture state under `/tmp` through `TemporaryDirectory`. All four commands exited 0. Temporary state was cleaned up normally; no separate on-disk probe script or artifact was retained at review time. The tool-call transcript retains the original commands/outputs. The following reproduction notes faithfully describe those commands; they are not a claim that they were rerun after the reviewed head changed.

Common prelude:

```python
import sys
sys.path[:0] = ['packages/sec-edgar-ingest/tests', 'packages/sec-edgar-ingest/src']
from network_guard import install
install()
import tempfile
from pathlib import Path
from unittest.mock import patch
from test_workflow_runner import RunnerTests
from support_workflows import CommandHarness, simple_pack
from sec_edgar_ingest.workflows.runner import select_work, run_workflow
from sec_edgar_ingest.workflows.results import freeze_selection, write_workflow_result, read_workflow_result
```

### P2 original progress probe

Create a temporary `CommandHarness(root, simple_pack(root/'pack'))`. Use `RunnerTests().prepared(h, run='review-progress')` to obtain the actual pinned context, intent and dispatcher. Run `select_work`, then `freeze_selection`. Patch only `sec_edgar_ingest.workflows.runner.datetime.now` to `context.deadline + timedelta(seconds=1)` while invoking `run_workflow`; the result is an actual deadline-undispatched two-member report. Use `dataclasses.replace(report.members[0], downloaded=True, transformed=True)`; retain the second member, recompute `outcome, counts` with `summarize(members, report.gaps, report.intent['discovered_sources'], report.intent['unresolved_before'], context.command, report.intent['already_complete_sources'])`, then replace only report members/outcome/counts. Invoke `write_workflow_result` and `read_workflow_result` on that altered report. Close harness in `finally`.

Exact observed stdout:

```text
{'accepted': True, 'receipt': None, 'child_refs': (), 'snapshot_ref': None, 'transformed_ref': None, 'downloaded_sources': 1, 'transformed_sources': 1, 'processing_count': 0}
```

### P2 neighboring fields probe

Repeat the actual deadline-undispatched setup with run `review-neighbors`, then independently replace the first member's fields and recompute outcome/counts as above. Call `_validate_report` on each variant (do not reuse a committed report path):

- `transformed_ref='worksets/sec/transformed/sha256=' + 'a'*64 + '/workset.json'`: accepted.
- `quarters=(PublicationResult('2026Q3', 'published', 'a'*64, 'published/sec/2026Q3/generation=' + 'a'*64 + '/manifest.json', None, 0),)`: accepted, `published_quarters=1`.
- `source=report.members[1].source`: refused with `Conflict: report member provenance differs from selection`.
- `parent_ref='worksets/sec/source/sha256=' + 'a'*64 + '/workset.json'`: refused with the same provenance Conflict.
- `snapshot_ref='worksets/sec/snapshot/sha256=' + 'a'*64 + '/workset.json'`: refused with FileNotFoundError.

For both accepted variants counts remained `complete_sources=0`, `pending_sources=2`, `failed_sources=0`, `discovered_sources=2`, `downloaded_sources=0`, `transformed_sources=0`, `quarantined_sources=0`, `unchanged_quarters=0`, `awaiting_approval_quarters=0`; only the quarter variant had `published_quarters=1`.

### P1 original missing-result discovery probe

Create `CommandHarness(root, simple_pack(root/'pack', empty=True))`. Use `RunnerTests().prepared(h, run='review-discovery', command='daily')`. While calling `select_work`, patch `AcquisitionState.finish_discovery` to raise `RuntimeError('real no-result discovery')`. Inspect the returned original selection, then change only `selected['gaps']=[]`. Invoke `freeze_selection`, `run_workflow`, `write_workflow_result`, then `read_workflow_result`. Close the harness in `finally`.

Exact observed stdout:

```text
original {'halted': True, 'gaps': [{'code': 'internal_error', 'message': 'real no-result discovery', 'retryable': False, 'source_id': None, 'details': {'type': 'RuntimeError'}}], 'discovery_error': 'internal_error', 'members': 0}
accepted {'outcome': 'no_new_sources', 'gaps': [], 'source_workset_ref': None, 'child_calls': 1}
```

### P1 durable failed-listing probe

Generate `simple_pack(root/'pack', empty=True)`. Decode its manifest, change only the status of each response for `BASE + 'daily-index/2026/QTR4/index.json'` to 404, and write canonical manifest JSON. Create the actual `CommandHarness` with this pack. Use `RunnerTests().prepared(h, run='review-listing-gap', command='daily')`, then call `select_work`. Inspect original selection; change only `selected['gaps']=[]`. Invoke `freeze_selection`, `run_workflow`, `write_workflow_result`, then `read_workflow_result`. Close harness in `finally`.

Exact observed stdout:

```text
original {'halted': False, 'gaps': 1, 'parent_present': True, 'failed_directories': 1}
accepted {'outcome': 'no_new_sources', 'gaps': 0, 'failed_directories': 1}
```
