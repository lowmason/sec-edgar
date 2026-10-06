# Provider documentation preparation

Status: **Raw independent preparation only**, collected 2026-10-05. This is not an approved API/version selection, a Task 5 result, an ordered Tasks 2–5 completion, a Stage 1 readiness finding, or evidence of effective deployment. The Stage 1 spec §§5.3–5.4 governs evidence distinctions. Task 1 owner traffic-window/binding decisions remain outside this preparation.

## Retained evidence

Directory: `specs/evidence/sec-filing-index-ingestion/stage-1/provider/preparation/20261005T230634Z/`.

- `retrieval-metadata.json`: individual direct URLs, retrieval methods, UTC access-start times, outcomes and completeness limits.
- Fourteen `*.web-extract.txt` files: saved returned web-tool text, including one failed retrieval and supplementary schedule passages.
- `claim-extracts.json`: twelve bounded provider-documentation claims with relevant short line extracts, direct URLs, access times, and limitations.
- `sha256-manifest.json`: exact saved-file byte counts and SHA-256 values. These hashes identify saved tool extracts and metadata; they are not hashes of original HTTP response bodies.

Access times range from 2026-10-05 23:06:50 UTC to 23:07:55 UTC. Each timestamp was read immediately before its individual retrieval. The tool did not expose precise HTTP receipt time/status/headers. Its rendered extracts can omit page text; none is represented as a complete HTTP body. The initial schedule extract lacked the Eastern row, so a second direct access at line 480 retained it. The intervening supported-timezones link resolved to the same schedule page and its tool output is also retained.

## Coverage and limits

The retained Jobs create/update, start, exact execution GET and corrected executions-list references identify the 2026-07-01 family. ADF Web and schedule passages, Blob Lease, Table Update Entity, ADLS known issues, Jobs guidance and Container Apps storage mounts were reaccessed from official Microsoft documentation. Every claim is bounded by its extract and limitation; no deployed request/response, resource state, role assignment, registry pull, or storage operation was exercised.

Provider documentation supports available capabilities. Application safeguards and readiness require later decisions and checks. A Blob lease protects writes/deletes on that blob, not SEC requests; conditional Table writes do not establish a Blob/Table transaction. Web activity asynchronous HTTP handling does not establish matching execution or durable worker-result success. Generic Container Apps temporary-storage limits do not prove the selected Jobs configuration's actual capacity or applicability.

## Failed checks and discrepancies retained

1. The guessed `containerapps/jobs/list-executions` documentation path was inaccessible through the web tool. Its failure is retained, without interpreting it as an HTTP status or unavailable API. Official search identified `containerapps/jobs-executions/list`; the corrected direct reference was accessible and retained.
2. Microsoft Learn displayed generic authorization banners while still returning documentation passages. This preparation used only accessible text and attempted no authentication.
3. The execution GET sample combines `Running`, an end time, and `BackoffLimitExceeded`. That sample does not establish consistent terminal semantics. The seven enum descriptions largely repeat their names, leaving uncertain-state handling and actual 200/202 correlation behavior for later finding/deployment verification.
4. Schedule documentation states non-UTC serialization without `Z`, while later examples contain explicit offsets. Retain this difference for an explicit serialization choice; this preparation does not approve a trigger definition.
5. Jobs guidance supports zero retries but recommends at least one for long-running replicas interrupted by maintenance. The accepted zero-retry policy remains authoritative and needs its later documented rationale and Stage 7 maintenance recovery check.
6. Storage mounts documentation is generic Container Apps guidance and uses app/revision examples. CPU-linked ephemeral capacity and temporary lifetime are documentation facts; selected Jobs capacity and real worker use are not measured here.

## Reserved evidence and work boundaries

Effective identity permissions, public reachability, regional eligibility/capacity, registry pulls, exact starts/status/correlation/result behavior, lease/CAS failure behavior, maintenance recovery, actual DST execution and worker memory/runtime remain **Reserved Stage 7 checks**. No owner decision, assumption resolution, readiness acceptance or API selection is inferred from this preparation.

Only the assigned preparation directory and this report were written. No SEC request, package change, provisioning, authentication, secret lookup, implementation, shared evidence index/register edit, staging or commit occurred.

## Verification

The preparation manifest is regenerated after final artifact edits, then every artifact byte count and SHA-256 is independently recalculated and compared. The retained verification result records counts and failures. This establishes saved-artifact integrity only.
