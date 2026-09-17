targetScope = 'subscription'
// targetScope = 'resourceGroup'

@minLength(1)
@maxLength(64)
@description('Name of the environment that can be used as part of naming resource convention')
param environmentName string

@minLength(1)
@maxLength(90)
@description('Name of the resource group to use or create')
param resourceGroupName string = 'rg-${environmentName}'

// Restricted locations to match list from
// https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/responses?tabs=python-key#region-availability
@minLength(1)
@description('Primary location for all resources')
@allowed([
  'australiaeast'
  'brazilsouth'
  'canadacentral'
  'canadaeast'
  'eastus'
  'eastus2'
  'francecentral'
  'germanywestcentral'
  'italynorth'
  'japaneast'
  'koreacentral'
  'northcentralus'
  'norwayeast'
  'polandcentral'
  'southafricanorth'
  'southcentralus'
  'southeastasia'
  'southindia'
  'spaincentral'
  'swedencentral'
  'switzerlandnorth'
  'uaenorth'
  'uksouth'
  'westus'
  'westus2'
  'westus3'
])
param location string

param aiDeploymentsLocation string = location

@description('Id of the user or app to assign application roles')
param principalId string

@description('Principal type of user or app')
param principalType string

@description('Optional salt to diversify resource names across project recreations')
param resourceTokenSalt string = ''

@description('Optional. Name of an existing AI Services account within the resource group. If not provided, a new one will be created.')
param aiFoundryResourceName string = ''

@description('Microsoft Foundry provider project name.')
param foundryProjectName string = 'ai-project-${environmentName}'

@description('Optional. Name of the AI Foundry project. If not provided, a default name will be used.')
param aiFoundryProjectName string = foundryProjectName

@description('Tags supplied by the Microsoft Foundry provider.')
param tags object = {}

@description('List of model deployments')
param aiProjectDeploymentsJson string = '[]'

@description('List of connections')
param aiProjectConnectionsJson string = '[]'

@secure()
@description('JSON map of connection name to credentials object. Example: {"my-conn":{"key":"secret"}}')
param aiProjectConnectionCredentialsJson string = '{}'

@description('List of resources to create and connect to the AI project')
param aiProjectDependentResourcesJson string = '[]'

// The Foundry provider can pass these JSON payloads with escaped quotes intact; strip
// the escaping so json() parses both the clean parameters-file path and the provider path.
var aiProjectDeployments = json(replace(aiProjectDeploymentsJson, '\\"', '"'))
var aiProjectConnections = json(replace(aiProjectConnectionsJson, '\\"', '"'))
var aiProjectConnectionCreds = json(replace(aiProjectConnectionCredentialsJson, '\\"', '"'))
var aiProjectDependentResources = json(replace(aiProjectDependentResourcesJson, '\\"', '"'))

@description('Enable hosted agent deployment')
@allowed([
  'true'
  'false'
])
param enableHostedAgents string

@description('Enable the capability host for supporting BYO storage of agent conversations. When false and hosted agents are enabled, the capability host is not created.')
@allowed([
  'true'
  'false'
])
param enableCapabilityHost string

@description('Enable monitoring for the AI project')
@allowed([
  'true'
  'false'
])
param enableMonitoring string

@description('When true, skip Foundry project/role/connection provisioning and reference the existing project read-only. Use when pointing at an existing Foundry project via --project-id.')
@allowed([
  'true'
  'false'
])
param useExistingAiProject string = 'false'

@description('Optional. Existing container registry resource ID. If provided, no new ACR will be created and a connection to this ACR will be established.')
param existingContainerRegistryResourceId string = ''

@description('Optional. Existing container registry endpoint (login server). Required if existingContainerRegistryResourceId is provided.')
param existingContainerRegistryEndpoint string = ''

@description('Optional. Name of an existing ACR connection on the Foundry project. If provided, no new ACR or connection will be created.')
param existingAcrConnectionName string = ''

@description('Optional. Skip ACR creation entirely (e.g. for code-deploy scenarios where no container registry is needed). Defaults to false for backward compatibility.')
@allowed([
  'true'
  'false'
])
param skipAcr string = 'false'

@description('Optional. Existing Application Insights connection string. If provided, a connection will be created but no new App Insights resource.')
param existingApplicationInsightsConnectionString string = ''

@description('Optional. Existing Application Insights resource ID. Used for connection metadata when providing an existing App Insights.')
param existingApplicationInsightsResourceId string = ''

@description('Optional. Name of an existing Application Insights connection on the Foundry project. If provided, no new App Insights or connection will be created.')
param existingAppInsightsConnectionName string = ''

