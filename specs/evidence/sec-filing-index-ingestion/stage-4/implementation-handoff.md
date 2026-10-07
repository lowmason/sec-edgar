# Approved Stage 4 execution handoff

The text below is a prompt for a fresh execution session. The planning chats can be archived; execution needs the saved files, not their conversation history.

---

Work in `/Users/lowell/Projects/sec-edgar`. Implement **Stage 4: Backfill and daily catch-up workflows** using the approved specification and Plan 4. The owner approved this exact scope on **2026-10-07 (America/New_York)**. Approval is already granted for offline implementation; do not ask for it again merely because the original document headers still say PROPOSED.

Read these before acting:

- `/Users/lowell/Projects/sec-edgar/specs/sec-filing-index-ingestion-stage-4-spec.md`
- `/Users/lowell/Projects/sec-edgar/specs/plans/4-sec-filing-index-ingestion-stage-4-spec.md`
- `/Users/lowell/Projects/sec-edgar/specs/evidence/sec-filing-index-ingestion/stage-4/approval/owner-approval.json`
- `/Users/lowell/Projects/sec-edgar/specs/sec-filing-index-ingestion-roadmap.md`
- `/Users/lowell/Projects/sec-edgar/specs/evidence/sec-filing-index-ingestion/stage-4/planning-validation.json`
- `/Users/lowell/Projects/sec-edgar/specs/evidence/sec-filing-index-ingestion/stage-4/planning-reconciliation.json`

The receipt binds read-only, create-only approved copies under `/Users/lowell/Projects/sec-edgar/specs/evidence/sec-filing-index-ingestion/stage-4/approval/`. Verify the source files and those copies against these approved SHA-256 values before execution:

- Spec: `5b822a4113eaa18c53a18ae71f244d6b69d2abd9e533381a69644e4b88cd1b0a`
- Plan 4: `d23d62c965f51a4af9a89edd615cc77ed267b58601875f06bcd27cc339c2508c`
- Roadmap at approval: `0101934eadf0ca3241b03a458c80ec300012430875c44522410836ab6c0ecc03`
- Approval receipt: `1a4beabfe15f8d39bb710ba7f92fb9ac1ea60eafc926a8f28905ad6c2ea176bc`

If the current documents or checkout have drifted, inspect and preserve the new bytes before proceeding. Use the approved snapshots as the approval authority, but do not overwrite later edits to make hashes match. The approval receipt supersedes the preserved PROPOSED headers only for this exact offline scope. The snapshots retain original relative links, so read the source-path documents for link navigation.

## Checkout and preservation

PR #3 is merged. Primary `main` and local `origin/main` are both at `fe95642bddf006f3d2d6cb3ccc57e595d75dc4cd`. Primary `main` was safely fast-forwarded from `5f90a2116eab21525e88a02d0988567e71d95967`; do not repeat that reconciliation. The index was empty at handoff. Stage 4 has **no implementation changes, tests or builds executed yet**. Its spec, plan and planning/approval evidence are untracked in the primary checkout; the roadmap is ignored.

Perform a fresh preservation preflight before any checkout/worktree mutation. Inspect tracked, untracked and relevant ignored drift, record hashes and required absences, make verified retained copies, and preserve all historical inputs and evidence. Existing preservation roots are:

- `/private/tmp/sec-edgar-stage3-merged-closeout-hhgufen8/` — original closeout receipt and primary inventory.
- `/private/tmp/sec-edgar-stage4-reconcile-9mbg9qog/` — fresh pre-fast-forward inventory, `retained/`, `displaced-originals/` and fast-forward receipt; **19,089 files / 294,547,731 bytes** verified.
- `/private/tmp/sec-edgar-primary-reconcile-1t9zru9x/` — independent retained copy, Stage 3 authority audit, prior-preservation audit and `plan-review-final.json`.

Do not remove or reuse these roots as build output. The four files below must remain **absent from the primary checkout**:

```text
packages/sec-edgar-index-ingest/README.md
packages/sec-edgar-index-ingest/pyproject.toml
packages/sec-edgar-index-ingest/src/sec_edgar_index_ingest/__init__.py
packages/sec-edgar-index-ingest/src/sec_edgar_index_ingest/py.typed
```

Never use `git add -A` or stash/reset/restore in the primary checkout. Do not stage the four primary deletions, the historical untracked Stage 3 originals, or unrelated ignored/untracked files. Do not rebuild primary `dist/`: its wheel is historical Stage 2 output, distinct from the retained Stage 3 installed proof. Preserve the ignored roadmap's historical, reconciled and approval bytes.

Use `using-git-worktrees`. Inspect current attached worktrees, then create or reuse a suitable **managed execution worktree**, branch `codex/sec-edgar-stage-4`, based on the exact merged baseline above. If the branch/worktree already exists, inspect its state; do not reset or overwrite it. Keep implementation, tests and builds in that worktree. Worktree setup must obey the offline restriction.

Because the new Stage 4 documents are untracked, a worktree created from main will not contain them. Copy only the hash-verified Stage 4 spec, Plan 4 and enumerated Stage 4 planning/approval/handoff evidence to their corresponding relative paths in the execution worktree. Copy the approved roadmap snapshot to the ignored roadmap path as an execution input, preserving primary bytes. Preserve the approved copies unchanged while tracking implementation progress separately. Use explicit reviewed path lists for any staging; do not copy the primary working tree or its historical Stage 3 originals wholesale. The new handoff inventory is `/Users/lowell/Projects/sec-edgar/specs/evidence/sec-filing-index-ingestion/stage-4/handoff-validation.json`; verify its enumerated files before copying.

