[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("preflight", "inspect", "analysis", "deny", "approve", "replay", "audit", "reset")]
    [string]$Cue,

    [string]$BaseUri = "http://127.0.0.1:8091"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Net.Http

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot "caldova-recall-control\.venv\Scripts\python.exe"
$StatePath = Join-Path ([System.IO.Path]::GetTempPath()) "caldova-presenter-state.json"
$ExpectedBatch = "B-2408-AX7"

function Write-Cue {
    param([string]$Message)
    Write-Host ""
    Write-Host "=== $Message ===" -ForegroundColor Cyan
}

function Assert-Demo {
    param(
        [bool]$Condition,
        [string]$Message
    )
    if (-not $Condition) {
        throw $Message
    }
}

function Invoke-DemoRequest {
    param(
        [ValidateSet("GET", "POST")]
        [string]$Method,
        [string]$Path,
        [hashtable]$Body
    )

    $client = [System.Net.Http.HttpClient]::new()
    try {
        $uri = "$($BaseUri.TrimEnd('/'))$Path"
        if ($Method -eq "GET") {
            $response = $client.GetAsync($uri).GetAwaiter().GetResult()
        }
        else {
            $json = if ($null -eq $Body) { "{}" } else { $Body | ConvertTo-Json -Compress }
            $content = [System.Net.Http.StringContent]::new(
                $json,
                [System.Text.Encoding]::UTF8,
                "application/json"
            )
            $response = $client.PostAsync($uri, $content).GetAwaiter().GetResult()
        }

        $text = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        $parsed = if ([string]::IsNullOrWhiteSpace($text)) {
            $null
        }
        else {
            $text | ConvertFrom-Json
        }

        return [pscustomobject]@{
            StatusCode = [int]$response.StatusCode
            Body = $parsed
        }
    }
    catch {
        throw "Cannot reach the Caldova Control Tower at $BaseUri. Start the 'Run Caldova Control Tower' task first. $($_.Exception.Message)"
    }
    finally {
        if ($null -ne $client) {
            $client.Dispose()
        }
    }
}

function Assert-Status {
    param(
        [pscustomobject]$Response,
        [int]$Expected,
        [string]$Operation
    )
    if ($Response.StatusCode -ne $Expected) {
        $detail = if ($null -ne $Response.Body -and $null -ne $Response.Body.detail) {
            " $($Response.Body.detail)"
        }
        else {
            ""
        }
        throw "$Operation returned HTTP $($Response.StatusCode), expected $Expected.$detail"
    }
}

function Get-DemoState {
    $response = Invoke-DemoRequest -Method GET -Path "/api/state"
    Assert-Status -Response $response -Expected 200 -Operation "Read state"
    return $response.Body
}

function Assert-LocalScenario {
    param([pscustomobject]$State)
    Assert-Demo ($State.runtime -eq "local") "The server is not in LOCAL / NO MODEL mode."
    Assert-Demo ($State.notice.batch_id -eq $ExpectedBatch) "Unexpected batch: $($State.notice.batch_id)."
    Assert-Demo ($State.inventory.total_units -eq 2196) "Expected 2,196 affected units."
    Assert-Demo ($State.inventory.locations -eq 4) "Expected four affected locations."
}

