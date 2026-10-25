targetScope = 'resourceGroup'

@description('Short lowercase prefix, for example hfdev.')
@minLength(3)
@maxLength(12)
param namePrefix string

@description('Azure region. Flex Consumption is not offered in every region.')
param location string = resourceGroup().location

@description('Mailbox that receives the budget alert.')
param alertEmail string

@description('Entra tenant id for SQL and the function identity.')
param tenantId string

@description('Monthly budget in USD for this resource group.')
param budgetAmount int = 50

@description('First day of the current or next month. Consumption budgets require a month start.')
param budgetStart string = '2026-11-01'

@description('Create the Foundry account and project.')
param deployFoundry bool = false

@description('Create Azure AI Search.')
param deploySearch bool = false

@description('Create the API Management AI gateway. Basic v2 is the development tier.')
param deployApim bool = false

@description('Create Entra-only Azure SQL.')
param deploySql bool = false

param sqlAdminGroupName string = 'hf-sql-admins'
param sqlAdminGroupObjectId string = ''

@description('Small model. The Foundry quickstart uses gpt-5-mini. Leave the version empty to skip the deployment.')
param smallModelName string = 'gpt-5-mini'
param smallModelVersion string = ''
param strongModelName string = ''
param strongModelVersion string = ''

@description('Foundry data-plane endpoint used by the gateway, for example https://example.services.ai.azure.com')
param foundryEndpoint string = ''

param pythonVersion string = '3.13'

var compact = toLower(replace(namePrefix, '-', ''))
var token = take(uniqueString(resourceGroup().id), 6)
var storageName = take('${compact}${token}st', 24)
var vaultName = take('${compact}${token}kv', 24)
var functionName = '${compact}-${token}-api'
var foundryAccountName = take('${compact}${token}ai', 24)
var searchName = '${compact}-${token}-search'
var sqlName = '${compact}-${token}-sql'
var apimName = '${compact}-${token}-apim'
var resolvedFoundryEndpoint = foundryEndpoint != '' ? foundryEndpoint : 'https://${foundryAccountName}.services.ai.azure.com'

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${compact}-${token}-logs'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${compact}-${token}-appi'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logs.id
  }
}

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: vaultName
  location: location
  properties: {
    tenantId: tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    publicNetworkAccess: 'Enabled'
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowSharedKeyAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    publicNetworkAccess: 'Enabled'
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  name: 'default'
  parent: storage
}

resource deploymentContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  name: 'app-package'
  parent: blobService
}

resource queueService 'Microsoft.Storage/storageAccounts/queueServices@2023-05-01' = {
  name: 'default'
  parent: storage
}

resource tableService 'Microsoft.Storage/storageAccounts/tableServices@2023-05-01' = {
  name: 'default'
  parent: storage
}

resource plan 'Microsoft.Web/serverfarms@2024-04-01' = {
  name: '${compact}-${token}-plan'
  location: location
  kind: 'functionapp'
  sku: {
    name: 'FC1'
    tier: 'FlexConsumption'
  }
  properties: {
    reserved: true
  }
}

resource functionApp 'Microsoft.Web/sites@2024-04-01' = {
  name: functionName
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      minTlsVersion: '1.2'
    }
    functionAppConfig: {
      deployment: {
        storage: {
          type: 'blobContainer'
          value: '${storage.properties.primaryEndpoints.blob}app-package'
          authentication: {
            type: 'SystemAssignedIdentity'
          }
        }
      }
      scaleAndConcurrency: {
        maximumInstanceCount: 40
        instanceMemoryMB: 2048
      }
      runtime: {
        name: 'python'
        version: pythonVersion
      }
    }
  }
  dependsOn: [
    deploymentContainer
  ]
}

resource appSettings 'Microsoft.Web/sites/config@2024-04-01' = {
  name: 'appsettings'
  parent: functionApp
  properties: {
    AzureWebJobsStorage__credential: 'managedidentity'
    AzureWebJobsStorage__accountName: storage.name
    AzureWebJobsStorage__blobServiceUri: storage.properties.primaryEndpoints.blob
    AzureWebJobsStorage__queueServiceUri: storage.properties.primaryEndpoints.queue
    AzureWebJobsStorage__tableServiceUri: storage.properties.primaryEndpoints.table
    APPLICATIONINSIGHTS_CONNECTION_STRING: appInsights.properties.ConnectionString
    APPLICATIONINSIGHTS_AUTHENTICATION_STRING: 'Authorization=AAD'
    HARBOR_ALLOW_DIRECT: 'false'
    KEY_VAULT_URI: vault.properties.vaultUri
  }
}

var blobContributor = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var queueContributor = '974c5e8b-45b9-4653-ba55-5f855dd0fb88'
var tableContributor = '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'
var keyVaultSecretsUser = '4633458b-17de-408a-b874-0445c86b69e6'
var monitoringPublisher = '3913510d-42f4-4e42-8a64-420c390055eb'