var resourceTags = union(tags, {
  'azd-env-name': environmentName
})
var enableHostedAgentsValue = bool(enableHostedAgents)
var enableCapabilityHostValue = bool(enableCapabilityHost)
var enableMonitoringValue = bool(enableMonitoring)
var useExistingAiProjectValue = bool(useExistingAiProject)
var skipAcrValue = bool(skipAcr)

// Check if resource group exists and create it if it doesn't
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: resourceGroupName
  location: location
  tags: resourceTags
}

// Build dependent resources array conditionally
// Check if ACR already exists in the user-provided array to avoid duplicates
// Also skip if user provided an existing container registry endpoint or connection name
var hasAcr = contains(map(aiProjectDependentResources, r => r.resource), 'registry')
var shouldCreateAcr = !skipAcrValue && enableHostedAgentsValue && !hasAcr && empty(existingContainerRegistryResourceId) && empty(existingAcrConnectionName)
var dependentResources = shouldCreateAcr ? union(aiProjectDependentResources, [
  {
    resource: 'registry'
    connectionName: 'acr-${uniqueString(subscription().id, resourceGroupName, location)}'
  }
]) : aiProjectDependentResources

// AI Project module — only when creating new resources
module aiProject 'core/ai/ai-project.bicep' = if (!useExistingAiProjectValue) {
  scope: rg
  name: 'ai-project'
  params: {
    tags: resourceTags
    location: aiDeploymentsLocation
    aiFoundryProjectName: aiFoundryProjectName
    principalId: principalId
    principalType: principalType
    existingAiAccountName: aiFoundryResourceName
    deployments: aiProjectDeployments
    connections: aiProjectConnections
    connectionCredentials: aiProjectConnectionCreds
    additionalDependentResources: dependentResources
    enableMonitoring: enableMonitoringValue
    enableHostedAgents: enableHostedAgentsValue
    enableCapabilityHost: enableCapabilityHostValue
    existingContainerRegistryResourceId: existingContainerRegistryResourceId
    existingContainerRegistryEndpoint: existingContainerRegistryEndpoint
    existingAcrConnectionName: existingAcrConnectionName
    existingApplicationInsightsConnectionString: existingApplicationInsightsConnectionString
    existingApplicationInsightsResourceId: existingApplicationInsightsResourceId
    existingAppInsightsConnectionName: existingAppInsightsConnectionName
    resourceTokenSalt: resourceTokenSalt
  }
}

// Existing project module — read-only reference when reusing an existing Foundry project
module existingAiProject 'core/ai/existing-ai-project.bicep' = if (useExistingAiProjectValue) {
  scope: rg
  name: 'existing-ai-project'
  params: {
    aiServicesAccountName: aiFoundryResourceName
    aiFoundryProjectName: aiFoundryProjectName
    deployments: aiProjectDeployments
    existingAcrConnectionName: existingAcrConnectionName
    existingContainerRegistryEndpoint: existingContainerRegistryEndpoint
    existingApplicationInsightsConnectionString: existingApplicationInsightsConnectionString
    existingApplicationInsightsResourceId: existingApplicationInsightsResourceId
    connections: aiProjectConnections
    connectionCredentials: aiProjectConnectionCreds
  }
}

// ACR for existing project — create when hosted agents need a registry but the existing project has none
var shouldCreateAcrForExistingProject = useExistingAiProjectValue && shouldCreateAcr
var acrConnectionName = 'acr-${uniqueString(subscription().id, resourceGroupName, location)}'

module acrForExistingProject 'core/host/acr.bicep' = if (shouldCreateAcrForExistingProject) {
  scope: rg
  name: 'acr-for-existing-project'
  params: {
    location: location
    tags: resourceTags
    resourceName: 'cr${uniqueString(subscription().id, resourceGroupName, location)}'
    connectionName: acrConnectionName
    principalId: principalId
    principalType: principalType
    aiServicesAccountName: aiFoundryResourceName
    aiProjectName: aiFoundryProjectName
  }
}

// Resources
output AZURE_RESOURCE_GROUP string = resourceGroupName
output AZURE_AI_ACCOUNT_ID string = useExistingAiProjectValue ? existingAiProject.outputs.accountId : aiProject.outputs.accountId
output AZURE_AI_PROJECT_ID string = useExistingAiProjectValue ? existingAiProject.outputs.projectId : aiProject.outputs.projectId
output AZURE_AI_FOUNDRY_PROJECT_ID string = useExistingAiProjectValue ? existingAiProject.outputs.projectId : aiProject.outputs.projectId
output AZURE_AI_ACCOUNT_NAME string = useExistingAiProjectValue ? existingAiProject.outputs.aiServicesAccountName : aiProject.outputs.aiServicesAccountName
output AZURE_AI_PROJECT_NAME string = useExistingAiProjectValue ? existingAiProject.outputs.projectName : aiProject.outputs.projectName

