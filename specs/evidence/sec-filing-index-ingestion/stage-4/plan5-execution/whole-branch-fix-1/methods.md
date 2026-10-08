# Whole-branch fix 1 implementation report

Approved scope: whole-branch findings P1 and P2 only, in the isolated Stage 4 Plan 5 execution checkout. Base was fc938385de277ef1cb1d5b5862a606ecb7244d9b. Owned code/test commit is 6528a4e7596ed55078cbe31892f448b3075773b3 (`fix: bind workflow reports to discovery and pending authority`). Only workflows/results.py, workflows/runner.py, test_workflow_results.py and test_workflow_runner.py are committed. The tracked checkout is clean; fix evidence and controller-owned whole-branch-review evidence remain untracked for the controller.

## Confirmed causes and changes

P1: selection validation decoded gaps/errors but never required the actual checked discovery errors to be retained. Real empty daily discovery with finish_discovery raising RuntimeError, and real empty daily Q4 listing HTTP 404, both accepted a selection differing only by gaps=[] before the fix. Each now refuses. Durable discovery requires all original child gaps and the exact computed halted classification. Report success/unchanged/no_new_sources requires an immutable parent with complete discovery and successful available/no_new_sources required listing outcomes. Missing and halted discovery cannot receive those outcomes.

For original missing-result discovery, first selection freeze calls unfinished_child against the actual saved Attempt. Its exact context, structured errors and checked call are validated against the proposed terminal error. The original wrapper error and all original structured gaps must remain in selection.gaps; select_work now includes that wrapper. Freeze retains canonical {context, terminal_error} at the original child result-directory terminal.json, using the existing member-processing capture schema/pattern. Historical validators read that immutable capture and original checked command rather than current Attempt/session indexes. A later successful result for the same original child does not replace the frozen failure's outcome, parent or gaps, and is not an optional new dependency of historical report reads. The test actually repairs that same original discover call and then deletes Attempt, DiscoverySession, WorkflowChildCall and WorkflowAttempt rows; exact report read and selection replay still pass.

P2: receipt=None formerly accepted any PENDING outcome with no child_refs, allowing reported acquisition/transform/publication claims without dispatched work. Validation now compares the entire receipt-less member to the runner's canonical undispatched MemberResult: exact selected member/source/parent and current versions; pending; no snapshot/transformed/child references, flags or quarters; and the exact workflow_deferred gap. Seven schema-valid mutations recompute report outcome/counters before shared read/write validation, covering downloaded, downloaded+transformed, a fabricated transformed reference, a fabricated published quarter, deferred outcome, absent gap and altered gap text.

Public APIs and selection/report/member persisted schemas are unchanged. The sole internal persistence extension is the original discovery terminal.json capture, already used for original unfinished member child history. It lives in the retained original runs/sec namespace and remains necessary transitive immutable report authority. No mutable latest lookup or provider operation was introduced.

## Methods and complete retained evidence

All execution used cached dependencies with `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests`, with the exact -p/-k/-v arguments stored as argv arrays in every output. All stdout/stderr are merged and retained in full with actual subprocess exit codes. Commands ran from /Users/lowell/.codex/worktrees/sec-edgar-stage4-plan5/sec-edgar. No network, provider, live, native, installed, build or whole-suite execution occurred. No protected specimen/proof/approved-plan bytes were modified.

Evidence root: specs/evidence/sec-filing-index-ingestion/stage-4/plan5-execution/whole-branch-fix-1/.

| File | Actual result and interpretation |
| --- | --- |
| 01-p1-red.txt | exit 1; both real P1 gap-omission refusal assertions failed (Conflict not raised), before production change. |
| 02-p1-green.txt | exit 0; both original P1 regression cases passed. |
| 03-p2-red.txt | exit 1; downloaded claim accepted; an invalid quarantined/pending mutation then failed the existing MemberResult schema. Setup limitation, not seven-case red evidence. |
| 04-p2-red-valid-variants.txt | exit 1; first invalid report accepted/written; its immutable report collision masked later variants and prevented canonical write. Setup limitation preserved. |
| 05-p2-red-authority.txt | exit 1; all seven schema-valid mutations independently accepted by the shared validator, with recomputed reducer outcome/counters. Genuine P2 behavioral red. |
| 06-p2-green.txt | exit 0; canonical deadline report and all seven refusals passed. |
| 07-results-scoped.txt | exit 1; 19/20 passed; existing synthetic transplanted-receipt fixture omitted its own no-call discovery_error gap. |
| 08-runner-scoped.txt | exit 1; 20/21 passed; new substitution fixture had not coherently replaced its wrapper gap, so it refused earlier than the asserted persisted-Attempt boundary. |
| 09-results-scoped-fixture-corrected.txt | exit 0; 20 tests passed after synthetic fixture correction, before final late-result refinement. |
| 10-p1-later-result-red.txt | exit 1; same incoherent wrapper fixture failed before reaching added late-result history assertion. Not late-result behavioral evidence. |
| 11-p1-later-result-red-fixture-corrected.txt | exit 1; actual same-call successful discovery repair invalidated original frozen failure history. Genuine additional P1 red. |
| 12-p1-later-result-green.txt | exit 1 despite filename; late-result/deletion history passed, but durable-error substitution refused with a different Conflict message than an overly specific new regex. Regex corrected to assert refusal. |
| 13-final-results-scoped.txt | exit 0; 20 tests passed in 78.543s against final production implementation. |
| 14-final-runner-scoped.txt | exit 0; 21 tests passed in 175.911s, including original two P1 cases, actual Attempt/error substitution, late same-child repair, mutable-index deletion and seven P2 mutations. |
| 15-cli-scoped.txt | exit 0; 6 directly affected workflow CLI tests passed in 44.493s. |
| 16-self-review-checks.txt | diff whitespace check exit 0; owned diff/stat and exact status retained. |
| 17-owned-code-commit.txt | explicit four-file staging, staged whitespace check and owned code/test commit all exit 0. |
| 18-post-commit-checks.txt | exact commit/hash/stat; diff check exit 0 and tracked-clean status. |

The P2 mutant tests call the shared _validate_report directly so first-write immutable collisions cannot falsely make later variants appear refused. The canonical runner report then exercises normal writer and reader. Existing synthetic result fixtures were corrected only to retain their own actual no-call/missing-result discovery errors and canonical deferred shape; transplanted-receipt tests still reach receipt validation. No production assertions were relaxed to satisfy test setup errors.

## Verification and handoff

Final scoped validation: 47 tests passed across results (20), runner (21) and CLI (6), each process exit 0. Self-review verified immutable original context/call/command binding; actual first-freeze Attempt comparison; exact retained error/gap classification; historical independence from mutable indexes and later child results; canonical receipt-less source/progress shape; complete-listing requirement; and four-file ownership. Whitespace checks passed before and after commit.

Applied clean-code judgments: named effectful capture/validation helper (N7), named expected_halt and canonical pending evidence (G19), cohesive original-discovery terminal authority helper (G30), empty-discovery and deadline boundary coverage (T5), and neighboring substitution/history mutations (T6). No adjacent cleanup was performed.

No remaining scoped implementation defect found in self-review. Independent rereview and controller-managed refreshed full/build/native/installed verification remain outstanding; this report makes no broader branch readiness claim. Controller owns progress/deviation ledger updates, evidence hashing/commit and integration disposition. No merge, push or cleanup was performed.
