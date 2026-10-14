// One HNS StorageV2 account; Entra-only access over public HTTPS (spec §9).
param location string
param name string
param containers array
param tables array

resource account 'Microsoft.Storage/storageAccounts@2025-06-01' = {
  name: name
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_ZRS'
  }
  properties: {
    accessTier: 'Hot'
    isHnsEnabled: true
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Enabled'
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2025-06-01' = {
  parent: account
  name: 'default'
}

resource blobContainers 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = [for container in containers: {
  parent: blobService
  name: container
  properties: {
    publicAccess: 'None'
  }
}]

resource tableService 'Microsoft.Storage/storageAccounts/tableServices@2025-06-01' = {
  parent: account
  name: 'default'
}

resource accountTables 'Microsoft.Storage/storageAccounts/tableServices/tables@2025-06-01' = [for table in tables: {
  parent: tableService
  name: table
}]
