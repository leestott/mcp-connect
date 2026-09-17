[CmdletBinding()]
param(
    [ValidateSet('Package', 'Validate', 'Preview', 'Provision', 'Publish')]
    [string]$Action = 'Validate',
    [string]$ParametersFile,
    [string]$SubscriptionId,
    [string]$ResourceGroup,
    [string]$WebAppName,
    [switch]$ApprovedDeployment
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$output = Join-Path $root '.azure/web'
$null = New-Item -ItemType Directory -Force -Path $output
$template = Join-Path $PSScriptRoot 'main.bicep'
$compiled = Join-Path $output 'main.json'

function Invoke-Azure {
    param([string[]]$Arguments)
    & az @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Azure CLI failed for $($Arguments[0])." }
}

function New-WebPackage {
    $source = Join-Path $root 'caldova-recall-control'
    $files = [ordered]@{
        'requirements.txt' = '../infra/web/requirements.txt'
        'requirements-ui.txt' = 'requirements-ui.txt'
        'src/control_tower_api.py' = 'src/control_tower_api.py'
        'src/online_control.py' = 'src/online_control.py'
        'src/hosted_analysis.py' = 'src/hosted_analysis.py'
        'src/agent-framework-workflows-responses/caldova_domain.py' = 'src/agent-framework-workflows-responses/caldova_domain.py'
        'src/agent-framework-workflows-responses/caldova_mcp.py' = 'src/agent-framework-workflows-responses/caldova_mcp.py'
        'src/agent-framework-workflows-responses/requirements-mcp.txt' = 'src/agent-framework-workflows-responses/requirements-mcp.txt'
        'src/control_tower_static/index.html' = 'src/control_tower_static/index.html'
        'src/control_tower_static/app.js' = 'src/control_tower_static/app.js'
        'src/control_tower_static/styles.css' = 'src/control_tower_static/styles.css'
    }
    foreach ($relative in $files.Values) {
        if (-not (Test-Path -LiteralPath (Join-Path $source $relative) -PathType Leaf)) {
            throw "Missing package source: $relative"
        }
    }
    $zipPath = Join-Path $output ('web-' + [guid]::NewGuid().ToString('N') + '.zip')
    $archive = [IO.Compression.ZipFile]::Open($zipPath, [IO.Compression.ZipArchiveMode]::Create)
    try {
        foreach ($entry in $files.GetEnumerator()) {
            $null = [IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $archive, (Join-Path $source $entry.Value), $entry.Key,
                [IO.Compression.CompressionLevel]::Optimal)
        }
    } finally { $archive.Dispose() }
    $inspect = [IO.Compression.ZipFile]::OpenRead($zipPath)
    try {
        if ($inspect.Entries.Count -ne $files.Count) { throw 'ZIP entry count mismatch.' }
        foreach ($entry in $inspect.Entries) {
            if (-not $files.Contains($entry.FullName)) { throw 'Unexpected ZIP entry.' }
        }
    } finally { $inspect.Dispose() }
    Get-FileHash -LiteralPath $zipPath -Algorithm SHA256 | Select-Object Path, Hash
    return $zipPath
}

if ($Action -eq 'Package') { New-WebPackage; return }
Invoke-Azure @('bicep', 'build', '--file', $template, '--outfile', $compiled)
$arm = Get-Content -LiteralPath $compiled -Raw | ConvertFrom-Json -AsHashtable
$site = @($arm.resources | Where-Object type -eq 'Microsoft.Web/sites')[0]
$auth = @($arm.resources | Where-Object { $_.type -eq 'Microsoft.Web/sites/config' -and $_.name -match 'authsettingsV2' })[0]
$storage = @($arm.resources | Where-Object type -eq 'Microsoft.Storage/storageAccounts')[0]
$settings = @($site.properties.siteConfig.appSettings.name)
foreach ($name in @('CALDOVA_HOSTED', 'CALDOVA_AGENT_ENDPOINT', 'CALDOVA_STATE_CONTAINER_URL', 'CALDOVA_PUBLIC_ORIGIN', 'CALDOVA_ALLOWED_USERS', 'CALDOVA_APPROVERS', 'AZURE_TENANT_ID', 'AZURE_CLIENT_ID', 'AZURE_AI_MODEL_DEPLOYMENT_NAME', 'OVERRIDE_USE_MI_FIC_ASSERTION_CLIENTID')) {
    if ($name -notin $settings) { throw "Missing runtime setting: $name" }
}
if (-not $site.properties.httpsOnly -or -not $auth.properties.platform.enabled -or -not $auth.properties.globalValidation.requireAuthentication) {
    throw 'HTTPS and platform authentication must be enforced.'
}
if ($storage.properties.allowBlobPublicAccess -or $storage.properties.allowSharedKeyAccess) {
    throw 'Storage anonymous or shared-key access must be disabled.'
}
Write-Output 'PASS: Bicep compilation and runtime/security contract checks.'
if ($Action -eq 'Validate') { return }
if (-not $SubscriptionId -or -not $ResourceGroup -or -not $ParametersFile) {
    throw 'Explicit SubscriptionId, ResourceGroup and ParametersFile are required for cloud actions.'
}
$parameters = Get-Content -LiteralPath $ParametersFile -Raw | ConvertFrom-Json
if ([guid]$parameters.parameters.authClientId.value -eq [guid]::Empty -or [guid]$parameters.parameters.tenantId.value -eq [guid]::Empty) {
    throw 'Replace example identity IDs with verified registration and tenant IDs.'
}
if ($parameters.parameters.webAppName.value -notmatch '^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$' -or $parameters.parameters.storageAccountName.value -notmatch '^[a-z0-9]{3,24}$') {
    throw 'Invalid App Service or storage account name.'
}
foreach ($approver in $parameters.parameters.approverIds.value) {
    if ($approver -notin $parameters.parameters.allowedUserIds.value) { throw 'Every approver must be an allowed user.' }
}
$context = Invoke-Azure @('account', 'show', '--subscription', $SubscriptionId, '--output', 'json') | ConvertFrom-Json
if ($context.tenantId -ne $parameters.parameters.tenantId.value) { throw 'Subscription tenant mismatch.' }
$common = @('--subscription', $SubscriptionId, '--resource-group', $ResourceGroup, '--template-file', $compiled, '--parameters', "@$ParametersFile")
if ($Action -eq 'Preview') {
    Invoke-Azure (@('deployment', 'group', 'validate') + $common + @('--output', 'none'))
    Invoke-Azure (@('deployment', 'group', 'what-if') + $common + @('--mode', 'Incremental', '--result-format', 'ResourceIdOnly'))
    return
}
if (-not $ApprovedDeployment) { throw 'Explicit cost and deployment consent is required; pass ApprovedDeployment only after consent.' }
$status = Get-Content -LiteralPath (Join-Path $root '.azure/validate-status.json') -Raw | ConvertFrom-Json
if ($status.completedStep -ne 'UpdateStatus') { throw 'Complete the azure-validate workflow for the web artifacts first.' }
$plan = Get-Content -LiteralPath (Join-Path $root '.azure/deployment-plan.md') -Raw
$activeWebPlan = ($plan -split '(?m)^---\s*$', 2)[0]
if ($activeWebPlan -notmatch '(?m)^\*\*Status:\*\* Validated') { throw 'The active web plan must be Validated, not a historical Foundry plan.' }
if ($Action -eq 'Provision') {
    Invoke-Azure (@('deployment', 'group', 'create', '--name', 'caldova-web', '--mode', 'Incremental') + $common + @('--query', 'properties.outputs', '--output', 'json'))
    return
}
if (-not $WebAppName -or $WebAppName -ne $parameters.parameters.webAppName.value) { throw 'WebAppName must match the approved parameters.' }
$resourceId = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.Web/sites/$WebAppName"
$deployedAuth = Invoke-Azure @('rest', '--method', 'get', '--url', "https://management.azure.com$resourceId/config/authsettingsV2/list?api-version=2024-04-01", '--subscription', $SubscriptionId) | ConvertFrom-Json
if (-not $deployedAuth.properties.platform.enabled -or -not $deployedAuth.properties.globalValidation.requireAuthentication) { throw 'Do not publish before EasyAuth is enforced.' }
$provider = $deployedAuth.properties.identityProviders.azureActiveDirectory
if (-not $provider.enabled -or $provider.registration.clientId -ne $parameters.parameters.authClientId.value -or $provider.registration.openIdIssuer -ne "https://login.microsoftonline.com/$($parameters.parameters.tenantId.value)/v2.0" -or $provider.registration.clientSecretSettingName -ne 'OVERRIDE_USE_MI_FIC_ASSERTION_CLIENTID') {
    throw 'Deployed EasyAuth does not match the approved secretless tenant/client configuration.'
}
$identityDifference = @(Compare-Object -ReferenceObject @($parameters.parameters.allowedUserIds.value) -DifferenceObject @($provider.validation.defaultAuthorizationPolicy.allowedPrincipals.identities))
if ($identityDifference.Count) { throw 'Deployed EasyAuth caller allowlist differs from the approved parameters.' }
$packageResults = @(New-WebPackage)
$zip = $packageResults[-1]
Invoke-Azure @('webapp', 'deploy', '--subscription', $SubscriptionId, '--resource-group', $ResourceGroup, '--name', $WebAppName, '--src-path', $zip, '--type', 'zip', '--track-status', 'false', '--output', 'none')
Write-Output 'Code upload completed. Authenticated browser and live-agent verification are still required.'