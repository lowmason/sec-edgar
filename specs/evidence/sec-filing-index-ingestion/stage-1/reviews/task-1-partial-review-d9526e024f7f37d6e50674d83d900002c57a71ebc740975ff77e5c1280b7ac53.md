# Task 1 partial preparation review

Reviewed the frozen evidence-only diff against Task 1's brief, its Global Constraints, the plan's evidence schema, and the accepted Stage 1 evidence categories. This is a partial task review, not a final whole-branch review. No SEC or Azure request, reported-check rerun, checkout/index/HEAD/branch mutation, or artifact edit was performed. Only this review report was written.

## Spec-compliance verdict

**Acceptable independent preparation; Task 1 remains incomplete.** No Critical or Important prepared-artifact defect was found. The records preserve the distinction between written-contract approval, observed account candidates, owner decisions, and deployed authority. The observed subscription is not promoted to an accepted binding; authentication is not treated as effective permission evidence; the empty VM inventory is limited to this actor's returned result. Root-report timestamps are explicitly receipt timestamps rather than invented access timestamps. The five required deliverables exist, and their visible CSV headers match the specified 12-column evidence and 10-column discrepancy schemas.

The original four deletions and original plan/roadmap bytes are recorded separately from new evidence. The before-state retains approval and actual HEAD, approved/current spec hashes, original-file hashes or absence states, and protected-document hashes. The retained command report contains the seven required baseline commands with outputs, stderr and exit codes. This review assesses that retained evidence, rather than independently rerunning the checks.

The 2026-10-05 America/New_York endpoint is pinned to 2026 Q4 with 68 intended units and 48 development units; the table explicitly describes requested units, without source-discovery or historical-coverage claims. Resource choices remain candidates. The SEC boundary has one root issuer, a shared proposal and zero-access accounting, no activated window, and an open owner-traffic gate. No proposed rate or budget is presented as owner acceptance. No readiness, production implementation, provisioning, roadmap advancement, or Stage 7 integration success is claimed.

## Task-quality verdict

**Acceptable with two Minor improvements.** The preparation is reviewable and its main authority boundaries are clear. The following do not permit Task 1 completion and do not justify SEC access.

### Minor: validator artifact resolution depends on the caller's current directory

`specs/evidence/sec-filing-index-ingestion/stage-1/validate-task-1.py:17` opens `Path(r["url_or_artifact"])` directly. Most index paths are repository-relative, although the script otherwise derives the repository from its own location. The documented repository-root invocation is valid, but running the same saved script from another directory fails while the protected files are unchanged.

Remedy: resolve relative artifact paths against `repo`, preserving absolute paths, or explicitly enforce and document a repository-root working-directory prerequisite. This is a reproducibility improvement, not evidence that the reported root invocation failed.

### Minor: broad local-facility absence is insufficiently attributed in the decision narrative

`specs/evidence/sec-filing-index-ingestion/stage-1/decisions.md:88` introduces the observations as retained in `prerequisites-initial.json`, then lines 89–91 extend the absence statement to podman, colima, limactl, nerdctl, container and named QEMU facilities. That artifact retains only docker/docker buildx/uv/az/az bicep commands. `index.csv:7` and the implementer report correctly label the broader search as root-reported, but the narrative omits that distinction.

Remedy: split the retained docker/az command results from the broader root-reported search, explicitly state that the latter's commands/outputs were not retained, or retain a separately indexed root report. Keep the execution-facility gate open until a concrete usable host is demonstrated.

## Completion gates, separate from defects

- D-01–D-08 still require concrete deployment choices/owner acceptance: cloud/tenant/subscription, resource-group name, environment/naming, operator and authority, registry and permissions, pull identity, rollback digest retention/availability, and tooling prerequisites. The deliberate “Keep binding undecided” answer maintains D-01 as open/blocking.
- D-09 still requires owner-wide SEC traffic allocation and confirmed bounded window, followed by exact activation start/end, rate, limits and shared ledger. The proposed 45-minute/240-attempt/512-MiB/12-specimen boundary is inactive.
- D-12 still requires a concrete probe host, authorized access path and demonstrated isolated Linux amd64 capability. An empty VM inventory does not resolve it.
- Newly created principal IDs and integrated deployed behavior remain Stage 7 evidence; that reservation does not discharge concrete Stage 1 inputs.

The owner's latest post-freeze “Can you not set this up for me?” direction and root's temporary Azure resource/cost/cleanup proposal are outside this frozen diff. A prepared proposal is neither resource creation nor an accepted deployment binding. Before relying on a changed host direction, append a dated decision that names the approved proposal/scope and supersedes the earlier existing-VM-only direction; do not silently rewrite the historical answer or infer acceptance from preparation alone. The frozen artifacts remain historically reviewable and must be updated with any later accepted decision before claiming current Task 1 completion.

