// The roles.json grants whose scope is one Blob container (spec §5).
param storageName string
param containerName string

@description('The roles.json scope key handled here, container:<name>.')
param scopeKey string

param assignments array
param roleIds object
param principals object

resource account 'Microsoft.Storage/storageAccounts@2025-06-01' existing = {
  name: storageName
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2025-06-01' existing = {
  parent: account
  name: 'default'
}

resource container 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' existing = {
  parent: blobService
  name: containerName
}

resource grants 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for grant in filter(assignments, item => item.scope == scopeKey): {
  name: guid(container.id, principals[grant.principal], grant.role)
  scope: container
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds[grant.role])
    principalId: principals[grant.principal]
    principalType: grant.principal == 'operator' ? 'User' : 'ServicePrincipal'
  }
}]
