// Stage 6 deployment definition (spec §9). Subscription scope: the resource group and the custom roles;
// every other resource lives in a resource-group module. Nothing here starts a trigger or a job.
targetScope = 'subscription'

@description('Region for every regional resource, in F1 region order.')
@allowed([
  'eastus'
  'eastus2'
  'centralus'
])
param location string = 'eastus'

@description('Canonical Azure config rendered by python -m sec_edgar_ingest.deployment (spec §4).')
param configJson string

@description('config_sha256 of configJson, from the same render.')
@minLength(64)
@maxLength(64)
param configSha256 string

@description('Entra object ID of the operator, Lowell Mason (spec §5).')
param operatorPrincipalId string

@description('First daily trigger time: Eastern local yyyy-MM-ddTHH:mm:ss, without Z (spec §7.4).')
@minLength(19)
@maxLength(19)
param dailyStartTime string

@description('First reconciliation trigger time: Eastern local yyyy-MM-ddTHH:mm:ss, without Z (spec §7.4).')
@minLength(19)
@maxLength(19)
param reconcileStartTime string

// F1 D-02 and D-03.
var names = {
  group: 'rg-sec-edgar-dev-eastus'
  environment: 'cae-sec-edgar-dev-eastus'
  job: 'job-sec-edgar-dev'
  factory: 'adf-sec-edgar-dev'
  workspace: 'law-sec-edgar-dev'
  actionGroup: 'ag-sec-edgar-dev'
  storage: 'secedgardevb8617'
  registry: 'secedgardevb8617'
  worker: 'id-sec-edgar-dev-worker'
  pull: 'id-sec-edgar-dev-pull'
}
var containers = [
  'raw'
  'worksets'
  'quarantine'
  'locks'
  'results'
  'generations'
  'manifests'
  'approvals'
]
var tables = [
  'SourceState'
  'Attempts'
  'ActivePointers'
  'Approvals'
]
var roles = loadJsonContent('roles.json')
var roleIds = union(toObject(roles.definitions, role => role.roleName, role => guid(subscription().id, role.roleName)), roles.builtins)
var config = json(configJson)
var registryServer = '${names.registry}.azurecr.io'

resource group 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: names.group
  location: location
}

resource roleDefinitions 'Microsoft.Authorization/roleDefinitions@2022-04-01' = [for role in roles.definitions: {
  name: guid(subscription().id, role.roleName)
  properties: {
    roleName: role.roleName
    description: role.description
    type: 'CustomRole'
    permissions: [
      {
        actions: role.actions
        notActions: []
        dataActions: role.dataActions
        notDataActions: []
      }
    ]
    assignableScopes: [
      subscription().id
    ]
  }
}]

module identities 'modules/identities.bicep' = {
  name: 'identities'
  scope: group
  params: {
    location: location
    workerName: names.worker
    pullName: names.pull
  }
}

module registry 'modules/registry.bicep' = {
  name: 'registry'
  scope: group
  params: {
    location: location
    name: names.registry
  }
}

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  scope: group
  params: {
    location: location
    workspaceName: names.workspace
    actionGroupName: names.actionGroup
    email: 'mason.lowell@mac.com'
  }
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  scope: group
  params: {
    location: location
    name: names.storage
    containers: containers
    tables: tables
  }
}

// The job container. ADF's start override repeats it with arguments added (spec §4, §7.1).
var container = {
  name: 'sec-edgar-ingest'
  image: '${registryServer}/sec-edgar-ingest@${config.worker.image_digest}'
  resources: {
    cpu: 2
    memory: '4Gi'
  }
  env: [
    {
      name: 'SEC_EDGAR_INGEST_WORKER_CLIENT_ID'
      value: identities.outputs.workerClientId
    }
    {
      name: 'SEC_EDGAR_INGEST_CONFIG'
      secretRef: 'ingest-config'
    }
  ]
}

// Container Apps checks the registry identity when it creates the job, so the pull grant comes first.
module job 'modules/job.bicep' = {
  name: 'job'
  scope: group
  params: {
    location: location
    environmentName: names.environment
    jobName: names.job
    workspaceId: monitoring.outputs.workspaceId
    container: container
    configJson: configJson
    workerIdentityId: identities.outputs.workerId
    pullIdentityId: identities.outputs.pullId
    registryServer: registryServer
  }
  dependsOn: [
    registryAccess
  ]
}

module factory 'modules/factory.bicep' = {
  name: 'factory'
  scope: group
  params: {
    location: location
    name: names.factory
    workspaceId: monitoring.outputs.workspaceId
    container: container
    imageDigest: config.worker.image_digest
    configSha256: configSha256
    jobPath: job.outputs.jobId
    asyncPrefix: 'https://management.azure.com/subscriptions/${subscription().subscriptionId}/providers/Microsoft.App/locations/${location}/'
    resultsUrl: '${config.storage.blob_endpoint}/results/runs/sec/'
    maxLaunches: 1 + config.orchestration.transient_replays
    dailyStartTime: dailyStartTime
    reconcileStartTime: reconcileStartTime
  }
}

// Who each roles.json principal is.
var principals = {
  adf: factory.outputs.principalId
  worker: identities.outputs.workerPrincipalId
  pull: identities.outputs.pullPrincipalId
  operator: operatorPrincipalId
}

module containerAccess 'modules/access/container.bicep' = [for name in containers: {
  name: 'access-container-${name}'
  scope: group
  params: {
    storageName: names.storage
    containerName: name
    scopeKey: 'container:${name}'
    assignments: roles.assignments
    roleIds: roleIds
    principals: principals
  }
  dependsOn: [
    storage
    roleDefinitions
  ]
}]

module tableAccess 'modules/access/table.bicep' = [for name in tables: {
  name: 'access-table-${name}'
  scope: group
  params: {
    storageName: names.storage
    tableName: name
    scopeKey: 'table:${name}'
    assignments: roles.assignments
    roleIds: roleIds
    principals: principals
  }
  dependsOn: [
    storage
    roleDefinitions
  ]
}]

module jobAccess 'modules/access/job.bicep' = {
  name: 'access-job'
  scope: group
  params: {
    jobName: names.job
    assignments: roles.assignments
    roleIds: roleIds
    principals: principals
  }
  dependsOn: [
    job
    roleDefinitions
  ]
}

// Only the pull identity: the full map names the factory, which needs the job, which needs this grant.
module registryAccess 'modules/access/registry.bicep' = {
  name: 'access-registry'
  scope: group
  params: {
    registryName: names.registry
    assignments: roles.assignments
    roleIds: roleIds
    principals: {
      pull: identities.outputs.pullPrincipalId
    }
  }
  dependsOn: [
    registry
    roleDefinitions
  ]
}

module subscriptionAccess 'modules/access/subscription.bicep' = {
  name: 'access-subscription'
  params: {
    assignments: roles.assignments
    roleIds: roleIds
    principals: principals
  }
  dependsOn: [
    roleDefinitions
  ]
}

module alerts 'modules/alerts.bicep' = {
  name: 'alerts'
  scope: group
  params: {
    location: location
    workspaceId: monitoring.outputs.workspaceId
    actionGroupId: monitoring.outputs.actionGroupId
  }
}
