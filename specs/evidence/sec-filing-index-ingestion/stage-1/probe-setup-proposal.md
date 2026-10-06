# Temporary ACR Tasks facility for Stage 1 probes

Revision: 1, 2026-10-05. Status: **Pending owner acceptance; proposal only.**

The owner asked whether Codex could set up the missing container facility. This proposes one temporary Azure Container Registry (ACR) for isolated Stage 1 Linux amd64 compatibility probes. It adds narrowly scoped temporary provisioning, provider registration and cleanup authority to Stage 1, whose accepted scope currently excludes Azure provisioning. It does not select a production deployment binding or introduce production infrastructure definitions. The owner's instruction to keep that binding undecided remains in force.

## Proposed temporary binding and resources

| Item | Proposed value |
|---|---|
| Cloud | AzureCloud |
| Tenant | `0bb72127-3aa2-408f-a5e4-ba9abcfc6db6` |
| Subscription | `3c92a216-8ed6-4897-b741-11ed287b8617` — LGM Consulting |
| Signed-in operator | `mason.lowell@mac.com` |
| Dedicated temporary resource group | `rg-sec-edgar-stage1-probe-20261005` |
| Region | `eastus` |
| Dedicated temporary registry | `secedgarstage1probe20261005b8617` |
| Registry SKU and permission mode | Basic; RBAC registry permissions |
| Registry exposure | Admin user disabled; anonymous pull disabled |
| Lifecycle | Delete after retained evidence verification; maximum 24 hours from creation |

No role assignments, production images, worker image publication, native job resources, ADF resources, schedules, automatic builds, or persistent task triggers are proposed. The only compute use is manually submitted sequential quick tasks. Existing subscription resources and production bindings are outside this scope.

Root's read-only preflight reported name availability, no existing registries, and `Microsoft.ContainerRegistry` in `NotRegistered` state, all with exit code 0. These reported results are retained in [root-reported-preflight.json](probe-setup/root-reported-preflight.json); exact call times and original output are not available in this preparation. Name availability can change. Registration, creation, task execution and deletion authority remain unverified. Setup must first register `Microsoft.ContainerRegistry` in the proposed subscription and observe successful registration before registry creation. Registration changes subscription-level provider state and can remain after resource cleanup; do not unregister the provider as part of cleanup because it may subsequently be used elsewhere.

## Execution method and limits

The [ACR Tasks overview](https://learn.microsoft.com/en-us/azure/container-registry/container-registry-tasks-overview) and [Azure CLI build reference](https://learn.microsoft.com/en-us/cli/azure/acr?view=azure-cli-latest#az-acr-build) are the root-reported official sources for cloud builds without local Docker. Their capabilities are documentation evidence; successful native probe outputs still have to be obtained. This proposal does not declare the dependency/container probes passed.

Use at most **four sequential quick-task runs**, each with `--platform linux/amd64`, `--cpu 2`, `--timeout 1800`, `--no-cache`, and `--no-push`. These are run-setting requirements, not a resource-definition artifact or an instruction to execute now. Count unsuccessful and canceled submitted runs toward the four-run maximum. Stop rather than expanding the count, timeout, CPU allocation or budget without further authorization.

Create each task context under `/private/tmp` from approved evidence/probe scripts only. Review the exact context before upload. Exclude the repository, user configuration, credential/token material and unrelated files. Probe dependency installation/imports, selected archive codecs, and a small Parquet write/read round trip only. No ingestion parser or production package implementation belongs in this context.

At ordered Task 4 start, pin the official Python 3.14 Linux amd64 child-image digest and record its metadata. Preserve the plan's two fresh installations using uncached builds. Record exact commands, script/input hashes, platform/ABI, dependency resolution, output, run IDs and exit codes. `--no-push` prevents publication of the probe image; no worker image is built or published.

Initial facility setup may occur before source investigation, once this bounded exception is accepted. Actual compatibility probes still execute at **Task 4 in plan order**. Replacing local Docker probe commands with ACR quick tasks is an explicit investigation-method deviation requiring owner acceptance. It does not alter the approved workload, production Bicep choice, or later-stage scope.

## Cost estimate and operational budget

The official [Azure Retail Prices endpoint](https://prices.azure.com/api/retail/prices) was queried by root for Container Registry in eastus. The original response body and receipt were copied unchanged to [retail-prices.json](probe-setup/retail-prices.json) and [receipt.json](probe-setup/receipt.json). The receipt records HTTP 200 at `2026-10-05T23:17:15.450204+00:00`; the body has USD currency and no next page. [copy-verification.json](probe-setup/copy-verification.json) records matching source/destination hashes.

The Basic registry row is USD 0.1666 per day. The paid Basic Task vCPU Duration row is USD 0.0001 per vCPU-second. Zero-price tier rows are also present; this estimate assumes no free allowance or subscription credit.

| Component | Bound and arithmetic | Base estimate, USD |
|---|---|---:|
| Quick-task compute | 4 runs × 1,800 seconds × 2 vCPU = 14,400 vCPU-seconds; × 0.0001 | 1.4400 |
| Temporary registry | At most one day × 0.1666/day | 0.1666 |
| Total | 1.4400 + 0.1666 | **1.6066** |

This is a retail base estimate, excluding taxes, network egress, storage overage and subscription-specific billing terms. Propose a **USD 5 operational investigation budget**. This is not a hard Azure-enforced spend cap. Enforce the four-run, CPU, timeout and expiry bounds; stop on unexpected pricing/charge terms or evidence that the budget could be exceeded. Preserve actual costs when available without treating delayed billing as proof of zero cost.

## Exact cleanup boundary

After downloading available run logs/outputs, recording run IDs/exit outcomes and hashes, and verifying retained artifacts, delete only the proposed dedicated registry and dedicated group in subscription `3c92a216-8ed6-4897-b741-11ed287b8617`:

- Registry resource ID: `/subscriptions/3c92a216-8ed6-4897-b741-11ed287b8617/resourceGroups/rg-sec-edgar-stage1-probe-20261005/providers/Microsoft.ContainerRegistry/registries/secedgarstage1probe20261005b8617`.
- Group resource ID: `/subscriptions/3c92a216-8ed6-4897-b741-11ed287b8617/resourceGroups/rg-sec-edgar-stage1-probe-20261005`.

Confirm identities and inventory the dedicated group before deletion; unexpected contents require stopping the group deletion and reporting the discrepancy. Never delete other groups or registries. Begin cleanup before the 24-hour expiry, including when probes fail or cannot proceed. If evidence cannot be fully downloaded before expiry, preserve what is available, record the loss/failure, and clean up within the accepted lifetime. Record deletion outcomes and verify absence; retain cleanup failures and residual-resource details for the owner instead of claiming removal. Provider registration is not rolled back.

## Single bundled acceptance required

Accept this narrow Stage 1 exception as one bundle: temporary probe-only scope; the temporary tenant/subscription binding above while production binding stays undecided; the exact group, registry and eastus location; subscription provider registration; no role assignments or automatic triggers; four sequential runs with the stated CPU/time settings, USD 5 operational budget and 24-hour maximum lifetime; deletion limited to the two exact dedicated resource IDs with retained evidence and failure reporting; and the ACR quick-task adaptation of the Task 4 probe method. Acceptance authorizes setup and its bounded cleanup, not later-stage implementation or production deployment.
