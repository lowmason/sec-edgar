// The factory, its pipelines and its stopped triggers (spec §7). Pipeline activities come from the committed
// JSON; the run-worker parameters and their defaults are declared here.
param location string
param name string
param workspaceId string

@description('The job container; the start override repeats it with arguments (spec §7.1).')
param container object

param imageDigest string
param configSha256 string
param jobPath string
param asyncPrefix string
param resultsUrl string
param maxLaunches int

@description('Eastern local yyyy-MM-ddTHH:mm:ss, without Z.')
param dailyStartTime string

@description('Eastern local yyyy-MM-ddTHH:mm:ss, without Z.')
param reconcileStartTime string

var runWorker = loadJsonContent('../pipelines/pl-sec-edgar-run-worker.json')
var callers = [
  {
    name: 'pl-sec-edgar-backfill'
    definition: loadJsonContent('../pipelines/pl-sec-edgar-backfill.json')
  }
  {
    name: 'pl-sec-edgar-daily'
    definition: loadJsonContent('../pipelines/pl-sec-edgar-daily.json')
  }
  {
    name: 'pl-sec-edgar-reconcile'
    definition: loadJsonContent('../pipelines/pl-sec-edgar-reconcile.json')
  }
]

resource factory 'Microsoft.DataFactory/factories@2018-06-01' = {
  name: name
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {}
}

resource factoryLogs 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'to-law-sec-edgar-dev'
  scope: factory
  properties: {
    workspaceId: workspaceId
    logAnalyticsDestinationType: 'Dedicated'
    logs: [
      {
        category: 'ActivityRuns'
        enabled: true
      }
      {
        category: 'PipelineRuns'
        enabled: true
      }
      {
        category: 'TriggerRuns'
        enabled: true
      }
    ]
  }
}

resource runWorkerPipeline 'Microsoft.DataFactory/factories/pipelines@2018-06-01' = {
  parent: factory
  name: 'pl-sec-edgar-run-worker'
  properties: {
    activities: runWorker.activities
    variables: runWorker.variables
    parameters: {
      command: {
        type: 'String'
      }
      runId: {
        type: 'String'
      }
      containerName: {
        type: 'String'
        defaultValue: container.name
      }
      imageRef: {
        type: 'String'
        defaultValue: container.image
      }
      containerResources: {
        type: 'Object'
        defaultValue: container.resources
      }
      containerEnv: {
        type: 'Array'
        defaultValue: container.env
      }
      imageDigest: {
        type: 'String'
        defaultValue: imageDigest
      }
      configSha256: {
        type: 'String'
        defaultValue: configSha256
      }
      jobPath: {
        type: 'String'
        defaultValue: jobPath
      }
      asyncPrefix: {
        type: 'String'
        defaultValue: asyncPrefix
      }
      resultsUrl: {
        type: 'String'
        defaultValue: resultsUrl
      }
      maxLaunches: {
        type: 'Int'
        defaultValue: maxLaunches
      }
      pollSeconds: {
        type: 'Int'
        defaultValue: 30
      }
      observeSeconds: {
        type: 'Int'
        defaultValue: 4200
      }
      workerSeconds: {
        type: 'Int'
        defaultValue: 3300
      }
    }
  }
}

resource callerPipelines 'Microsoft.DataFactory/factories/pipelines@2018-06-01' = [for caller in callers: {
  parent: factory
  name: caller.name
  properties: caller.definition
  dependsOn: [
    runWorkerPipeline
  ]
}]

// Triggers deploy stopped: the schema has no settable runtimeState and nothing here starts them (spec §7.4).
resource dailyTrigger 'Microsoft.DataFactory/factories/triggers@2018-06-01' = {
  parent: factory
  name: 'tr-sec-edgar-daily'
  properties: {
    type: 'ScheduleTrigger'
    pipelines: [
      {
        pipelineReference: {
          referenceName: 'pl-sec-edgar-daily'
          type: 'PipelineReference'
        }
      }
    ]
    typeProperties: {
      recurrence: {
        frequency: 'Day'
        interval: 1
        startTime: dailyStartTime
        timeZone: 'Eastern Standard Time'
        schedule: {
          hours: [
            5
          ]
          minutes: [
            0
          ]
        }
      }
    }
  }
  dependsOn: [
    callerPipelines
  ]
}

resource reconcileTrigger 'Microsoft.DataFactory/factories/triggers@2018-06-01' = {
  parent: factory
  name: 'tr-sec-edgar-reconcile'
  properties: {
    type: 'ScheduleTrigger'
    pipelines: [
      {
        pipelineReference: {
          referenceName: 'pl-sec-edgar-reconcile'
          type: 'PipelineReference'
        }
      }
    ]
    typeProperties: {
      recurrence: {
        frequency: 'Week'
        interval: 1
        startTime: reconcileStartTime
        timeZone: 'Eastern Standard Time'
        schedule: {
          weekDays: [
            'Sunday'
          ]
          hours: [
            6
          ]
          minutes: [
            0
          ]
        }
      }
    }
  }
  dependsOn: [
    callerPipelines
  ]
}

output principalId string = factory.identity.principalId
