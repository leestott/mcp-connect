[CmdletBinding()]
param(
    [string]$BaseUri = "http://127.0.0.1:8091",
    [switch]$AutoAdvance
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$CueScript = Join-Path $PSScriptRoot "present_caldova_demo.ps1"
if (-not (Test-Path $CueScript)) {
    throw "Presenter cue controller is missing at $CueScript."
}

$steps = @(
    [pscustomobject]@{
        Cue = "preflight"
        Label = "PRE-SHOW - Validate local contracts"
        Timing = "Before the audience enters"
        Surface = "Terminal"
        BeforeLabel = "OPERATOR NOTE"
        Before = "Confirm the localhost server is already running. This check runs the focused contracts and verifies the untouched synthetic fixture."
        AfterLabel = "OPERATOR CONFIRMATION"
        After = "Python 3.13, the focused contracts, and the four-location fixture are ready. Do not present this as audience-facing evidence."
    },
    [pscustomobject]@{
        Cue = "reset"
        Label = "PRE-SHOW - Reset synthetic scenario"
        Timing = "Before slide 1"
        Surface = "Control Tower"
        BeforeLabel = "OPERATOR NOTE"
        Before = "Reset only this local synthetic scenario before the talk. This clears prior approval, quarantine, replay, and audit state."
        AfterLabel = "OPERATOR CONFIRMATION"
        After = "The browser should now show four available positions, 2,196 units, no active run, and no control events."
    },
    [pscustomobject]@{
        Cue = "inspect"
        Label = "DEMO 01 - MCP stdio inspection"
        Timing = "Slide 5; terminal segment"
        Surface = "Terminal"
        AfterLabel = "SUMMARY"
        After = "We discovered seven tools, inspected the inventory schema, and received structured evidence for four positions and 2,196 units. Malformed input failed validation, and a schema-valid but unauthorised write failed policy. The stock stayed unchanged and no model was called."
    },
    [pscustomobject]@{
        Cue = "analysis"
        Label = "DEMO 02 - Deterministic local analysis"
        Timing = "Stock evidence by 5:00"
        Surface = "Control Tower"
        AfterLabel = "SUMMARY"
        After = "The application made exactly three read-only calls: recall notice, inventory, and supplier status. It established four affected locations and 2,196 units, then stopped at a named human approval boundary. Analysis did not authorise a mutation."
    },
    [pscustomobject]@{
        Cue = "deny"
        Label = "DEMO 03 - Failure lab"
        Timing = "Failure evidence by 13:00"
        Surface = "Terminal, then Control Tower"
        AfterLabel = "SUMMARY"
        After = "The application returned HTTP 403 and all four inventory positions remained unchanged. The earlier terminal failure was an MCP tool error; this one is an application authorization gate. Both boundaries fail closed."
    },
    [pscustomobject]@{
        Cue = "approve"
        Label = "DEMO 04 - Named approval and quarantine"
        Timing = "Approval evidence by 16:00"
        Surface = "Control Tower"
        AfterLabel = "SUMMARY"
        After = "The first authorised call changed exactly four positions and quarantined 2,196 units. That mutation happened below the model boundary through deterministic policy and tool code. The local approval and audit state are in memory, not production compliance evidence."
    },
    [pscustomobject]@{
        Cue = "replay"
        Label = "DEMO 05 - Idempotent replay"
        Timing = "Replay evidence by 17:00"
        Surface = "Control Tower"
        AfterLabel = "SUMMARY"
        After = "The replay changed zero additional positions and was explicitly recorded as idempotent. The final state is still four quarantined positions and 2,196 units, not a second mutation disguised as success."
    },
    [pscustomobject]@{
        Cue = "audit"
        Label = "DEMO 05 - Audit comparison"
        Timing = "Immediately after replay"
        Surface = "Terminal or Control Tower"
        AfterLabel = "SUMMARY"
        After = "The audit shows the synthetic named approval, a first quarantine with four positions changed, and a replay with zero positions changed. This is useful demonstration evidence, but it remains local and in memory. Production requires authenticated identity, durable transactional state, and tamper-evident audit."
    }
)

function Show-Step {
    param(
        [int]$Index,
        [pscustomobject]$Step
    )

    Write-Host ""
    Write-Host ("-" * 78) -ForegroundColor DarkGray
    Write-Host "CALDOVA PRESENTATION CONTROL" -ForegroundColor Cyan
    Write-Host "Local deterministic path - no hosted-agent invocation" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "Step $($Index + 1) of $($steps.Count): $($Step.Label)" -ForegroundColor Yellow
    Write-Host "Timing:  $($Step.Timing)"
    Write-Host "Surface: $($Step.Surface)"
    Write-Host "Cue:     $($Step.Cue)"
    Write-Host ""
    if ($Step.PSObject.Properties.Name -contains "Before") {
        Write-Host "$($Step.BeforeLabel):" -ForegroundColor Green
        Write-Host "`"$($Step.Before)`"" -ForegroundColor White
        Write-Host ""
    }
}

function Invoke-Cue {
    param([string]$Cue)

    & powershell.exe `
        -NoProfile `
        -ExecutionPolicy Bypass `
        -File $CueScript `
        $Cue `
        -BaseUri $BaseUri

    if ($LASTEXITCODE -ne 0) {
        throw "Presentation cue '$Cue' failed with exit code $LASTEXITCODE."
    }
}

function Show-After {
    param([pscustomobject]$Step)

    Write-Host ""
    Write-Host "$($Step.AfterLabel):" -ForegroundColor Green
    Write-Host "`"$($Step.After)`"" -ForegroundColor White
}

$index = 0
while ($index -lt $steps.Count) {
    $step = $steps[$index]
    Show-Step -Index $index -Step $step

    if (-not $AutoAdvance) {
        $action = Read-Host "ENTER=run  S=skip  R=repeat previous  Q=quit"
        switch ($action.Trim().ToUpperInvariant()) {
            "Q" {
                Write-Host "Presentation control stopped. Demo state was preserved." -ForegroundColor Yellow
                exit 0
            }
            "S" {
                $index++
                continue
            }
            "R" {
                if ($index -eq 0) {
                    Write-Host "There is no previous cue to repeat." -ForegroundColor Yellow
                    Start-Sleep -Seconds 1
                    continue
                }
                $previous = $steps[$index - 1]
                Invoke-Cue -Cue $previous.Cue
                Show-After -Step $previous
                continue
            }
        }
    }

    Invoke-Cue -Cue $step.Cue
    Show-After -Step $step

    if (-not $AutoAdvance) {
        Write-Host ""
        Read-Host "Cue passed. Press ENTER for the next presentation checkpoint"
    }
    $index++
}

Write-Host ""
Write-Host "PRESENTATION DEMOS COMPLETE" -ForegroundColor Green
Write-Host "The quarantined state is preserved for questions."
Write-Host "Run 'caldova-demo reset' after the session."
