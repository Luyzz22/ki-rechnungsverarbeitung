param azureOpenAiAccountName string
param documentIntelligenceAccountName string
param workloadManagedIdentityPrincipalId string
param azureOpenAiInferenceRoleDefinitionId string
param documentIntelligenceInferenceRoleDefinitionId string

resource azureOpenAiAccount 'Microsoft.CognitiveServices/accounts@2023-05-01' existing = {
  name: azureOpenAiAccountName
}

resource documentIntelligenceAccount 'Microsoft.CognitiveServices/accounts@2023-05-01' existing = {
  name: documentIntelligenceAccountName
}

resource azureOpenAiInferenceRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(azureOpenAiAccount.id, workloadManagedIdentityPrincipalId, azureOpenAiInferenceRoleDefinitionId)
  scope: azureOpenAiAccount
  properties: {
    principalId: workloadManagedIdentityPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', azureOpenAiInferenceRoleDefinitionId)
  }
}

resource documentIntelligenceInferenceRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(documentIntelligenceAccount.id, workloadManagedIdentityPrincipalId, documentIntelligenceInferenceRoleDefinitionId)
  scope: documentIntelligenceAccount
  properties: {
    principalId: workloadManagedIdentityPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', documentIntelligenceInferenceRoleDefinitionId)
  }
}