resource functionBlobRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, functionApp.id, blobContributor)
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', blobContributor)
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource functionQueueRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, functionApp.id, queueContributor)
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', queueContributor)
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource functionTableRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, functionApp.id, tableContributor)
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', tableContributor)
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource functionVaultRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(vault.id, functionApp.id, keyVaultSecretsUser)
  scope: vault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUser)
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource functionInsightsRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(appInsights.id, functionApp.id, monitoringPublisher)
  scope: appInsights
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', monitoringPublisher)
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource budget 'Microsoft.Consumption/budgets@2024-08-01' = {
  name: '${compact}-monthly'
  properties: {
    category: 'Cost'
    amount: budgetAmount
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: budgetStart
    }
    notifications: {
      Actual_GreaterThan_80_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 80
        contactEmails: [
          alertEmail
        ]
        thresholdType: 'Actual'
      }
    }
  }
}

resource foundry 'Microsoft.CognitiveServices/accounts@2024-10-01' = if (deployFoundry) {
  name: foundryAccountName
  location: location
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: foundryAccountName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: true
    allowProjectManagement: true
  }
}

resource foundryProject 'Microsoft.CognitiveServices/accounts/projects@2024-10-01' = if (deployFoundry) {
  name: 'harbor'
  parent: foundry
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: 'Harbor'
  }
}

resource smallModel 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = if (deployFoundry && smallModelVersion != '') {
  name: smallModelName
  parent: foundry
  sku: {
    name: 'GlobalStandard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: smallModelName
      version: smallModelVersion
    }
  }
}

resource strongModel 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = if (deployFoundry && strongModelVersion != '') {
  name: strongModelName
  parent: foundry
  sku: {
    name: 'GlobalStandard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: strongModelName
      version: strongModelVersion
    }
  }
}

resource search 'Microsoft.Search/searchServices@2024-06-01-preview' = if (deploySearch) {
  name: searchName
  location: location
  sku: {
    name: 'basic'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
    disableLocalAuth: true
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
  }
}

resource sql 'Microsoft.Sql/servers@2023-08-01-preview' = if (deploySql) {
  name: sqlName
  location: location
  properties: {
    version: '12.0'
    minimalTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
    administrators: {
      administratorType: 'ActiveDirectory'
      principalType: 'Group'
      login: sqlAdminGroupName
      sid: sqlAdminGroupObjectId
      tenantId: tenantId
      azureADOnlyAuthentication: true
    }
  }
}

resource sqlDb 'Microsoft.Sql/servers/databases@2023-08-01-preview' = if (deploySql) {
  name: 'harbor'
  parent: sql
  location: location
  sku: {
    name: 'GP_S_Gen5'
    tier: 'GeneralPurpose'
    family: 'Gen5'
    capacity: 1
  }
  properties: {
    autoPauseDelay: 60
    minCapacity: json('0.5')
    requestedBackupStorageRedundancy: 'Local'
  }
}

resource sqlAzureServices 'Microsoft.Sql/servers/firewallRules@2023-08-01-preview' = if (deploySql) {
  name: 'AllowAzureServices'
  parent: sql
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource apim 'Microsoft.ApiManagement/service@2024-05-01' = if (deployApim) {
  name: apimName
  location: location
  sku: {
    name: 'BasicV2'
    capacity: 1
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    publisherEmail: alertEmail
    publisherName: 'Harbor Field Services'
  }
}

resource miniBackend 'Microsoft.ApiManagement/service/backends@2024-05-01' = if (deployApim) {
  name: 'foundry-mini'
  parent: apim
  properties: {
    protocol: 'http'
    url: '${resolvedFoundryEndpoint}/openai/deployments/${smallModelName}'
    tls: {
      validateCertificateChain: true
      validateCertificateName: true
    }
  }
}

var strongDeploymentName = strongModelName != '' ? strongModelName : smallModelName

resource strongBackend 'Microsoft.ApiManagement/service/backends@2024-05-01' = if (deployApim) {
  name: 'foundry-strong'
  parent: apim
  properties: {
    protocol: 'http'
    url: '${resolvedFoundryEndpoint}/openai/deployments/${strongDeploymentName}'
    tls: {
      validateCertificateChain: true
      validateCertificateName: true
    }
  }
}

resource modelsApi 'Microsoft.ApiManagement/service/apis@2024-05-01' = if (deployApim) {
  name: 'harbor-models'
  parent: apim
  properties: {
    displayName: 'Harbor models'
    path: 'models'
    protocols: [
      'https'
    ]
    subscriptionRequired: true
    serviceUrl: resolvedFoundryEndpoint
  }
}

resource modelsPolicy 'Microsoft.ApiManagement/service/apis/policies@2024-05-01' = if (deployApim) {
  name: 'policy'
  parent: modelsApi
  properties: {
    format: 'rawxml'
    value: loadTextContent('policies/foundry-gateway.xml')
  }
  dependsOn: [
    miniBackend
  ]
}

output functionAppName string = functionApp.name
output keyVaultName string = vault.name
output applicationInsightsName string = appInsights.name
output foundryAccountName string = deployFoundry ? foundryAccountName : ''
output searchServiceName string = deploySearch ? search.name : ''
output sqlServerName string = deploySql ? sql.name : ''
output apimName string = deployApim ? apim.name : ''
