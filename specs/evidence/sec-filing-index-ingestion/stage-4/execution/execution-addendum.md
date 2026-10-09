# Stage 4 execution corrections proposed after ultra review

This addendum supplements the exact approved Plan 4 without editing its source or approval snapshots. It preserves the approved specification, offline scope, acceptance boundaries, dependency pins, seven-task order, and the already owner-approved move of `current_complete()` into Task 2.

Review: `/private/tmp/sec-edgar-stage4-ultra-plan-review.md`.
Implementation baseline: `775866aae5cc2c9cf974be6a614716a14548f081`.
Status: owner approved on 2026-10-07 by direct reply, "Use the correction addendum (recommended)", resolving conflicts between plan examples and approved specification. This is an execution correction, not renewed scope approval.

## Corrections

1. **All affected quarters (Tasks 2, 4, 6).** `current_complete()` must apply the existing publisher's affected-quarter rules, including formerly affected quarters retained in active manifests. New observation `quarter_counts` alone cannot suppress a partially published replacement. Preserve exact binding, Processing identity, observation and manifest validation. Regression: a nonempty quarterly replacement moves Q3 rows into Q4; Q4 publishes while Q3 is refused. Completion stays false and a subsequent daily run retains backlog and cannot report `no_new_sources`.

2. **Transport retry evidence versus whole-source quarantine (Tasks 3, 6).** Keep the strict MemberResult invariant. Derive source quarantine from terminal whole-source refusal; do not convert collection's retained failed retry-body count into source quarantine when a later download succeeds. Retain all original request/body/error evidence and retry accounting. Regression: truncated retry prefix followed by valid body completes and publishes, workflow quarantined-source count remains zero, and retained prefix evidence remains readable. Separate conflicting-duplicate fixtures must still refuse the entire source without accepted observations/publication.

3. **Outstanding publication repair (Tasks 2, 3, 4, 6).** A committed pointer remains data authority, but does not erase a known unfinished publish/ancillary repair obligation. Pending selection must either repair through the existing checked command boundary or retain the source explicitly unresolved. Preserve exact retry; an expired original attempt remains unchanged and a fresh valid attempt can use existing no-op publish/repair behavior. Regression: ordinary post-CAS repair failure yields no child result or member/workflow completion; a fresh workflow cannot claim no-new/success while repair remains outstanding. Repair must not advance the pointer again.

4. **Parent-command child namespace (Tasks 3, 5, 6).** Include the workflow command in deterministic child identities, together with run/attempt/step identity. Regression: backfill and daily sharing run, execution, attempt, config, deadline and fixture pack use separate discovery child identities and exact replay stays within each command. Changed inputs at an exact path still refuse.

5. **All-quarantined aggregate (Tasks 1, 4, 6).** Keep baseline publication gaps, but distinguish gaps caused solely by the selected quarantined sources from independent directory/missing-source failures. A fresh backfill with successful listings and every selected source quarantined must return `quarantined`/exit 7, as the approved spec requires; mixed progress or independent missing coverage remains incomplete. Regression: no preexisting pointer, all selected raw sources contain conflicting duplicate rows, zero complete sources, exact failed/quarantined counts, retained gaps and no accepted observations/pointers. Preserve mixed valid/invalid behavior.

6. **Complete locked installed dependencies (Task 7).** Reuse existing offline proof's frozen-lock export and hash-bound cached installation, then install the reviewed wheel with `--no-deps`. Bind installed distribution versions and complete dependency inventory to the accepted lock/hash. Reject a transitive mismatch even when all five direct pins match. Preserve isolated imports, source-byte equality, wheel SHA, create-only evidence and exact inventory membership. Missing cached artifacts remain blockers; no fetching or changing pins.

## Mandatory elaborations already required by approved prose

- Reopen actual parent listing receipts/bytes, preserve the required discovery ledger and immediate directory provenance, and never relabel failed parent discovery complete through a projection.
- Validate the exact binding winner returned by `bind_once`; refuse divergent existing pins without overwriting them.
- Validate decoded Processing source, snapshot, parser and schema identities against the requested identity, not only the state lookup key.
- Decode and validate complete member receipts against exact children and immutable publication captures; historical successful invocation receipts cannot bless new refresh inputs or versions.
- Validate canonical frozen intent, saved context/index descriptors, selection and report captures on replay; return completed historical reports after deadline before constructing senders.
- Capture immutable before-dispatch evidence for skipped already-complete sources in selection and validate it on report read.
- Accumulate all child gaps, preserve fatal stop behavior and resumable repair, isolate corrupt legacy provenance, and prevent recursive projection reconstruction.
- Preserve the shipped parser's zero-row refusal; illustrative zero-output contract support does not authorize empty IDX acceptance.

## Scope and execution

No approved snapshot, retained Stage 3 evidence, primary bytes, ignored primary roadmap or required legacy absence is changed. SEC-0141/0142/0143 remain exact whole-source refusals with 21/24/6 conflicts. All live-access authorizations remain closed and all 22 Stage 7 checks remain reserved/not_run. This addendum authorizes no merge, deployment, schedule activation or later-stage work.

After resolving this interpretation, copy this addendum and the read-only review into separate execution evidence, append affected task briefs and the progress ledger, then resume Task 1 red/green and the ordered review gates. These static findings are not newly executed test failures. Each correction must receive meaningful implementation regression proof before acceptance.
