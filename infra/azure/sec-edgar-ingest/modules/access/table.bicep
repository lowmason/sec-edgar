// The roles.json grants whose scope is one table (spec §5).
param storageName string
param tableName string

@description('The roles.json scope key handled here, table:<name>.')
param scopeKey string

param assignments array
param roleIds object
param principals object

resource account 'Microsoft.Storage/storageAccounts@2025-06-01' existing = {
  name: storageName
}

resource tableService 'Microsoft.Storage/storageAccounts/tableServices@2025-06-01' existing = {
  parent: account
  name: 'default'
}

resource table 'Microsoft.Storage/storageAccounts/tableServices/tables@2025-06-01' existing = {
  parent: tableService
  name: tableName
}

resource grants 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for grant in filter(assignments, item => item.scope == scopeKey): {
  name: guid(table.id, principals[grant.principal], grant.role)
  scope: table
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds[grant.role])
    principalId: principals[grant.principal]
    principalType: grant.principal == 'operator' ? 'User' : 'ServicePrincipal'
  }
}]