switch ($Cue.ToLowerInvariant()) {
    "preflight" {
        Write-Cue "PREFLIGHT"
        Assert-Demo (Test-Path $Python) "Project Python is missing at $Python."
        Assert-Demo ($env:CALDOVA_HOSTED -ne "1") "CALDOVA_HOSTED=1. Refusing to run the deterministic local presentation workflow."

        $version = & $Python --version 2>&1
        Assert-Demo ($LASTEXITCODE -eq 0) "Could not run the project Python interpreter."
        Assert-Demo ($version -match "^Python 3\.13\.") "Expected Python 3.13; found $version."
        Write-Host $version

        & $Python -m pytest `
            (Join-Path $RepoRoot "caldova-recall-control\tests\test_caldova_domain.py") `
            (Join-Path $RepoRoot "caldova-recall-control\tests\test_caldova_mcp.py") `
            -q
        Assert-Demo ($LASTEXITCODE -eq 0) "Focused local contract tests failed."

        $state = Get-DemoState
        Assert-LocalScenario $state
        Write-Host "PASS: localhost Control Tower, batch $ExpectedBatch, 4 locations, 2,196 units."
    }

    "inspect" {
        Write-Cue "DEMO 01 - MCP STDIO INSPECTION"
        Assert-Demo (Test-Path $Python) "Project Python is missing at $Python."
        & $Python (Join-Path $RepoRoot "caldova-recall-control\scripts\inspect_mcp.py")
        Assert-Demo ($LASTEXITCODE -eq 0) "MCP stdio inspection failed."
        Write-Host "PASS: discovery, contract, structured result, validation, policy denial, unchanged inventory."
    }

    "analysis" {
        Write-Cue "DEMO 02 - LOCAL ANALYSIS"
        $response = Invoke-DemoRequest -Method POST -Path "/api/analysis"
        Assert-Status -Response $response -Expected 200 -Operation "Run analysis"
        Assert-LocalScenario $response.Body
        $incomplete = @($response.Body.workflow | Where-Object { $_.status -ne "complete" })
        Assert-Demo ($incomplete.Count -eq 0) "One or more deterministic workflow stages did not complete."
        Assert-Demo ($response.Body.last_result.status -eq "approval_required") "Analysis did not stop at the approval boundary."
        Assert-Demo (@($response.Body.calls).Count -eq 3) "Expected exactly three read-only MCP calls."
        Write-Host "PASS: 3 read-only MCP calls; four stages complete; named approval required."
    }

    "deny" {
        Write-Cue "DEMO 03 - DENIED WRITE"
        $before = Get-DemoState
        Assert-LocalScenario $before
        $beforeStatuses = @($before.inventory.positions | ForEach-Object { "$($_.location):$($_.status)" })

        $response = Invoke-DemoRequest -Method POST -Path "/api/quarantine" -Body @{
            approval_id = "not-approved"
        }
        Assert-Status -Response $response -Expected 403 -Operation "Denied quarantine"

        $after = Get-DemoState
        Assert-LocalScenario $after
        $afterStatuses = @($after.inventory.positions | ForEach-Object { "$($_.location):$($_.status)" })
        Assert-Demo (($beforeStatuses -join "|") -eq ($afterStatuses -join "|")) "Inventory changed after the denied request."
        Write-Host "PASS: HTTP 403; inventory unchanged at four positions and 2,196 units."
    }

    "approve" {
        Write-Cue "DEMO 04 - APPROVE AND QUARANTINE"
        $state = Get-DemoState
        Assert-LocalScenario $state
        Assert-Demo ($null -ne $state.last_result -and $state.last_result.status -eq "approval_required") "Run the analysis cue before approval."

        $approval = Invoke-DemoRequest -Method POST -Path "/api/approval" -Body @{
            approver = "Asha Rao, Responsible Pharmacist"
        }
        Assert-Status -Response $approval -Expected 200 -Operation "Request approval"
        Assert-Demo ($approval.Body.status -eq "approved") "The named approval was not issued."

        $quarantine = Invoke-DemoRequest -Method POST -Path "/api/quarantine" -Body @{
            approval_id = $approval.Body.approval_id
        }
        Assert-Status -Response $quarantine -Expected 200 -Operation "Quarantine"
        Assert-Demo ($quarantine.Body.last_result.positions_changed -eq 4) "Expected four positions to change."
        Assert-Demo ($quarantine.Body.last_result.units_quarantined -eq 2196) "Expected 2,196 units to be quarantined."
        Assert-Demo ($quarantine.Body.last_result.idempotent_replay -eq $false) "The first authorised call was unexpectedly marked as a replay."

        @{
            base_uri = $BaseUri
            approval_id = $approval.Body.approval_id
        } | ConvertTo-Json | Set-Content -Path $StatePath -Encoding UTF8

        Write-Host "PASS: synthetic named approval; 4 positions and 2,196 units quarantined."
        Write-Host "Replay handle retained in the presenter temporary state."
    }

    "replay" {
        Write-Cue "DEMO 05 - IDEMPOTENT REPLAY"
        Assert-Demo (Test-Path $StatePath) "No presenter replay handle exists. Run the approve cue first."
        $presenterState = Get-Content -Raw -Path $StatePath | ConvertFrom-Json
        Assert-Demo ($presenterState.base_uri -eq $BaseUri) "The saved replay handle belongs to a different Control Tower URL."

        $response = Invoke-DemoRequest -Method POST -Path "/api/quarantine" -Body @{
            approval_id = $presenterState.approval_id
        }
        Assert-Status -Response $response -Expected 200 -Operation "Replay quarantine"
        Assert-Demo ($response.Body.last_result.positions_changed -eq 0) "Replay changed additional inventory positions."
        Assert-Demo ($response.Body.last_result.idempotent_replay -eq $true) "The repeated call was not identified as a replay."
        Write-Host "PASS: zero additional positions changed; idempotent replay confirmed."
    }

    "audit" {
        Write-Cue "AUDIT EVIDENCE"
        $state = Get-DemoState
        Assert-LocalScenario $state
        Assert-Demo (@($state.audit).Count -gt 0) "No audit events are available."
        $state.audit |
            ForEach-Object {
                $evidence = if ($_.event -eq "approval_issued") {
                    "approver=$($_.details.approver)"
                }
                else {
                    "positions_changed=$($_.details.positions_changed); replay=$($_.details.idempotent_replay)"
                }
                [pscustomobject]@{
                    timestamp = $_.timestamp
                    event = $_.event
                    batch_id = $_.batch_id
                    evidence = $evidence
                }
            } |
            Format-Table -AutoSize
        if ($null -ne $state.last_result) {
            Write-Host "Latest result:"
            $state.last_result | ConvertTo-Json -Depth 6
        }
        Write-Host "PASS: local in-memory audit evidence displayed."
    }

    "reset" {
        Write-Cue "RESET SYNTHETIC SCENARIO"
        $response = Invoke-DemoRequest -Method POST -Path "/api/reset"
        Assert-Status -Response $response -Expected 200 -Operation "Reset demo"
        Assert-LocalScenario $response.Body
        $changed = @($response.Body.inventory.positions | Where-Object { $_.status -ne "available" })
        Assert-Demo ($changed.Count -eq 0) "Reset did not restore every inventory position."
        Assert-Demo ($null -eq $response.Body.last_result) "Reset did not clear the last result."
        if (Test-Path $StatePath) {
            Remove-Item -LiteralPath $StatePath -Force
        }
        Write-Host "PASS: synthetic scenario reset; presenter replay handle removed."
    }
}
