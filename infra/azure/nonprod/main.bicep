targetScope = 'resourceGroup'

@allowed([
  'nonprod'
])
param environment string

param location string
param resourcePrefix string

param azureOpenAiAccountName string
param documentIntelligenceAccountName string

@minLength(1)
param azureOpenAiCustomSubdomain string

@minLength(1)
param documentIntelligenceCustomSubdomain string

param workloadManagedIdentityPrincipalId string

@allowed([
  'TRANSITIONAL_STATIC_EGRESS'
  'PRIVATE_VNET_TARGET'
])
param networkMode string

param allowedHetznerEgressCidrs array

param privateEndpointSubnetResourceId string
param privateDnsZoneResourceIds array
param privateEndpointConnectionResourceIds array

param azureOpenAiInferenceRoleDefinitionId string
param documentIntelligenceInferenceRoleDefinitionId string

@minLength(1)
param azureOpenAiDeploymentName string

@minLength(1)
param azureOpenAiModelName string

@minLength(1)
param azureOpenAiModelVersion string

@minLength(1)
param azureOpenAiModelFormat string
param azureOpenAiDeploymentSkuName string

@minValue(1)
param azureOpenAiModelCapacity int

module networkTransition 'modules/network-transition.bicep' = {
  name: '${resourcePrefix}-${environment}-network-contract'
  params: {
    networkMode: networkMode
    allowedHetznerEgressCidrs: allowedHetznerEgressCidrs
    privateEndpointSubnetResourceId: privateEndpointSubnetResourceId
    privateDnsZoneResourceIds: privateDnsZoneResourceIds
    privateEndpointConnectionResourceIds: privateEndpointConnectionResourceIds
  }
}

module aiServices 'modules/ai-services.bicep' = {
  name: '${resourcePrefix}-${environment}-ai-services'
  params: {
    location: location
    azureOpenAiAccountName: azureOpenAiAccountName
    documentIntelligenceAccountName: documentIntelligenceAccountName
    azureOpenAiCustomSubdomain: azureOpenAiCustomSubdomain
    documentIntelligenceCustomSubdomain: documentIntelligenceCustomSubdomain
    publicNetworkAccess: networkMode == 'TRANSITIONAL_STATIC_EGRESS' ? 'Enabled' : 'Disabled'
    networkAcls: networkTransition.outputs.networkAcls
    azureOpenAiDeploymentName: azureOpenAiDeploymentName
    azureOpenAiModelName: azureOpenAiModelName
    azureOpenAiModelVersion: azureOpenAiModelVersion
    azureOpenAiModelFormat: azureOpenAiModelFormat
    azureOpenAiDeploymentSkuName: azureOpenAiDeploymentSkuName
    azureOpenAiModelCapacity: azureOpenAiModelCapacity
  }
}

module rbac 'modules/rbac.bicep' = {
  name: '${resourcePrefix}-${environment}-inference-rbac'
  params: {
    azureOpenAiAccountName: azureOpenAiAccountName
    documentIntelligenceAccountName: documentIntelligenceAccountName
    workloadManagedIdentityPrincipalId: workloadManagedIdentityPrincipalId
    azureOpenAiInferenceRoleDefinitionId: azureOpenAiInferenceRoleDefinitionId
    documentIntelligenceInferenceRoleDefinitionId: documentIntelligenceInferenceRoleDefinitionId
  }
  dependsOn: [
    aiServices
  ]
}
