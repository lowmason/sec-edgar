// The roles.json grants whose scope is the job (spec §5).
param jobName string
param assignments array
param roleIds object
param principals object

resource job 'Microsoft.App/jobs@2026-07-01' existing = {
  name: jobName
}

resource grants 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for grant in filter(assignments, item => item.scope == 'job'): {
  name: guid(job.id, principals[grant.principal], grant.role)
  scope: job
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds[grant.role])
    principalId: principals[grant.principal]
    principalType: grant.principal == 'operator' ? 'User' : 'ServicePrincipal'
  }
}]