Task 1 must remain incomplete and SEC access must remain inactive until the applicable gates are explicitly discharged.

## Scoped re-review of the two Minor corrections

Reviewed only `task-1-fix-review.diff` and the appended implementer verification report. No checks were rerun and no network access occurred.

- **ADDRESSED — caller-independent artifact resolution.** `validate-task-1.py:17` now creates the artifact path, resolves relative values against the derived `repo`, and retains absolute paths. The implementer reports exit 0 for both repository-root and `/private/tmp` invocations. The code directly addresses the prior working-directory dependency.
- **ADDRESSED — broader facility-search attribution.** `decisions.md:88` now limits the copied JSON's evidence to its exact uv/docker/az command observations, then separately labels the broader `shutil.which` search as root-reported and not retained in that JSON. The execution-facility gate remains open.

**No new Important issues caused by these fixes were found.** Both previous Minor findings are closed. This scoped result does not discharge full Task 1 gates, approve the pending temporary-resource scope proposal, activate SEC access, or establish readiness.

## Updated source-access checkpoint assessment

Reviewed the new frozen `task-1-checkpoint-review.diff`, current implementer report, and retained acceptance/proposal records. This updates the earlier inactive/unanswered-window assessment. No network access or reported-check rerun was performed. This is not a full-branch review or a review of actual Azure setup/probe outcomes.

**Spec-compliance verdict: PASS for the Task 1 source-access checkpoint, conditional on root recording activation before the first SEC request.** Baseline protections and decision statuses remain reviewable; D-09 now records an accepted exclusive, bounded investigation allocation. `access-window.md:40` identifies the exact owner reply, “Confirm window; all other SEC traffic paused,” and names the accepted limits. `sec-window-owner-acceptance.json:7` retains the sole-root issuer, zero other-owner allocation, sequential/no-burst issuing, maximum 3 requests/second with at least 1/3-second starts, 45-minute duration, 240 attempts including retries, 536,870,912 received bytes, and 12 complete initial specimens. D-09 is resolved with acceptance date and acceptance-artifact revision hash. Authorization is distinctly **not activation**; zero accounting and unset activation times are accurate preparation states.

The remaining action genuinely required before source access is for root to record the actual UTC start and deadline/end boundary, confirm the accepted zero-other-traffic allocation remains in force, record the selected rate/limits, and initialize the shared attempt/byte/specimen ledger. Root alone may then perform ordered Task 2 access within those limits. Retries use the same budget; longer server delays must be honored; 403/access-denial content halts access; the first exhausted budget, new format family or additional-sampling need pauses work pending a separately recorded bounded continuation. This review does not itself activate the window.

The unresolved production choices D-01–D-08 and actual native-facility/probe evidence D-12 are **readiness/later-investigation gates, not additional preconditions for this source-access checkpoint**. Task 1 requires their explicit status and owner questions rather than invented decisions. The plan expressly permits registry/tooling proposals during Tasks 4–5 and requires all concrete choices before readiness. The owner's production binding remains deliberately undecided. Neither a production registry, deployment operator binding nor successful Linux amd64 probe is needed to discover SEC source directories with the accepted issuer/window. Treating those as pre-access gates would impose an extra dependency and obstruct the specified source Tasks 2–3 before the runtime investigation in Task 4. Full Task 1 decision acquisition and Stage 1 readiness remain incomplete; passing this checkpoint does not resolve those entries.

**Task-quality verdict: PASS for prepared controls; no new Critical, Important or Minor defect found in the reviewed checkpoint changes.** The accepted temporary-probe exception is tied to immutable proposal revision 1, SHA-256 `5946673f1cdd8fc3a346ae61b4a2d711cccb3fa660031060a412f1b8e5ffeb84`, and exact owner reply, with separately retained `probe-setup/acceptance.json` dated 2026-10-05. `decisions.md:156` records its temporary bindings, bounded runs/cost/lifetime, cleanup scope, method adaptation and separation from production acceptance. It explicitly supersedes the historical existing-VM direction for this probe without altering the original answer. D-13 is resolved for the accepted method exception; D-12 remains open for actual setup/native compatibility. Acceptance establishes authority for the narrow proposal, not successful resource creation, permissions, costs, expiry compliance, cleanup or Task 4 completion. Compatibility probes remain Task 4 in order.

Exact review limitations: baseline preservation, hashes and checker success are assessed from the frozen artifacts and reported fresh outputs, without independently rerunning validation. No SEC availability, format support, actual traffic, effective deployed authority or runtime compatibility has been established by this checkpoint review. Only root may activate and maintain the recorded SEC boundary. All concrete production choices and required source/runtime/provider evidence must still be completed and explicitly accepted before a readiness conclusion.
