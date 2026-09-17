[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('Register', 'Federate')][string]$Action,
    [Parameter(Mandatory)][guid]$TenantId,
    [Parameter(Mandatory)][string]$WebAppName,
    [guid]$ApplicationObjectId,
    [guid]$IdentityPrincipalId,
    [switch]$ApprovedIdentityChanges
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not $ApprovedIdentityChanges) { throw 'Creating an Entra application or federation requires explicit identity-change approval.' }
if ($WebAppName -notmatch '^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$') { throw 'Invalid web app name.' }
$tokenJson = & az account get-access-token --tenant $TenantId --resource https://graph.microsoft.com/ --output json
if ($LASTEXITCODE -ne 0) { throw 'Graph authentication required in the specified tenant. Complete interactive login outside chat.' }
$token = $tokenJson | ConvertFrom-Json
$headers = @{ Authorization = "Bearer $($token.accessToken)" }
$base = 'https://graph.microsoft.com/v1.0'
$displayName = "$WebAppName-easyauth"
$redirect = "https://$WebAppName.azurewebsites.net/.auth/login/aad/callback"
try {
    if ($Action -eq 'Register') {
        $filter = [uri]::EscapeDataString("displayName eq '$displayName'")
        $existing = Invoke-RestMethod -Uri "$base/applications?`$filter=$filter" -Headers $headers
        if (@($existing.value).Count -gt 0) { throw 'Registration already exists. Inspect it and reuse its IDs; no existing application was modified.' }
        $body = @{
            displayName = $displayName
            signInAudience = 'AzureADMyOrg'
            web = @{ redirectUris = @($redirect); implicitGrantSettings = @{ enableIdTokenIssuance = $true; enableAccessTokenIssuance = $false } }
            requiredResourceAccess = @()
        } | ConvertTo-Json -Depth 8
        $app = Invoke-RestMethod -Method Post -Uri "$base/applications" -Headers $headers -ContentType 'application/json' -Body $body
        $spBody = @{ appId = $app.appId } | ConvertTo-Json
        $null = Invoke-RestMethod -Method Post -Uri "$base/servicePrincipals" -Headers $headers -ContentType 'application/json' -Body $spBody
        [pscustomobject]@{ ApplicationObjectId = $app.id; AuthClientId = $app.appId; RedirectUri = $redirect }
        return
    }
    if ($ApplicationObjectId -eq [guid]::Empty -or $IdentityPrincipalId -eq [guid]::Empty) { throw 'ApplicationObjectId and IdentityPrincipalId are required.' }
    $app = Invoke-RestMethod -Uri "$base/applications/$ApplicationObjectId" -Headers $headers
    if ($app.displayName -ne $displayName -or $app.signInAudience -ne 'AzureADMyOrg' -or $redirect -notin $app.web.redirectUris) {
        throw 'Application does not match the restricted web registration.'
    }
    $federation = @{
        name = 'caldova-web-managed-identity'
        issuer = "https://login.microsoftonline.com/$TenantId/v2.0"
        subject = $IdentityPrincipalId.ToString()
        audiences = @('api://AzureADTokenExchange')
    }
    $credentials = Invoke-RestMethod -Uri "$base/applications/$ApplicationObjectId/federatedIdentityCredentials" -Headers $headers
    $existing = @($credentials.value | Where-Object name -eq $federation.name)
    if ($existing.Count -gt 0) {
        if ($existing[0].issuer -ne $federation.issuer -or $existing[0].subject -ne $federation.subject -or @($existing[0].audiences).Count -ne 1 -or $existing[0].audiences[0] -ne 'api://AzureADTokenExchange') { throw 'Existing federation differs; refusing to replace it.' }
        Write-Output 'Existing federation matches.'
        return
    }
    $null = Invoke-RestMethod -Method Post -Uri "$base/applications/$ApplicationObjectId/federatedIdentityCredentials" -Headers $headers -ContentType 'application/json' -Body ($federation | ConvertTo-Json)
    Write-Output 'Managed-identity federation created; browser authentication still requires verification.'
} finally {
    $headers.Clear()
    $token = $null
    $tokenJson = $null
}