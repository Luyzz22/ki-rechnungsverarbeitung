using './main.bicep'

param environment = 'nonprod'
param location = '<azure-region-placeholder>'
param resourcePrefix = '<flowcheck-nonprod-prefix-placeholder>'

param azureOpenAiAccountName = '<azure-openai-account-name-placeholder>'
param documentIntelligenceAccountName = '<document-intelligence-account-name-placeholder>'

param azureOpenAiCustomSubdomain = '<azure-openai-custom-subdomain-placeholder>'
param documentIntelligenceCustomSubdomain = '<document-intelligence-custom-subdomain-placeholder>'

param workloadManagedIdentityPrincipalId = '<azure-arc-system-assigned-managed-identity-principal-id-placeholder>'

param networkMode = 'PRIVATE_VNET_TARGET'
param allowedHetznerEgressCidrs = []

param privateEndpointSubnetResourceId = '<private-endpoint-subnet-resource-id-placeholder>'
param privateDnsZoneResourceIds = [
  '<private-dns-zone-resource-id-placeholder>'
]
param privateEndpointConnectionResourceIds = [
  '<private-endpoint-connection-resource-id-placeholder>'
]

param azureOpenAiInferenceRoleDefinitionId = '<verify-azure-openai-inference-role-definition-id-placeholder>'
param documentIntelligenceInferenceRoleDefinitionId = '<verify-document-intelligence-inference-role-definition-id-placeholder>'

param azureOpenAiDeploymentName = '<pinned-azure-openai-deployment-name-placeholder>'
param azureOpenAiModelName = '<pinned-azure-openai-model-name-placeholder>'
param azureOpenAiModelVersion = '<pinned-azure-openai-model-version-placeholder>'
param azureOpenAiModelFormat = '<pinned-azure-openai-model-format-placeholder>'
param azureOpenAiDeploymentSkuName = '<pinned-azure-openai-deployment-sku-placeholder>'
param azureOpenAiModelCapacity = 1
