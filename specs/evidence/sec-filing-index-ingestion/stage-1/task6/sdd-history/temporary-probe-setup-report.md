# Temporary probe facility setup report

Status: **DONE for accepted temporary facility setup. Task 4 compatibility probes and cleanup remain separate obligations.**

Owner Lowell Mason accepted revision 1 on 2026-10-05 with the exact reply `Accept temporary probe proposal`, as reported in the root dispatch. The separate `acceptance.json` record preserves proposal SHA-256 `5946673f1cdd8fc3a346ae61b4a2d711cccb3fa660031060a412f1b8e5ffeb84`; proposal bytes were not edited. The accepted temporary binding does not select a production binding.

AzureCloud, tenant `0bb72127-3aa2-408f-a5e4-ba9abcfc6db6`, subscription `3c92a216-8ed6-4897-b741-11ed287b8617`, and operator `mason.lowell@mac.com` were confirmed by read-only CLI output. Fresh auxiliary preflight found the group absent, no registries, and the registry name available. Installed Azure CLI help confirmed the exact accepted creation flags.

`Microsoft.ContainerRegistry` registration returned exit code 0 at 2026-10-05T23:24:57.233996+00:00. Bounded polling reached `Registered` at 2026-10-05T23:26:13.248864+00:00 (poll 8, exit code 0). Provider registration is a retained subscription change and is not rolled back during cleanup.

## Execution handoff and uncertainty resolution

The auxiliary creation escalation returned `aborted by user after 1249.8 seconds`. The later read-only reconciliation escalation returned `aborted by user after 110.8 seconds`. Neither returned command execution results or new receipt files. Missing receipts were treated as uncertain resource state. Root took sole Azure execution ownership, and the auxiliary agent stopped Azure calls. Root freshly reconciled the exact group as absent, registries as `[]`, and name availability as true before creation. These observations resolved the retry uncertainty without duplicate mutation. Root then created and freshly verified the accepted resources. This was a setup orchestration deviation, not a scope change. No authority-denial error was returned by the Azure service; the stalled/interrupted tool calls cannot establish whether an approval rejection occurred.

## Created resources and lifecycle

- Group: `/subscriptions/3c92a216-8ed6-4897-b741-11ed287b8617/resourceGroups/rg-sec-edgar-stage1-probe-20261005`. Group creation command began at `2026-10-05T23:50:30.922520+00:00` and returned `Succeeded` at 2026-10-05T23:50:33.314314+00:00. The group response does not expose an exact server-side creation timestamp.
- Registry: `/subscriptions/3c92a216-8ed6-4897-b741-11ed287b8617/resourceGroups/rg-sec-edgar-stage1-probe-20261005/providers/Microsoft.ContainerRegistry/registries/secedgarstage1probe20261005b8617`. Azure reports creation at `2026-10-05T23:50:52.211421+00:00` by `mason.lowell@mac.com`.
- Cleanup deadline: **2026-10-06T23:50:30.922520+00:00**. This is 24 hours from the first resource creation command start, conservatively earlier than the successful group response. Both resources carry matching `purpose=stage1-compatibility-probe`, `owner=LowellMason`, and `expiresAtUTC` tags.
- HTTPS registry login hostname: `secedgarstage1probe20261005b8617.azurecr.io`. Provisioning exposes the usual ACR HTTPS endpoint; no independent transport probe was performed.

Fresh `az acr show` returned exit code 0 at 2026-10-05T23:51:24.178084+00:00 and confirmed the exact ID, `eastus`, `Basic`, admin user disabled, anonymous pull disabled, `LegacyRegistryPermissions` (the returned RBAC registry mode), `Succeeded`, and public network access enabled. A fresh persistent task listing returned `[]` with exit code 0; therefore no persisted tasks or associated task triggers/schedules were present at verification. Fresh group inventory returned only the exact expected registry with exit code 0. No quick tasks were submitted during setup.

## Evidence validation and limits

Evidence is retained under `specs/evidence/sec-filing-index-ingestion/stage-1/probe-setup/`. Auxiliary `setup-*` receipts preserve readable commands, argument vectors, UTC start/end times, stdout, stderr, and exit codes. Root `root-reconcile-*`, `root-create-*`, and `root-verify-*` receipts preserve the full argument vectors and command outcomes; `setup-root-execution-validation.json` supplies readable command renderings and SHA-256 hashes for those receipts. Local validation checks JSON readability, exit code 0, exact subscription flags on every management command, immutable proposal hash, accepted resource fields and tags, exact inventory, empty persistent-task list, and the 24-hour deadline arithmetic. The retained initial 16 auxiliary command receipts also passed these checks where applicable. Help calls are nonmanagement commands. The initial sandbox denial reading CLI help was retried with escalation and succeeded without Azure mutation.

No SEC traffic, role assignments, production resource definitions, package changes, or Git mutations were performed by the auxiliary agent. Stage 7 remains reserved. This setup does not establish native-task execution authority, worker capacity, dependency compatibility, successful tests, or production acceptance. Actual billing remains unverified; the accepted USD 5 operational budget and four sequential Task 4 runs with their CPU/time settings remain binding.

Cleanup is **not yet performed**. Root handles the cleanup safeguard and must begin cleanup before the stated deadline, retaining evidence and verifying removal. Cleanup authority covers only the two exact resource IDs after identity and inventory checks; unexpected group contents require stopping group deletion and reporting. Provider registration remains in place. No cleanup reminder or independent schedule was created by the auxiliary agent.
