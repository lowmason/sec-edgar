# SEC filing-index ingestion — Stage 2: Durable discovery and collection

**Status:** APPROVED (2026-10-06 America/New_York) — Lowell Mason approved Plan 2 for fresh-session execution via subagent-driven-development; implementation and completion gates remain unexecuted and Stage 2 remains unticked.
**Owner:** Lowell Mason.
**Implementing plan:** [Plan 2](plans/2-sec-filing-index-ingestion-stage-2-spec.md).
**Parent authority:** [Design spec](sec-filing-index-ingestion-spec.md), [ADR](sec-filing-index-ingestion-adr.md), [roadmap](sec-filing-index-ingestion-roadmap.md), and [accepted Stage 1 finding](sec-filing-index-ingestion-stage-1-findings.md#10-final-owner-acceptance--f1). This is a Stage 2 scope and rollout reference, not a replacement for the parent contracts.

**Owner approval record:** Lowell Mason replied **“Approved”** to the request to approve Plan 2 for fresh-session execution via `subagent-driven-development`, recorded on 2026-10-06 America/New_York. The approved pre-recording plan SHA-256 is `a868939950abb0838625bf539fc46bc4fcc5c10f384b75764a3af4d9bc4f601c`; this implementing spec SHA-256 is `ed256aa56319269bb0ac7ad3ed54c91ffcfae13357be8daa7851c0e2555b0b0c`. This update records approval status only; technical scope, safeguards and completion gates are unchanged. Approval authorizes the prescribed fresh-session implementation, not live access, Stage 2 completion or Stage 3 work. No owner-authored time of day was supplied.

## 1. Resume/reconcile record

On 2026-10-06, offline inspection found `HEAD`, local `origin/main` and PR #1's reported merge commit equal to `17731c33961f8ae3669e472765c1d1745ade44b4`. The local remote-tracking reference was inspected; no remote fetch or assertion about subsequent server-side activity was made. No implementation, tests, infrastructure or ingestion coverage has shipped beyond the scaffolds and Stage 1 evidence.

Stage 1's authoritative [completion stamp](completed/sec-filing-index-ingestion-stage-1-spec.md#9-rollout-note) records COMPLETE (2026-10-06), implemented by [completed plan 1](plans/completed/1-sec-filing-index-ingestion-stage-1-spec.md). Lowell Mason accepted READY finding F1, revision/acceptance date 2026-10-05 America/New_York, finding SHA-256 `939a724eccf22147015a59d5940ed57f02cc4e9fe9d942a9cd78ae73c34615ff`, and evidence-manifest SHA-256 `124e96041548daba8216aa495fc69021751555b0f0e4c890ac85e934f512a131`.

Fresh offline verification checked all 1,584 accepted manifest records: 1,583 direct matches and one expressly declared immutable alias for the finding before its acceptance appendix. All 192 targets in the three retained historical/SDD maps also matched. The [owner receipt](evidence/sec-filing-index-ingestion/stage-1/final-candidate/owner-acceptance.json) records controller receipt `2026-10-06T03:48:04.966448+00:00`; this is not an owner-authored timestamp. Capture-time pending statements in the finding and retained reports do not override its final §10 acceptance or the later completion stamp.

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

Stage 2 remains unticked until implementation, the plan's tests/build/CLI gates, every per-task Spec/Quality review, and final **GPT-6.1 Max** whole-branch review are complete and resolved. Local evidence must explicitly identify what it proves and which Stage 7 checks remain reserved. Safeguards cannot be deferred to manufacture stage completion.

> Roadmap: specs/sec-filing-index-ingestion-roadmap.md, Stage 2 — on plan completion, tick the
> stage and re-validate later stages against what shipped.

On actual completion, replace that rollout line with:

```text
Stage 2: COMPLETE (<actual completion date>) — implemented by plan 2
(specs/plans/completed/2-sec-filing-index-ingestion-stage-2-spec.md).
Acquisition verification/review evidence: <actual retained report and reviewed revision>.
Next: resume the roadmap.
```

The angle-bracket fields are completion-record fields filled from actual evidence, never planning-time claims. Retire only this Stage 2 implementing spec and plan when eligible. Keep the parent design spec, ADR, Stage 1 finding/evidence and roadmap active. The roadmap remains local/untracked unless the owner explicitly changes that instruction; stage ticking is a later local reconciliation edit, not authority to include it in a PR.

Stop after the Stage 2 completion boundary. Do not begin or plan Stage 3.
