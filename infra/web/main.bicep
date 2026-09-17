targetScope = 'resourceGroup'

param location string = 'northcentralus'
@minLength(3)
@maxLength(40)
param webAppName string
@minLength(3)
@maxLength(24)
param storageAccountName string
@minLength(36)
@maxLength(36)
param authClientId string
@minLength(36)
@maxLength(36)
param tenantId string
@minLength(1)
@maxLength(10)
param allowedUserIds array
@minLength(1)
param approverIds array
param foundryAccountName string
param foundryProjectName string
@minLength(1)
param agentEndpoint string
param modelDeploymentName string = 'caldova-model-router'
@allowed(['B1', 'P0v4'])
param planSku string = 'B1'

var tags = { workload: 'caldova-web', environment: 'demo' }
var origin = 'https://${webAppName}.azurewebsites.net'
var foundryUserRole = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d')
var blobContributorRole = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')

resource webIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${webAppName}-identity'
  location: location
  tags: tags
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    publicNetworkAccess: 'Enabled'
    networkAcls: { defaultAction: 'Allow', bypass: 'None' }
  }
}

resource blobs 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: {
    deleteRetentionPolicy: { enabled: true, days: 7 }
    containerDeleteRetentionPolicy: { enabled: true, days: 7 }
  }
}

resource sessions 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobs
  name: 'sessions'
  properties: { publicAccess: 'None' }
}

resource stateAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(sessions.id, webIdentity.id, blobContributorRole)
  scope: sessions
  properties: {
    principalId: webIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: blobContributorRole
  }
}

resource foundryAccount 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryAccountName
}
resource foundryProject 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' existing = {
  parent: foundryAccount
  name: foundryProjectName
}
resource inferenceAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundryProject.id, webIdentity.id, foundryUserRole)
  scope: foundryProject
  properties: {
    principalId: webIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: foundryUserRole
  }
}

resource plan 'Microsoft.Web/serverfarms@2024-04-01' = {
  name: '${webAppName}-plan'
  location: location
  tags: tags
  kind: 'linux'
  sku: { name: planSku, tier: planSku == 'P0v4' ? 'PremiumV4' : 'Basic', capacity: 1 }
  properties: { reserved: true }
}

resource web 'Microsoft.Web/sites@2024-04-01' = {
  name: webAppName
  location: location
  tags: tags
  kind: 'app,linux'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${webIdentity.id}': {} }
  }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    publicNetworkAccess: 'Enabled'
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.13'
      appCommandLine: 'python -m uvicorn control_tower_api:app --app-dir src --host 0.0.0.0 --port 8000 --workers 1'
      alwaysOn: true
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      scmMinTlsVersion: '1.2'
      http20Enabled: true
      remoteDebuggingEnabled: false
      appSettings: [
        { name: 'SCM_DO_BUILD_DURING_DEPLOYMENT', value: 'true' }
        { name: 'ENABLE_ORYX_BUILD', value: 'true' }
        { name: 'CALDOVA_HOSTED', value: '1' }
        { name: 'AZURE_TENANT_ID', value: tenantId }
        { name: 'AZURE_CLIENT_ID', value: webIdentity.properties.clientId }
        { name: 'CALDOVA_AGENT_ENDPOINT', value: agentEndpoint }
        { name: 'CALDOVA_STATE_CONTAINER_URL', value: '${storage.properties.primaryEndpoints.blob}${sessions.name}' }
        { name: 'CALDOVA_PUBLIC_ORIGIN', value: origin }
        { name: 'CALDOVA_ALLOWED_USERS', value: join(allowedUserIds, ',') }
        { name: 'CALDOVA_APPROVERS', value: join(approverIds, ',') }
        { name: 'AZURE_AI_MODEL_DEPLOYMENT_NAME', value: modelDeploymentName }
        { name: 'OVERRIDE_USE_MI_FIC_ASSERTION_CLIENTID', value: webIdentity.properties.clientId }
        { name: 'WEBSITE_AUTH_AAD_ALLOWED_TENANTS', value: tenantId }
      ]
    }
  }
}

resource authentication 'Microsoft.Web/sites/config@2024-04-01' = {
  parent: web
  name: 'authsettingsV2'
  properties: {
    platform: { enabled: true, runtimeVersion: '~1' }
    globalValidation: {
      requireAuthentication: true
      unauthenticatedClientAction: 'RedirectToLoginPage'
      redirectToProvider: 'azureactivedirectory'
    }
    httpSettings: { requireHttps: true }
    identityProviders: {
      azureActiveDirectory: {
        enabled: true
        registration: {
          clientId: authClientId
          openIdIssuer: '${environment().authentication.loginEndpoint}${tenantId}/v2.0'
          clientSecretSettingName: 'OVERRIDE_USE_MI_FIC_ASSERTION_CLIENTID'
        }
        validation: {
          allowedAudiences: [authClientId, 'api://${authClientId}']
          defaultAuthorizationPolicy: { allowedPrincipals: { identities: allowedUserIds } }
        }
        login: { loginParameters: ['scope=openid profile email'] }
      }
    }
    login: { tokenStore: { enabled: false } }
  }
}

resource stickySettings 'Microsoft.Web/sites/config@2024-04-01' = {
  parent: web
  name: 'slotConfigNames'
  properties: {
    appSettingNames: [
      'OVERRIDE_USE_MI_FIC_ASSERTION_CLIENTID'
      'AZURE_CLIENT_ID'
      'AZURE_TENANT_ID'
      'CALDOVA_HOSTED'
      'CALDOVA_ALLOWED_USERS'
      'CALDOVA_APPROVERS'
      'CALDOVA_PUBLIC_ORIGIN'
      'CALDOVA_STATE_CONTAINER_URL'
      'CALDOVA_AGENT_ENDPOINT'
      'WEBSITE_AUTH_AAD_ALLOWED_TENANTS'
    ]
  }
}

resource scmPublishing 'Microsoft.Web/sites/basicPublishingCredentialsPolicies@2024-04-01' = {
  parent: web
  name: 'scm'
  properties: { allow: false }
}
resource ftpPublishing 'Microsoft.Web/sites/basicPublishingCredentialsPolicies@2024-04-01' = {
  parent: web
  name: 'ftp'
  properties: { allow: false }
}

output webUrl string = origin
output webAppResourceId string = web.id
output identityClientId string = webIdentity.properties.clientId
output identityPrincipalId string = webIdentity.properties.principalId
output redirectUri string = '${origin}/.auth/login/aad/callback'
output stateContainerUrl string = '${storage.properties.primaryEndpoints.blob}${sessions.name}'