## Authority and non-negotiable limits

Authoritative Stage 3 completion is:

- `/Users/lowell/Projects/sec-edgar/specs/completed/sec-filing-index-ingestion-stage-3-spec.md`
- `/Users/lowell/Projects/sec-edgar/specs/plans/completed/3-sec-filing-index-ingestion-stage-3-spec.md`

The untracked `/Users/lowell/Projects/sec-edgar/specs/sec-filing-index-ingestion-stage-3-spec.md` and `/Users/lowell/Projects/sec-edgar/specs/plans/3-sec-filing-index-ingestion-stage-3-spec.md` are historical inputs. Do not use them to reopen completed work. The old `codex/sec-edgar-stage-3` branches are deleted and its managed worktree is archived recoverably; do not restore it for this stage.

Stage 3 acceptance includes exact documented **SEC-0141 / SEC-0142 / SEC-0143** quarantines, with **21 / 24 / 6** conflicts respectively. These remain whole-source refusals, without accepted observations or published generations. Do not weaken strict parsing, silently drop conflicting rows, reinterpret quarantines as successful coverage, or rewrite retained evidence. Planning verified the 9,678-record completion inventory and quarantine raw/state evidence; historical Stage 3's 452-test result was not rerun during planning.

**Use offline evidence and fixtures only.** All live-access authorizations remain closed. All **22 Stage 7 integrated checks remain reserved/not_run**. No SEC/Azure access, authentication, provisioning, deployment, image build, network fetch, trigger enablement or live smoke is authorized. Use offline/frozen dependency operations; missing cached dependencies are an execution blocker, not permission to fetch or change pins. Preserve every version, resource limit, safety gate and retention rule in Plan 4's Global Constraints. No new dependencies. Do not infer deployed runtime/memory/connectivity guarantees from native fixtures.

## Execution and acceptance

Use `subagent-driven-development`, the approved Plan 4 default, with fresh implementers per task and the required spec/quality review gates. Follow applicable repository instructions and the execution skill's actual available review roles/models; do not claim unavailable Opus/Sonnet/Haiku aliases were used. Apply `test-driven-development`, meaningful red/green cycles, and `verification-before-completion`. Execute the seven tasks in order:

1. Coverage and workflow result contracts.
2. Exact source projections and durable unresolved-member retention.
3. Checked existing discover/collect/transform/publish child command execution.
4. Backfill/daily orchestration, legacy pending-work recovery and durable report repair.
5. Manual CLI validation, logs and runbooks.
6. Compact offline fixtures proving outage, overlap, quarantine, gates, crash recovery and repeat behavior.
7. Fresh native and installed-wheel proofs, resolved reviews and completion checkpoint.

The reviewed design retains original acquisition settings, parent worksets and snapshot bindings while processing under the current parser/schema versions. Discovery progress and published coverage are separate. A newer successful listing must not hide older unresolved work. Publication remains per quarter, with the active pointer as authority; gated candidates are `awaiting_approval`. Daily `no_new_sources` requires valid required listings and no new or unresolved work. Do not manufacture completion from dates, counters or child stdout.

Use the complete interfaces, code examples, fixture matrix and commands in Plan 4. Important resolved review cases include typed Mapping codecs, exact saved-context replay before deadline validation, reuse of already downloaded bytes, legacy sources predating WorkflowMember, no projection-of-projection growth over repeated runs, fatal discovery halting child dispatch, cross-quarter daily publication, and an installed proof importing the reviewed distribution rather than checkout source.

Track milestone progress in an execution ledger. Surface deviations before crossing an approved acceptance boundary. Do not edit approved snapshots or retick Stage 4 early. Retain failed/red proofs and corrected results in new create-only evidence locations. Run the scoped gates and final full offline check `./scripts/check-sec-edgar-ingest.sh`, guarded help/version/build/compile/whitespace checks, real crash/reopen tests and fresh installed-wheel workflow/read proof required by the plan. Record actual results and the expanded test count; never reuse historical counts as fresh verification.

After required tests and installed proof pass and task/whole-branch findings are resolved, apply `writing-plans` completion protocol, including resolve-before-defer and backlog reporting. Retire only the executed Stage 4 plan/spec together, repair relative links, and tick Stage 4 through `derive-roadmap` reconciliation only after acceptance. Keep Stages 5–8 unticked and all 22 Stage 7 checks reserved. Retain the ignored roadmap payload for integration. Finish through `finishing-a-development-branch` and obtain any required integration decision; this approval is not authorization to merge, deploy, activate schedules or implement later stages.

The planning chats **“Plan Stage 4 ingestion workflows”** (`01a1185c-16a1-70d0-95e6-aa6e0847346e`) and **“Reconcile main and plan Stage 4”** (`01a11858-acdc-7073-9dd8-b413b53529d4`) stopped at handoff. Their histories are not required. Do not resume them or send coordination messages merely to begin execution. Start with receipt/hash verification and the fresh preservation preflight, then proceed with the approved offline implementation.
