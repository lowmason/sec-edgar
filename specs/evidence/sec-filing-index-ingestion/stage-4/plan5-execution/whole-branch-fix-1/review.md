# Independent scoped re-review: whole-branch fix 1

Reviewed base: `fc938385de277ef1cb1d5b5862a606ecb7244d9b`.
Reviewed head: `6528a4e7596ed55078cbe31892f448b3075773b3`.
Reviewer: the original independent `whole_branch_review` Codex agent. Native code-reviewer role and Sonnet/Opus aliases are unavailable; no provider/tier substitution claim is made. No second opinion or subagents were dispatched.

Scope: the two original findings, their corrections, and adjacent discovery/member/report authority and historical replay interactions. This is a scoped re-review, not a repetition of the original whole-branch review. The original report retains its original base/head identity. I read the complete supplied fix diff in bounded passes, the original review and updated implementation report, the changed runtime/test code, relevant checked-child and terminal-capture boundaries, and retained red/final scoped command outputs. HEAD matched the stated implementation commit. The tracked implementation was unchanged; the already-retained review/fix evidence directories were untracked.

## Strengths

- Discovery failure classification is now checked against original evidence. Durable discovery must retain every original structured gap and the exact computed halted flag. A report with a complete outcome also requires a non-halted selection, a captured parent whose discovery is complete, and successful required directory outcomes.
- Missing-result discovery is captured against the actual begun Attempt at first selection freeze. Exact structured errors, child context, checked call and command are bound into immutable original terminal evidence. Historical reads use that capture instead of a mutable Attempt or a later result of the same child.
- Receipt-less members now compare equal to the runner's entire canonical undispatched MemberResult. This checks selected source/parent identity, current versions, all false progress flags, absent snapshot/transformed/child references, empty quarter operations, and one exact workflow_deferred gap.
- Tests construct real fixture discoveries and deadline-undispatched work. Coherent substitutions and recomputed counters exercise evidence authority rather than relying on a reducer mismatch or first-write collision. Historical coverage actually retries the same original discovery child successfully, then deletes mutable Attempt/discovery/workflow indexes before reopening the original report and selection.
- The fix remains within the four owned runtime/test files. Public APIs and selection/report/member schemas are unchanged; original discovery terminal.json is a transitive immutable evidence extension using the existing terminal-capture shape.

## Original findings

### P1 discovery failure omission: ADDRESSED

Correction: `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/results.py:108`, `:193`, `:299`, `:349`, and `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/runner.py:177` (at reviewed head).

The original no-result wrapper is retained in selection gaps, with every original structured error. First freeze validates the proposed error against the persisted exact Attempt; subsequent validation checks original immutable terminal bytes, context and command. Durable child gaps and halted classification cannot be omitted or changed. Complete report outcomes are forbidden for absent/halted/incomplete discovery and failed required directories. This covers both original reproduced omissions, including the durable empty-listing 404 case.

The additional late-result correction is necessary and sound: a later successful result for the same original child does not replace the frozen failed selection's parent, gaps or classification. The report durable-child loop skips that discovery result only after the selection's immutable original failure authority has been validated. Missing/corrupt terminal or checked-call/command evidence therefore fails closed rather than falling back to current state.

### P2 receipt-less fabricated progress: ADDRESSED

Correction: `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/results.py:400` (at reviewed head).

Entire-value comparison to canonical pending evidence closes the original downloaded/transformed flags and adjacent invented transformed-reference/publication-quarter cases. It also refuses alternate pending-family outcomes, absent/changed deferral gaps, mismatched selected identity and versions. Normal receipt-bearing processing remains on its original checked receipt path. The canonical pending construction agrees with the runner's actual undispatched branch.

## Issues

### Critical (Must Fix)

None identified in the scoped correction and adjacent interactions.

### Important (Should Fix)

None identified in the scoped correction and adjacent interactions. Both original Important findings are addressed.

### Minor (Nice to Have)

None raised.

## Evidence and verification limits

I inspected the actual retained final scoped command output, not merely the implementation report's summary:

| Evidence | Observed result |
| --- | --- |
| `whole-branch-fix-1/13-final-results-scoped.txt` | exit 0; 20 results tests passed in 78.543 seconds |
| `whole-branch-fix-1/14-final-runner-scoped.txt` | exit 0; 21 runner tests passed in 175.911 seconds |
| `whole-branch-fix-1/15-cli-scoped.txt` | exit 0; 6 CLI tests passed in 44.493 seconds |

Total: 47 scoped tests passed against the final production implementation. These files retain exact `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p <test file> -v` argv and complete output. The reviewer did not rerun them.

I also inspected genuine behavioral reds: `01-p1-red.txt` has both original omission assertions fail with Conflict not raised; `05-p2-red-authority.txt` has all seven independent schema-valid/recomputed-counter variants fail their refusal assertions; `11-p1-later-result-red-fixture-corrected.txt` shows a later successful same-call discovery invalidating the original failed report before the historical correction. Earlier fixture/collision/message-only failures remain documented in the implementation report and are not counted as behavioral proof. No additional probes were needed or run during this scoped review.

The original 618-test/build/native/installed proof belongs to the original reviewed head. It is not refreshed evidence for this runtime correction. Controller-managed full-suite, build and native/installed proof refresh remains required after scoped acceptance. No claim that those final checks have already run is made here.

## Recommendations

Proceed with the controller's refreshed final full-suite/build/native/installed verification. Preserve both the original review and this scoped report, including the genuine reds and intermediate limitations. Treat discovery terminal.json as required transitive original report authority when retaining evidence; do not replace it with a current child result or mutable index lookup.

Owner review of actual final coverage and the disposition of the absent former planning checkout remain pending external gates. Task 10 owner approval does not waive them. All Stage 7 checks remain reserved/not_run. This review authorizes no merge, push, worktree cleanup, deployment or activation.

## Assessment

**Ready to merge? Yes, technically for this scoped correction, subject to refreshed final verification and the separate external gates above.**

**Reasoning:** Both original report-authority omissions are closed, and the adjacent historical replay/index-repair interactions preserve immutable original failure evidence. No new Critical or Important issue was identified in the complete correction diff; overall integration remains contingent on controller verification and owner gates.

No runtime/source, index, HEAD, branch or worktree mutation, network access, subagent dispatch or broad test execution occurred during this re-review. These two identical review records were created afterward at the controller's explicit bookkeeping request.
