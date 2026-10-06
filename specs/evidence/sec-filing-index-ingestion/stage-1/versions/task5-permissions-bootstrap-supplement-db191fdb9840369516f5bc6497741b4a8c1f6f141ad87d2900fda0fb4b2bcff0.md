# Supplement: namespace registration and selected deployment actions

Public official permission catalog evidence collected 2026-10-06; versioned separately from permissions-source-notes.md. Historical notes and source manifest remain unchanged. supplement-sources-manifest.json hashes the seven new source JSON files and this supplement.

## Registration correction

Do not use Microsoft.Resources/subscriptions/providers/register/action: it is not listed in the current Management and governance catalog. The resource-provider registration endpoint and its Azure RBAC permission name differ. Exact namespace permission strings from the catalogs are:

| Namespace | Registration Action | Retained catalog |
|---|---|---|
| Microsoft.App | microsoft.app/register/action | supplement-compute.json |
| Microsoft.DataFactory | Microsoft.DataFactory/register/action | supplement-analytics.json |
| Microsoft.Storage | Microsoft.Storage/register/action | supplement-storage.json |
| Microsoft.ManagedIdentity | Microsoft.ManagedIdentity/register/action | supplement-identity.json |
| Microsoft.ContainerRegistry | Microsoft.ContainerRegistry/register/action | supplement-containers.json |
| Microsoft.OperationalInsights | Microsoft.OperationalInsights/register/action | supplement-monitor.json |
| Microsoft.Insights | Microsoft.Insights/Register/Action | supplement-monitor.json |

Each registration assignment belongs at subscription scope, separate from later resource-group deployment authority. Catalog capitalization is retained. The Insights catalog also contains Microsoft.Insights/Tenants/Register/Action, but that is tenant initialization and is not selected for subscription provider registration.

## Proposed SecEdgarBootstrap role

This is a proposed custom role specification, not an existing effective role:

- Actions: Microsoft.Resources/subscriptions/resourceGroups/read; Microsoft.Resources/subscriptions/resourceGroups/write; Microsoft.Resources/subscriptions/providers/read; exactly the seven registration Actions above.
- DataActions, NotActions and NotDataActions: empty.
- AssignableScopes and assignment: chosen subscription.
- Scope consequence: resourceGroups/write at subscription allows creating/updating groups throughout that subscription, and provider registration applies subscription-wide. It is not limited by naming intentions; avoid claiming it restricts group creation to an application name.
- Omit resourceGroups/delete and provider unregister actions unless separately authorized for cleanup.

User Access Administrator (UAA) has documented Actions */read, Microsoft.Authorization/* and Microsoft.Support/* with no DataActions (historical privileged-role evidence). This covers custom roleDefinitions/write and roleAssignments/write/delete at its assigned scope. Subscription UAA can create the subscription-scoped async observer assignment, and can define custom roles when it has write authority on every selected assignable scope. It cannot itself register providers or create resources; those are SecEdgarBootstrap/Contributor permissions. This is broad authorization-management trust, not constrained delegation. Exact actor and grants need owner acceptance and effective Stage 7 proof.

## Exact creation/update Actions for selected resource types

The following are management Actions, with no direct Blob/Table entity data access implied:

| Resource/operation | Action | Retained catalog |
|---|---|---|
| Managed environment | microsoft.app/managedenvironments/write | supplement-compute.json |
| Job | microsoft.app/jobs/write | supplement-compute.json |
| Join managed environment | microsoft.app/managedenvironments/join/action | supplement-compute.json |
| ADF factory | Microsoft.DataFactory/factories/write | supplement-analytics.json |
| ADF pipeline | Microsoft.DataFactory/factories/pipelines/write | supplement-analytics.json |
| ADF trigger | Microsoft.DataFactory/factories/triggers/write | supplement-analytics.json |
| Trigger enable/disable | Microsoft.DataFactory/factories/triggers/start/action; Microsoft.DataFactory/factories/triggers/stop/action | supplement-analytics.json |
| Storage account | Microsoft.Storage/storageAccounts/write | supplement-storage.json |
| Blob service configuration | Microsoft.Storage/storageAccounts/blobServices/write | supplement-storage.json |
| Blob container | Microsoft.Storage/storageAccounts/blobServices/containers/write | supplement-storage.json |
| Table service configuration | Microsoft.Storage/storageAccounts/tableServices/write | supplement-storage.json |
| Table | Microsoft.Storage/storageAccounts/tableServices/tables/write | supplement-storage.json |
| UAMI | Microsoft.ManagedIdentity/userAssignedIdentities/write | supplement-identity.json |
| UAMI attachment | Microsoft.ManagedIdentity/userAssignedIdentities/assign/action plus target resource write | supplement-identity.json |
| Registry | Microsoft.ContainerRegistry/registries/write | supplement-containers.json |
| Log Analytics workspace | Microsoft.OperationalInsights/workspaces/write | supplement-monitor.json |
| Log Analytics table/retention | Microsoft.OperationalInsights/workspaces/tables/write | supplement-monitor.json |
| Diagnostic setting | Microsoft.Insights/DiagnosticSettings/Write | supplement-monitor.json |
| Action group | Microsoft.Insights/ActionGroups/Write | supplement-monitor.json |
| Scheduled query alert | Microsoft.Insights/ScheduledQueryRules/Write | supplement-monitor.json |
| Metric alert, if selected | Microsoft.Insights/MetricAlerts/Write | supplement-monitor.json |
| ARM deployment create/update | Microsoft.Resources/deployments/write | supplement-governance.json |
| Role-definition bootstrap | Microsoft.Authorization/roleDefinitions/write | supplement-governance.json |

The resource group Contributor baseline grants these Actions through its * wildcard minus NotActions, but not role assignment/role definition write. ARM deployment itself also needs read/validate/whatIf/operations/status as used by the actual deployment workflow. Exact individual read operations, delete/cleanup operations, linked-scope authorization, regional async polling, diagnostic destination authorization, policy and service-specific deployment checks are not established by these creation strings. This supplement must not be presented as an executable complete custom deployment role.

## Retrieval constraints

The public permission pages contain generic access-authorization banners but returned the permission tables without authentication. Searches initially produced some localized official pages; the selected retained entries use English catalog pages. No Azure access was used. Effective permission checks remain reserved for Stage 7.
