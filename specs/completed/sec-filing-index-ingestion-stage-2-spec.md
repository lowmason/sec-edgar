# SEC filing-index ingestion — Stage 2: Durable discovery and collection

**Status: COMPLETE (2026-10-06)** — executed via subagent-driven-development; nothing deferred
**Owner:** Lowell Mason.
**Implementing plan:** [Plan 2](../plans/completed/2-sec-filing-index-ingestion-stage-2-spec.md).
**Parent authority:** [Design spec](../sec-filing-index-ingestion-spec.md), [ADR](../sec-filing-index-ingestion-adr.md), [roadmap](../sec-filing-index-ingestion-roadmap.md), and [accepted Stage 1 finding](../sec-filing-index-ingestion-stage-1-findings.md#10-final-owner-acceptance--f1). This is a Stage 2 scope and rollout reference, not a replacement for the parent contracts.

> Historical approval record: this paragraph retains the original authorization and its then-pending execution status. The completed rollout stamp and retained verification below supply current Stage 2 evidence.

**Owner approval record:** Lowell Mason replied **“Approved”** to the request to approve Plan 2 for fresh-session execution via `subagent-driven-development`, recorded on 2026-10-06 America/New_York. The approved pre-recording plan SHA-256 is `a868939950abb0838625bf539fc46bc4fcc5c10f384b75764a3af4d9bc4f601c`; this implementing spec SHA-256 is `ed256aa56319269bb0ac7ad3ed54c91ffcfae13357be8daa7851c0e2555b0b0c`. This update records approval status only; technical scope, safeguards and completion gates are unchanged. Approval authorizes the prescribed fresh-session implementation, not live access, Stage 2 completion or Stage 3 work. No owner-authored time of day was supplied.

## 1. Resume/reconcile record

This is the historical planning-time reconciliation record. Its scaffold, unticked-stage and protected-roadmap statements describe that baseline; §§5–6 record the completed Stage 2 result and the one authorized local checkbox reconciliation.

On 2026-10-06, offline inspection found `HEAD`, local `origin/main` and PR #1's reported merge commit equal to `17731c33961f8ae3669e472765c1d1745ade44b4`. The local remote-tracking reference was inspected; no remote fetch or assertion about subsequent server-side activity was made. No implementation, tests, infrastructure or ingestion coverage has shipped beyond the scaffolds and Stage 1 evidence.

Stage 1's authoritative [completion stamp](sec-filing-index-ingestion-stage-1-spec.md#9-rollout-note) records COMPLETE (2026-10-06), implemented by [completed plan 1](../plans/completed/1-sec-filing-index-ingestion-stage-1-spec.md). Lowell Mason accepted READY finding F1, revision/acceptance date 2026-10-05 America/New_York, finding SHA-256 `939a724eccf22147015a59d5940ed57f02cc4e9fe9d942a9cd78ae73c34615ff`, and evidence-manifest SHA-256 `124e96041548daba8216aa495fc69021751555b0f0e4c890ac85e934f512a131`.

Fresh offline verification checked all 1,584 accepted manifest records: 1,583 direct matches and one expressly declared immutable alias for the finding before its acceptance appendix. All 192 targets in the three retained historical/SDD maps also matched. The [owner receipt](../evidence/sec-filing-index-ingestion/stage-1/final-candidate/owner-acceptance.json) records controller receipt `2026-10-06T03:48:04.966448+00:00`; this is not an owner-authored timestamp. Capture-time pending statements in the finding and retained reports do not override its final §10 acceptance or the later completion stamp.

The current untracked roadmap already ticks Stage 1. Preserve it byte-for-byte at planning-time SHA-256 `e4fdf810785daa3700a92c96b65e08f671f4afbdfe273eed6154dcd255a9cf02`. Preserve the four existing deletions of `packages/sec-edgar-index-ingest/README.md`, `pyproject.toml`, `src/sec_edgar_index_ingest/__init__.py`, and `src/sec_edgar_index_ingest/py.typed`. No files were restored, staged, stashed, reset or repaired during reconciliation.

Every unticked stage was checked for consistency with the shipped baseline, parent authority and accepted F1 limitations. This check neither designs nor plans the later stages:

| Unticked stage | Revalidation result |
|---|---|
| 2 — Durable discovery and collection | Still required: broken workspace/CLI and hello-only scaffolds; no durable acquisition behavior. Accepted D10 alignment handoff is unchanged. Route to `writing-plans`. |
| 3 — Replayable ETL and safe publication | Still requires Stage 2 pinned inputs/state. No parser, normalized observations, generation publication or replay proof shipped. F1's two bounded families and nullable-accession/date obligations remain constraints. |
| 4 — Backfill and daily catch-up workflows | Still requires later publication interfaces. Handoff 2026-10-01, overlap, pending older work and failed-directory boundary rules remain unchanged. |
| 5 — Reconciliation and withdrawal approval | No reconciliation or approval implementation shipped. Hash-bound approval, open-quarter absence and stale-replay safeguards remain unchanged. |
| 6 — Azure orchestration and deployment definitions | Accepted bindings, versions and Bicep selection remain design inputs. No worker image, provisioned stack or production triggers shipped. |
| 7 — Deployment checkpoint and recovery evidence | All 22 reserved integrated checks remain required, including actual identity/network/lease/CAS behavior and worker memory/runtime/temporary space. Local fixtures cannot pass these checks. |
| 8 — Baseline and scheduled-operation acceptance | No accepted production coverage or observed scheduled executions. Earlier stages' dependencies remain intact. |

The roadmap's historical derivation table remains historical. Its partition and unticked stage definitions need no change. Only Stage 2 is routed and planned here.

## 2. Required Stage 2 outcome

Deliver a runnable acquisition boundary under the parent's §§4.1–4.3, 4.5, 4.8–4.9 and applicable §§5–6:

1. Align the workspace to the single implementation at `packages/sec-edgar-ingest/`, distribution/CLI `sec-edgar-ingest`, import `sec_edgar_ingest`.
2. Validate acquisition configuration before external I/O.
3. Persist source identities, discovery outcomes, attempts, pending/failed gaps and immutable discovery worksets.
4. Retain original bytes, promote verified acquisition snapshots, bind each source-workset member once, and emit immutable snapshot worksets containing exact hashes.
5. Exercise meaningful concurrent-collector, lease-loss, in-flight takeover, crash/resumption, discovery-failure and build/CLI checks using offline/local fixtures.

Storage adapters implement the accepted Blob-created-object lifecycle, renewable Blob lease and conditional Table entity writes. A durable local fixture adapter supplies restart and multi-process proof against the same application contracts; it is explicitly selected and never substitutes silently for Azure. Stage 2 includes data-plane adapter code, not provisioning or proof of effective Azure behavior.

Acquisition validation checks transport completeness, selected container/encoding and index envelope. ZIP originals remain ZIPs; decoded members are derivatives. Row parsing, normalization, logical-key validation, nullable-accession handling, precedence and generation publication remain later-stage obligations. `downloaded` is not `transformed`, `published`, accepted row coverage or withdrawal authority.

## 3. Carried-forward authority and new owner choices

Accepted Stage 1 inputs remain in force: intended range 2010 Q1 through the run-pinned open quarter; development range 2015 Q1 through it; daily handoff 2026-10-01; SEC identity `Lowell Mason sec-edgar-ingest mason.lowell@mac.com`; all parent §4.8 defaults. Endpoint labels and source availability must be resolved anew per run; the 68/48 Stage 1 counts are receipt-time accounting, not coverage.

The supported acquisition representations established by F1 are quarterly ZIP with exactly one DEFLATE `master.idx` member and plain daily IDX. Their two observed text envelopes are strict ASCII, CRLF/`Filename`/ISO dates for quarterly and LF/`File Name`/compact dates for daily. These bounded observations establish no global format coverage. Optional codecs remain unselected. The 33 uninspected historical daily directories establish no recovery horizon, retention guarantee or ingestion coverage.

On 2026-10-06, Lowell Mason directly answered the Stage 2 batch: **“Keep excluded scaffolds; accept proposed guards.”** This records two choices, separate from plan approval:

- Keep `packages/sec-edgar-client/` and `packages/sec-edgar-download/` on disk, exclude them from workspace membership/dependencies/builds and put all implementation in ingest. Do not restore the deleted index-ingest files or stage their original deletions.
- Bound one complete HTTP exchange to **90 seconds**, retained response bytes to **64 MiB (67,108,864 bytes)** and an expanded IDX member to **512 MiB (536,870,912 bytes)**. Retain evidence on violation and leave that source unresolved. These guards establish no source coverage or worker fit. Raising them requires an explicit reviewed revision.

Use the accepted Stage 1 exact acquisition pins: Requests 2.34.2, Identity 1.26.0, Blob 12.31.0 and Tables 12.7.0. Blob data-plane version is explicitly 2026-04-06; Table is 2020-12-06. Keep Linux amd64/Python 3.14.8 compatibility evidence distinct from the local runtime and any future worker image. PyArrow 25.0.1 remains the accepted later ETL candidate and is not needed to collect bytes.

The retained evidence establishes provider primitives and selected versions; it does not retain every full SDK method signature. Plan 2 includes an execution-time inspection of the installed exact SDK public signatures and mocked request contracts before adapter implementation. This inspection needs no Azure access. Do not present proposed SDK call shapes as already-observed Azure behavior.

No additional owner selection is pending. New principal IDs, effective grants, globally available resource names, usable temporary storage, worker digest, tools/build facility and deployed behavior retain their existing later-stage gates. Do not invent values or reactivate closed Stage 1 authorizations.

## 4. Non-negotiable acquisition contracts

- All discovery, collection and retry traffic uses one coordinator and one owner-wide namespace; no per-workflow or per-subagent budgets. Daily gets the next bounded turn ahead of queued baseline/reconciliation work.
- A lease alone does not fence SEC traffic. Stop new starts on loss/uncertain renewal; bound/cancel each exchange and drain or wait out the old ownership window plus possible in-flight allowance before successor requests. Persist pacing, server delays and takeover guards across process restart.
- Preserve original bytes, original SHA-256, source URL, receipt UTC, byte count and available validators. Content-Length, transport encoding, ZIP member/CRC and envelope validation cannot be replaced by an HTTP 200 check.
- Promote raw content before recording a snapshot or binding. Bind each member by conditional create exactly once. A concurrent loser adopts the existing pin, never changes it. Newer source state cannot change earlier workset inputs.
- Immutable object/workset writes are create-only and checked on conflict. There is no Blob/Table transaction. Recovery repairs metadata from verified existing content without overwriting accepted inputs.
- Discovery includes the open/preceding quarters, handoff or contiguous last-success boundary through the run endpoint, and pending/failed identities from any quarter. Baseline overlap is retained.
- An inaccessible/malformed listing is `discovery_failed`; an authenticated valid listing with no relevant new entries is `no_new_sources`. A listed 404 stays pending. Successful later directories cannot advance the contiguous boundary past a failure. Absence authorizes no withdrawal.
- Attempts retain failures without erasing an earlier successful snapshot state. Incomplete collection emits progress/gaps; an immutable complete snapshot workset is emitted only when every member has a pin. A successful empty discovery is distinguishable from an incomplete empty workset.
- Configured image/parser/schema identities are explicit and copied into worksets/results. A fixture digest is labelled as synthetic fixture provenance and never reused as a deployed worker digest.

## 5. Completion gates and rollout reference

> Stage 2: COMPLETE (2026-10-06) — implemented by [plan 2](../plans/completed/2-sec-filing-index-ingestion-stage-2-spec.md).
> Acquisition verification/review evidence: [verification report](../evidence/sec-filing-index-ingestion/stage-2/verification.md), reviewed revision `e458010ead6709c16e992fa22a33997d3aa36ef0`, and [branch-shared completion receipt](../evidence/sec-filing-index-ingestion/stage-2/verification/completion-checkpoint/completion-receipt.json).
> Next: resume the [roadmap](../sec-filing-index-ingestion-roadmap.md).

All eight tasks and their Spec/Quality reviews are resolved. The latest prescribed offline check after the last implementation change passed all 302 tests in 106.619 seconds and completed build, CLI and whitespace checks with exit 0; its wrapper elapsed time was 106.99618458282202 seconds. The retained stderr SHA-256 is `dbd06ab5e7211f84abbb04ead35838721937e0ec54abe914cd20896403a6273a`. Documentation completion did not rerun acquisition, installation or the test suite; the completion receipt verifies the runtime, build inputs, tests and existing proof drivers equal the tested and reviewed revision.

Fresh [installed-wheel proof](../evidence/sec-filing-index-ingestion/stage-2/verification/sec-edgar-wheel-n0zc5qlc/sha256-manifest.json), [approved combined fixture sequence](../evidence/sec-filing-index-ingestion/stage-2/verification/sec-edgar-stage-2-46bhxh8j/sha256-manifest.json) and [process/recovery inspection](../evidence/sec-filing-index-ingestion/stage-2/verification/final-review-fix1-checkpoint/sdd/final-review-fix1-evidence/process-proof-inspection.json) retain exact bytes, versions, command exits, real local CAS losers, killed-child lifetime/takeover and crash-boundary recovery. Installed and combined manifests are respectively `126a1c3c666e1e41f63d37f68ec95ec145f55a28ec6a1ea97676fa9941caff47` and `beee194e1a67f1870c2b1d948c9ea29044f6ba0b6d9da0008443ccb13a8d4ab7`.

The [original full review](../evidence/sec-filing-index-ingestion/stage-2/verification/final-review-fix1-checkpoint/sdd/whole-branch-review-9098fe9.md) and fresh [scoped final review](../evidence/sec-filing-index-ingestion/stage-2/verification/completion-checkpoint/sdd/final-review-fix1-rereview.md) jointly resolve W-I1, W-I2 and W-M1 as ADDRESSED with no new findings. The controller's [composed verdict](../evidence/sec-filing-index-ingestion/stage-2/verification/completion-checkpoint/sdd/whole-branch-review-resolution.json) is Spec PASS and Quality PASS. Both required final reviewers used fresh GPT-6.1 Max (`gpt-6.1-sol`, effort `max`); unavailable `code-reviewer` role routing used the explicitly recorded default-role fallback. The Codex CLI second seat was SKIPPED under the same-family rule, with no second-review claim. No skipped/descoped step, unfixed finding, unanswered owner decision or deferred item remains. Backlog inspection found no `specs/deferred_items.md`; no empty backlog was created.

The separate daily endpoint answer is the owner's exact **“Yes”**, retained in the [owner receipt](../evidence/sec-filing-index-ingestion/stage-2/verification/task-8-i1-checkpoint/sdd/task-8-daily-endpoint-owner-answer.json), SHA-256 `f9720b21df9f56135386496f39bb2ec4d310614410b1b5f8645fdc07a7b963ac`. Its controller-recorded `2026-10-06T23:03:32+00:00` is receipt provenance, not an owner-authored time of day. The sequence uses separate quarterly 2015Q1 and daily-end-open synthetic configurations with unchanged canonical source/workset/pin contracts.

Only Stage 2's implementing plan and spec are retired. The parent design, ADR, accepted F1/evidence and roadmap remain active. The local/untracked roadmap receives exactly its Stage 2 checkbox after this authoritative stamp. Stop at this completion boundary; a later stage requires the owner to request “resume the roadmap.”

## 6. Completed interfaces and later-stage consistency

The delivered package provides validated `discover`/`collect` commands, immutable source and snapshot worksets, durable source/discovery/attempt/result state, original-byte raw promotion and one write-once member binding. `RunContext` includes immutable `effective_config` and `pinned_on`; discovery checkpoint APIs preserve frozen origin provenance, and collection staging obtains a verified actual request reservation through keyword-only `request_id`. Azure state uses old small inline Payload entities or content-first verified whole-record objects at internal `worksets/state/sha256=<hash>.json` paths and a single property/entity-bounded Table descriptor with actual ETag CAS. Approved source/snapshot/raw paths and identities are unchanged.

Step-level deviations in retired plan 2 record the actual shared interfaces, conservative Azure release guard and corrected explicit fixture invocation. Azure journal mutation and lease release are separate operations, so Azure successors retain the full `unsafe_until` wait; local `release_clean` can atomically finalize the journal and release. Fixture configs use relative configured storage roots plus an absolute fixture-only state directory and explicit synthetic clock/deadline override markers. Local evidence was produced on macOS 26.6.2 arm64/Python 3.14.0 with the accepted acquisition pins; it is distinct from Linux amd64/Python 3.14.8 compatibility evidence and a future worker image. These execution deviations defer no safeguard.

Revalidation below is read-only consistency against shipped Stage 2 interfaces and the existing roadmap definitions. Every later checkbox remains unticked; no later-stage design or implementation begins here.

| Unticked stage | Revalidation against completed Stage 2 |
|---|---|
| 3 — Replayable ETL and safe publication | Pinned original snapshots, source/snapshot worksets and state interfaces are available. Deterministic row parsing, canonical observations, generation builder/publisher/reader and golden/raw-only replay remain this stage's existing R3/R6/R9 exits. F1's bounded families, date and nullable-accession obligations remain. |
| 4 — Backfill and daily catch-up workflows | Acquisition can resume unresolved work and preserves failed-directory boundaries, handoff/overlap and pending older sources. Composition with Stage 3 publication and manually runnable historical/daily workflows with R1/R2 evidence remains required. |
| 5 — Reconciliation and withdrawal approval | Immutable pins and absence/failure outcomes preserve the parent safeguards. Reconciliation workflow, corrected deltas, hash-bound candidate/approval records, stale replay/reintroduction and shared R5/R7/R10 evidence remain required. |
| 6 — Azure orchestration and deployment definitions | Azure data-plane adapters and acquisition results are delivered. A pinned complete-worker image, versioned resources/identities, ADF start/poll/result handling, disabled triggers, telemetry/alerts and R4/R11 delivery checks remain required. |
| 7 — Deployment checkpoint and recovery evidence | Local/mock proof does not discharge any of the [22 reserved integrated checks](../evidence/sec-filing-index-ingestion/stage-1/stage-7-checks.md). Effective identity/network/owner-wide lease/CAS/HNS behavior, actual worker memory/runtime/temporary space, bounded live smoke and integrated replay/approval/rollback/runbooks remain reserved. |
| 8 — Baseline and scheduled-operation acceptance | No accepted production coverage or observed enabled schedules follows from fixtures. Accepted baseline/catch-up/reconciliation reports, controlled trigger enablement and matching durable scheduled reports/logs remain required. |