// Endpoints
output AZURE_AI_PROJECT_ENDPOINT string = useExistingAiProjectValue ? existingAiProject.outputs.AZURE_AI_PROJECT_ENDPOINT : aiProject.outputs.AZURE_AI_PROJECT_ENDPOINT
output FOUNDRY_PROJECT_ENDPOINT string = useExistingAiProjectValue ? existingAiProject.outputs.FOUNDRY_PROJECT_ENDPOINT : aiProject.outputs.FOUNDRY_PROJECT_ENDPOINT
output AZURE_OPENAI_ENDPOINT string = useExistingAiProjectValue ? existingAiProject.outputs.AZURE_OPENAI_ENDPOINT : aiProject.outputs.AZURE_OPENAI_ENDPOINT
output APPLICATIONINSIGHTS_CONNECTION_STRING string = useExistingAiProjectValue ? existingAiProject.outputs.APPLICATIONINSIGHTS_CONNECTION_STRING : aiProject.outputs.APPLICATIONINSIGHTS_CONNECTION_STRING
output APPLICATIONINSIGHTS_RESOURCE_ID string = useExistingAiProjectValue ? existingAiProject.outputs.APPLICATIONINSIGHTS_RESOURCE_ID : aiProject.outputs.APPLICATIONINSIGHTS_RESOURCE_ID

// Dependent Resources and Connections

// ACR
output AZURE_AI_PROJECT_ACR_CONNECTION_NAME string = shouldCreateAcrForExistingProject ? acrForExistingProject.outputs.containerRegistryConnectionName : (useExistingAiProjectValue ? existingAiProject.outputs.dependentResources.registry.connectionName : aiProject.outputs.dependentResources.registry.connectionName)
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = shouldCreateAcrForExistingProject ? acrForExistingProject.outputs.containerRegistryLoginServer : (useExistingAiProjectValue ? existingAiProject.outputs.dependentResources.registry.loginServer : aiProject.outputs.dependentResources.registry.loginServer)

// Bing Search
output BING_GROUNDING_CONNECTION_NAME  string = useExistingAiProjectValue ? existingAiProject.outputs.dependentResources.bing_grounding.connectionName : aiProject.outputs.dependentResources.bing_grounding.connectionName
output BING_GROUNDING_RESOURCE_NAME string = useExistingAiProjectValue ? existingAiProject.outputs.dependentResources.bing_grounding.name : aiProject.outputs.dependentResources.bing_grounding.name
output BING_GROUNDING_CONNECTION_ID string = useExistingAiProjectValue ? existingAiProject.outputs.dependentResources.bing_grounding.connectionId : aiProject.outputs.dependentResources.bing_grounding.connectionId

// Bing Custom Search
output BING_CUSTOM_GROUNDING_CONNECTION_NAME string = useExistingAiProjectValue ? existingAiProject.outputs.dependentResources.bing_custom_grounding.connectionName : aiProject.outputs.dependentResources.bing_custom_grounding.connectionName
output BING_CUSTOM_GROUNDING_NAME string = useExistingAiProjectValue ? existingAiProject.outputs.dependentResources.bing_custom_grounding.name : aiProject.outputs.dependentResources.bing_custom_grounding.name
output BING_CUSTOM_GROUNDING_CONNECTION_ID string = useExistingAiProjectValue ? existingAiProject.outputs.dependentResources.bing_custom_grounding.connectionId : aiProject.outputs.dependentResources.bing_custom_grounding.connectionId

// Azure AI Search
output AZURE_AI_SEARCH_CONNECTION_NAME string = useExistingAiProjectValue ? existingAiProject.outputs.dependentResources.search.connectionName : aiProject.outputs.dependentResources.search.connectionName
output AZURE_AI_SEARCH_SERVICE_NAME string = useExistingAiProjectValue ? existingAiProject.outputs.dependentResources.search.serviceName : aiProject.outputs.dependentResources.search.serviceName

// Azure Storage
output AZURE_STORAGE_CONNECTION_NAME string = useExistingAiProjectValue ? existingAiProject.outputs.dependentResources.storage.connectionName : aiProject.outputs.dependentResources.storage.connectionName
output AZURE_STORAGE_ACCOUNT_NAME string = useExistingAiProjectValue ? existingAiProject.outputs.dependentResources.storage.accountName : aiProject.outputs.dependentResources.storage.accountName

// Connections
output AI_PROJECT_CONNECTION_IDS_JSON string = useExistingAiProjectValue ? string(existingAiProject.outputs.connectionIds) : string(aiProject.outputs.connectionIds)
