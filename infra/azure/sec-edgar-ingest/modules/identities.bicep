// The worker identity (storage access) and the pull identity (registry access only) (spec §5).
param location string
param workerName string
param pullName string

resource worker 'Microsoft.ManagedIdentity/userAssignedIdentities@2024-11-30' = {
  name: workerName
  location: location
}

resource pull 'Microsoft.ManagedIdentity/userAssignedIdentities@2024-11-30' = {
  name: pullName
  location: location
}

output workerId string = worker.id
output workerClientId string = worker.properties.clientId
output workerPrincipalId string = worker.properties.principalId
output pullId string = pull.id
output pullPrincipalId string = pull.properties.principalId
