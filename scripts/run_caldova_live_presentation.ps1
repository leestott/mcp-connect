[CmdletBinding()]
param(
    [string]$WebUrl = $env:CALDOVA_LIVE_WEB_URL,
    [switch]$NoLaunch
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$CueScript = Join-Path $PSScriptRoot "present_caldova_demo.ps1"
if (-not (Test-Path $CueScript)) {
    throw "Presenter cue controller is missing at $CueScript."
}
if ([string]::IsNullOrWhiteSpace($WebUrl)) {
    throw "Supply -WebUrl or set CALDOVA_LIVE_WEB_URL after an authenticated website is deployed."
}

$uri = $null
if (
    -not [Uri]::TryCreate($WebUrl, [UriKind]::Absolute, [ref]$uri) -or
    $uri.Scheme -ne "https" -or
    [string]::IsNullOrWhiteSpace($uri.Host) -or
    $uri.IsLoopback -or
    -not [string]::IsNullOrEmpty($uri.UserInfo) -or
    -not [string]::IsNullOrEmpty($uri.Fragment)
) {
    throw "The live website URL must be an absolute, non-loopback HTTPS URL without credentials or a fragment."
}

function Write-Checkpoint {
    param(
        [string]$Title,
        [string]$Surface,
        [string]$Action
    )

    Write-Host ""
    Write-Host ("-" * 78) -ForegroundColor DarkGray
    Write-Host $Title -ForegroundColor Cyan
    Write-Host "Surface: $Surface" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "ACTION:" -ForegroundColor Yellow
    Write-Host $Action
    Write-Host ""
}

function Confirm-Evidence {
    param(
        [string]$Evidence,
        [string]$Summary
    )

    Write-Host "VISIBLE EVIDENCE REQUIRED:" -ForegroundColor Yellow
    Write-Host $Evidence
    Write-Host ""
    $answer = Read-Host "ENTER=confirmed  F=hosted fallback  Q=quit"
    switch ($answer.Trim().ToUpperInvariant()) {
        "F" {
            Write-Host ""
            Write-Host "HOSTED EXECUTION NOT CONFIRMED" -ForegroundColor Yellow
            Write-Host "Use the runbook's labelled source walkthrough. Do not claim a successful live invocation, identity, trace, or mutation."
            exit 2
        }
        "Q" {
            Write-Host "Live presentation control stopped. Browser state was preserved." -ForegroundColor Yellow
            exit 0
        }
    }
    Write-Host ""
    Write-Host "SUMMARY:" -ForegroundColor Green
    Write-Host "`"$Summary`""
}

Write-Host "CALDOVA LIVE TERMINAL / BROWSER CONTROL" -ForegroundColor Cyan
Write-Host "Terminal calls only the independent local MCP stdio inspection." -ForegroundColor DarkGray
Write-Host "All authenticated agent and mutation actions remain in the HTTPS browser." -ForegroundColor DarkGray

Write-Checkpoint `
    -Title "DEMO 01 - REAL MCP STDIO INSPECTION" `
    -Surface "Terminal" `
    -Action "Run the independent MCP inspection. Keep this output in terminal scrollback for the later failure-lab handoff."

& powershell.exe `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File $CueScript `
    inspect
if ($LASTEXITCODE -ne 0) {
    throw "MCP stdio inspection failed with exit code $LASTEXITCODE."
}

Write-Host ""
Write-Host "SUMMARY:" -ForegroundColor Green
Write-Host '"The terminal negotiated real MCP stdio, discovered the tools, returned four positions and 2,196 units, rejected malformed input and an unauthorised write, and left its independent inventory unchanged with zero model calls."'

Write-Checkpoint `
    -Title "BROWSER HANDOFF - AUTHENTICATED HOSTED CONTROL TOWER" `
    -Surface "Browser" `
    -Action "Open the live site, complete Entra sign-in, and wait for the Control Tower state to load."

if (-not $NoLaunch) {
    Start-Process $uri.AbsoluteUri
}

Confirm-Evidence `
    -Evidence "The page shows HOSTED, FOUNDRY HOSTED AGENT, the signed-in identity, four available locations, and 2,196 units. The approver control must reflect the identity's actual authorization." `
    -Summary "The browser is now using the authenticated hosted path. Identity comes from the hosting platform, and this session's durable state is isolated by tenant and object identity."

Write-Checkpoint `
    -Title "DEMO 02 - LIVE AGENT ANALYSIS" `
    -Surface "Browser" `
    -Action "Select Run analysis. Wait up to 30 seconds for useful output; if none appears, choose F and use the labelled source fallback."

Confirm-Evidence `
    -Evidence "A nonempty hosted assessment is visible with a Response ID and, when returned by the service, a Request ID. It reports four locations and 2,196 units, and requires human approval without claiming quarantine." `
    -Summary "The hosted read-only workflow completed an actual response and preserved service correlation. The agent assessed evidence; it did not approve or mutate inventory."

Write-Checkpoint `
    -Title "DEMO 03 - FAILURE BOUNDARY" `
    -Surface "Terminal" `
    -Action "Switch back to the persisted DEMO 01 output and point to sections 5, 6, and 7: validation error, policy error, and unchanged inventory."

Confirm-Evidence `
    -Evidence "The terminal still shows isError for malformed input, isError for the schema-valid unauthorised write, inventory_unchanged true, and model_calls 0." `
    -Summary "Typed input did not grant authority. Validation and policy failed independently, and the denied operation changed no stock."

Write-Checkpoint `
    -Title "DEMO 04 - AUTHENTICATED APPROVAL AND QUARANTINE" `
    -Surface "Browser" `
    -Action "Return to the browser. Select Approve quarantine and complete the hosted confirmation using the signed-in approver identity."

Confirm-Evidence `
    -Evidence "The first authorised result records four positions changed and 2,196 units quarantined. The displayed approver is the authenticated identity, not a typed local label." `
    -Summary "The server bound approval to the authenticated actor, batch, action, session generation, and expiry. The first authorised call changed exactly four positions and 2,196 units."

Write-Checkpoint `
    -Title "DEMO 05 - REPLAY AND AUDIT" `
    -Surface "Browser" `
    -Action "Select Replay quarantine, then compare First authorised call with Latest replay in Quarantine evidence and inspect the audit trail."

Confirm-Evidence `
    -Evidence "Latest replay records zero positions changed and idempotent replay. First authorised call still records four positions changed. The audit contains approval and both quarantine outcomes." `
    -Summary "The repeated authorised operation changed zero additional positions. The browser preserved separate evidence for the first mutation and the latest replay."

Write-Host ""
Write-Host "LIVE DEMO CHECKPOINTS COMPLETE" -ForegroundColor Green
Write-Host "Preserve the browser state for questions. Use the authenticated Reset demo control only after the session."
