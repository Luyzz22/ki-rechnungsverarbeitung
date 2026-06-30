param location string

param azureOpenAiAccountName string
param documentIntelligenceAccountName string

@minLength(1)
param azureOpenAiCustomSubdomain string

@minLength(1)
param documentIntelligenceCustomSubdomain string

@allowed([
  'Enabled'
  'Disabled'
])
param publicNetworkAccess string

param networkAcls object

@minLength(1)
param azureOpenAiDeploymentName string

@minLength(1)
param azureOpenAiModelName string

@minLength(1)
param azureOpenAiModelVersion string

@minLength(1)
param azureOpenAiModelFormat string

@minValue(1)
param azureOpenAiModelCapacity int

resource azureOpenAiAccount 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: azureOpenAiAccountName
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: azureOpenAiCustomSubdomain
    disableLocalAuth: true
    publicNetworkAccess: publicNetworkAccess
    networkAcls: networkAcls
  }
}

resource azureOpenAiDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = {
  parent: azureOpenAiAccount
  name: azureOpenAiDeploymentName
  sku: {
    name: 'Standard'
    capacity: azureOpenAiModelCapacity
  }
  properties: {
    model: {
      format: azureOpenAiModelFormat
      name: azureOpenAiModelName
      version: azureOpenAiModelVersion
    }
  }
}

resource documentIntelligenceAccount 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: documentIntelligenceAccountName
  location: location
  kind: 'FormRecognizer'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: documentIntelligenceCustomSubdomain
    disableLocalAuth: true
    publicNetworkAccess: publicNetworkAccess
    networkAcls: networkAcls
  }
}

output azureOpenAiAccountResourceId string = azureOpenAiAccount.id
output documentIntelligenceAccountResourceId string = documentIntelligenceAccount.id
