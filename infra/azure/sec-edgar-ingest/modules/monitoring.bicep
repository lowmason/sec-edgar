// The workspace every log lands in and the action group every alert notifies (spec §8).
param location string
param workspaceName string
param actionGroupName string
param email string

resource workspace 'Microsoft.OperationalInsights/workspaces@2025-07-01' = {
  name: workspaceName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 90
  }
}

resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: actionGroupName
  location: 'Global'
  properties: {
    groupShortName: 'secedgar'
    enabled: true
    emailReceivers: [
      {
        name: 'operator'
        emailAddress: email
        useCommonAlertSchema: true
      }
    ]
  }
}

output workspaceId string = workspace.id
output actionGroupId string = actionGroup.id
