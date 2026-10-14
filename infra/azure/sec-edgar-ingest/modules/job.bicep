// The Manual job and its Consumption environment (spec §2, §4, §9). It has no schedule and no volumes; the
// config reaches the container only as the ingest-config secret.
param location string
param environmentName string
param jobName string
param workspaceId string

@description('The job container; ADF starts it with the same container plus arguments.')
param container object

@description('Canonical config, stored as the ingest-config secret.')
param configJson string

param workerIdentityId string
param pullIdentityId string
param registryServer string

resource managedEnvironment 'Microsoft.App/managedEnvironments@2026-07-01' = {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'azure-monitor'
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

resource environmentLogs 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'to-law-sec-edgar-dev'
  scope: managedEnvironment
  properties: {
    workspaceId: workspaceId
    logAnalyticsDestinationType: 'Dedicated'
    logs: [
      {
        category: 'ContainerAppConsoleLogs'
        enabled: true
      }
      {
        category: 'ContainerAppSystemLogs'
        enabled: true
      }
    ]
  }
}

resource job 'Microsoft.App/jobs@2026-07-01' = {
  name: jobName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${workerIdentityId}': {}
      '${pullIdentityId}': {}
    }
  }
  properties: {
    environmentId: managedEnvironment.id
    workloadProfileName: 'Consumption'
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 3600
      replicaRetryLimit: 0
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
      secrets: [
        {
          name: 'ingest-config'
          value: configJson
        }
      ]
      registries: [
        {
          server: registryServer
          identity: pullIdentityId
        }
      ]
    }
    template: {
      containers: [
        container
      ]
    }
  }
}

output jobId string = job.id
