# Plan 3 execution checkpoint — owner reconciliation required

Approved Plan 3 was executed through subagent-driven-development in the isolated
`codex/sec-edgar-stage-3` worktree. Offline implementation and review repairs are
verified. **Stage 3 acceptance remains BLOCKED**, because three complete retained
sources contain conflicting observations under the approved CIK/archive-path key.
This checkpoint does not mark the plan or roadmap complete or retire the work.

Reviewed delivery HEAD: `78a1d3151c72fca586b261f7b33830505e0e77f6`.
Production code/docs HEAD: `2343f39f0e21adc2ad401a9346a8c9ffa0509040`.
Initial base/primary HEAD: `5f90a2116eab21525e88a02d0988567e71d95967`.
A following checkpoint-only commit retains these receipts; package source and
README hashes remain the reviewed/tested values.

## Implementation and review disposition

Tasks 1–6 implement typed immutable contracts, strict complete-source parsing,
Parquet observations, conservative quarterly catalog/deltas, validated immutable
candidates, conditional pointer publication, captured readers, and raw-only
transform/publish commands with exact Attempt resumption and separate results.
Task 7 capability proofs pass; its retained-source acceptance step remains open.
Task-scoped reviews and repair evidence are preserved in the historical SDD tree.

The [whole-branch review](final-review.md) found two Important recovery gaps and
one Minor runbook issue. The [final scoped re-review](final-re-review-1.md) marks
all three ADDRESSED, with no new Critical, Important or Minor findings. Quarter
discovery now validates authoritative captures even without receipts. Ordinary
post-CAS repair failures retain truthful quarter captures and leave exact retries
resumable. The runbook uses a separate supported ETL fixture configuration and
its actual seeded transform/publish sequence passed.

Named task-reviewer and code-reviewer roles were unavailable when attempted;
default agents received the complete read-only review contracts. Recorded model
mapping for unavailable aliases: cheap → gpt-6-luna, standard → gpt-6.1-sol,
capable → gpt-6-astra. The final review used the capable route. Separate Codex CLI
second opinion was SKIPPED under requesting-code-review/codex-review.md's rule
for a Codex controller; no such review is claimed. [Review-package receipts](review-packages.json)
retain exact ranges, lengths and hashes. Packages remain in active W and are
regenerable using subagent-driven-development/scripts/review-package with those
recorded ranges. No HEAD~1 substitution was used.

## Current offline evidence

| Check | Actual result |
| --- | --- |
| Full package check | 452 test records OK; 163.537s test / 164.112s wall; wheel/sdist, help/version, compile and scoped whitespace pass |
| Raw lifecycle and process sequence | Exit 0; 5.989s wall; three real races and four forced-death boundaries |
| Isolated installed wheel | Exit 0; 9.875s wall; all 28 Python sources and current README metadata equal |
| Documented transform → publish → captured read | Exit 0; 0.361s wall; exact returned transformed ref used; one expected Q4 filing |
| Controller preservation/source/evidence audit | Exit 0; no failures |

See [combined proof report](../final-review-fix1/report.md),
[current verification](../verification.md), and the
[controller audit](controller-verification/audit-final-fix1.json).
The current 111,195-byte wheel SHA256 is
`eb8bb3b318b3b1a4fe1983291efb92161e22fac998f86230b5f2b7f3cf15c3ab`.
New proof inventory: 2,070 payloads / 15,471,496 bytes, SHA256
`606a2ea013e7695d8fbf6029a00f30016c23dc2829ec882d218a29a11a10be14`.
Historical proof remains exact: 7,525 payloads / 72,546,066 bytes, inventory SHA256
`4554adb90acdda3e44bffac01bb878d3391d4ae523e0c4439aa4e1ab2c612b6b`.

Scoped implementation/prose whitespace checks exit 0. Full staged historical
proof checks exit 2 for preserved context whitespace, including the two exact
copied owned diffs in the latest proof; original failed outputs are retained.
There is no claim that the complete evidence diff is whitespace-clean. Controller
report-shape inspection initially used an incorrect context field; its KeyError
and successful corrected inspection are disclosed in
[inspection notes](controller-verification/inspection-notes.json). Actual product
and proof commands passed.

The preservation preflight and final audit verify 19,088 protected primary records,
294,399,711 existing bytes, four absent legacy package paths, original Git status
and HEAD, original roadmap bytes, approval/planning evidence and retained sources.
Primary was read-only. No protected deletion was committed, reset, stashed or
restored; no retained bytes were normalized. The active worktree is preserved.

## Unresolved retained-source acceptance

Two independent complete scans agree on source hashes, receipt bytes, row counts,
selected rows, date bounds, quarter counts and all 51 conflicting observations
across 970,622 parsed rows. Production transformation actually quarantines the
three conflicting sources before an accepted Processing reference or pointer.

| Receipt | Parsed rows | Conflicting observations | First physical conflict line |
| --- | ---: | ---: | ---: |
| SEC-0141 / 2010Q1 | 300,561 | 21 | 6,580 |
| SEC-0142 / 2015Q1 | 318,647 | 24 | 87,808 |
| SEC-0143 / 2026Q3 | 302,315 | 6 | 40,292 |

There are 45 form_type-only and 6 company_name-only disagreements for the same
CIK/archive path; filing dates and accession identity agree. No alternate key,
normalization, winning-row rule, exemption or acceptance amendment was invented.
The other seven receipt scans pass, including the documented root-quarterly
byte alias; this does not establish complete retained-range acceptance.
[Actual specimen report](../verification/specimens/report.json) and historical
preflight/transform-refusal artifacts retain all observed facts. The original
acceptance command remains exit 1 and was not rerun for unrelated recovery fixes.

The owner must decide whether to retain strict quarantine with an explicit
acceptance-criterion amendment, or specify a revised identity/conflict policy
for implementation and verification. Until that question is answered, the plan,
roadmap, completion/retirement chain, integration and cleanup remain held.
Writing-plans' resolve-before-defer gate requires answers before plan markup,
appending or retiring. Approved Stage 3 spec §8 makes invalid retained rows a
reported blocker that cannot be bypassed to stamp completion.

All live SEC, Azure, authentication, compute, provisioning, deployment, image
build and fetch authorizations remain closed. Evidence is native macOS ARM64 /
Python 3.14.0; all 22 later Stage 7 integrated checks remain reserved. No Linux
worker, live Azure identity/ETag behavior, deployed capacity or history-wide
acceptance is established by these offline proofs.
