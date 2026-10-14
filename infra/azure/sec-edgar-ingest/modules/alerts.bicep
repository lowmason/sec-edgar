// Log search alerts over law-sec-edgar-dev (spec §8). Per-run alerts are stateless and overlap their
// windows, so an event ingested up to 15 minutes late still alerts. The staleness alerts are stateful and
// deploy disabled until Stage 8 enables them with their triggers.
param location string
param workspaceId string
param actionGroupId string

var alerts = [
  {
    name: 'alert-sec-edgar-failed-job'
    description: 'A run-worker pipeline failed with an outcome other than awaiting_approval or execution_unknown.'
    severity: 1
    enabled: true
    stateful: false
    frequency: 'PT15M'
    window: 'PT30M'
    query: loadTextContent('../alerts/failed-job.kql')
  }
  {
    name: 'alert-sec-edgar-ambiguous-start'
    description: 'A run-worker pipeline ended execution_unknown; no relaunch happened.'
    severity: 1
    enabled: true
    stateful: false
    frequency: 'PT15M'
    window: 'PT30M'
    query: loadTextContent('../alerts/ambiguous-start.kql')
  }
  {
    name: 'alert-sec-edgar-lease-failure'
    description: 'A worker lost its lease (ownership_lost).'
    severity: 1
    enabled: true
    stateful: false
    frequency: 'PT15M'
    window: 'PT30M'
    query: loadTextContent('../alerts/lease-failure.kql')
  }
  {
    name: 'alert-sec-edgar-access-block'
    description: 'The SEC blocked access (access_blocked).'
    severity: 1
    enabled: true
    stateful: false
    frequency: 'PT15M'
    window: 'PT30M'
    query: loadTextContent('../alerts/access-block.kql')
  }
  {
    name: 'alert-sec-edgar-retry-exhausted'
    description: 'A workflow exhausted the retry budget of a member.'
    severity: 2
    enabled: true
    stateful: false
    frequency: 'PT15M'
    window: 'PT30M'
    query: loadTextContent('../alerts/retry-exhausted.kql')
  }
  {
    name: 'alert-sec-edgar-quarantine'
    description: 'A source or workflow was quarantined.'
    severity: 2
    enabled: true
    stateful: false
    frequency: 'PT15M'
    window: 'PT30M'
    query: loadTextContent('../alerts/quarantine.kql')
  }
  {
    name: 'alert-sec-edgar-publication-conflict'
    description: 'A publication conflict is unresolved.'
    severity: 1
    enabled: true
    stateful: false
    frequency: 'PT15M'
    window: 'PT30M'
    query: loadTextContent('../alerts/publication-conflict.kql')
  }
  {
    name: 'alert-sec-edgar-pending-approval'
    description: 'A withdrawal candidate is pending approval.'
    severity: 2
    enabled: true
    stateful: false
    frequency: 'PT15M'
    window: 'PT30M'
    query: loadTextContent('../alerts/pending-approval.kql')
  }
  {
    name: 'alert-sec-edgar-reconcile-staleness'
    description: 'No successful reconciliation in eight days. Enabled with the reconcile trigger (Stage 8).'
    severity: 2
    enabled: false
    stateful: true
    frequency: 'PT1H'
    window: 'P2D'
    query: loadTextContent('../alerts/reconcile-staleness.kql')
  }
  {
    name: 'alert-sec-edgar-daily-staleness'
    description: 'No daily run with complete discovery in 30 hours. Enabled with the daily trigger (Stage 8).'
    severity: 2
    enabled: false
    stateful: true
    frequency: 'PT1H'
    window: 'P2D'
    query: loadTextContent('../alerts/daily-staleness.kql')
  }
]

resource rules 'Microsoft.Insights/scheduledQueryRules@2023-12-01' = [for alert in alerts: {
  name: alert.name
  location: location
  kind: 'LogAlert'
  properties: {
    displayName: alert.name
    description: alert.description
    severity: alert.severity
    enabled: alert.enabled
    scopes: [
      workspaceId
    ]
    evaluationFrequency: alert.frequency
    windowSize: alert.window
    criteria: {
      allOf: [
        {
          query: alert.query
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 0
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    autoMitigate: alert.stateful
    skipQueryValidation: true
    actions: {
      actionGroups: [
        actionGroupId
      ]
    }
  }
}]
