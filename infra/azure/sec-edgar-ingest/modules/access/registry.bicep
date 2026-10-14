// The roles.json grants whose scope is the registry (spec §5).
param registryName string
param assignments array
param roleIds object
param principals object

resource registry 'Microsoft.ContainerRegistry/registries@2025-11-01' existing = {
  name: registryName
}

resource grants 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for grant in filter(assignments, item => item.scope == 'registry'): {
  name: guid(registry.id, principals[grant.principal], grant.role)
  scope: registry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds[grant.role])
    principalId: principals[grant.principal]
    principalType: grant.principal == 'operator' ? 'User' : 'ServicePrincipal'
  }
}]
