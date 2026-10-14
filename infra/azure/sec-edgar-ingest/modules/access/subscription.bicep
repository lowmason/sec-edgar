// The roles.json grants whose scope is the subscription: the async observer, whose operation routes sit
// outside the job's ancestry (spec §5).
targetScope = 'subscription'

param assignments array
param roleIds object
param principals object

resource grants 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for grant in filter(assignments, item => item.scope == 'subscription'): {
  name: guid(subscription().id, principals[grant.principal], grant.role)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds[grant.role])
    principalId: principals[grant.principal]
    principalType: grant.principal == 'operator' ? 'User' : 'ServicePrincipal'
  }
}]
