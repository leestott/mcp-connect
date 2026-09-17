---
name: caldova-presentation-rehearsal
description: 'Build and rehearse the Caldova event presentation using existing decks and assets. Use when: preparing the Bengaluru speaker edition, checking presenter notes and slide layout, rehearsing the 25-minute MCP demo, or choosing an honest hosted-demo fallback.'
---

# Caldova Presentation Rehearsal

## Workflow

1. Read the [presenter runbook](../../../caldova-recall-control/presentation/RUNBOOK.md) and [speaker notes](../../../caldova-recall-control/presentation/mcp-community-connect-bengaluru-speaker-notes.md). The event edition has 14 main slides and four hidden appendices. Follow the runbook's current deck choice; older technical/Teams drafts are reference material, not interchangeable current evidence.
2. Before rebuilding, inspect pending presentation changes and confirm generation is in scope: builds can rewrite decks and the notes companion. Reuse [build_event_deck.py](../../../caldova-recall-control/presentation/build_event_deck.py), [deck_common.py](../../../caldova-recall-control/presentation/deck_common.py), and existing [assets and attribution](../../../caldova-recall-control/presentation/assets/README.md). Edit the owning generator only if requested; do not hand-edit generated slides or introduce duplicate asset pipelines.
3. Build the event edition with the existing Python 3.13 environment below. Missing dependencies or artwork are prerequisites to report, not permission to install or fetch replacements. Use [build_deck.py](../../../caldova-recall-control/presentation/build_deck.py) and [build_teams_deck.py](../../../caldova-recall-control/presentation/build_teams_deck.py) only when those decks or the complete CI build are in scope.
4. Inspect the generated deck in Presenter View or an available slide renderer: titles, fonts, overflow, image rendering, speaker notes, source links, and hidden appendices. Reuse the existing renders location. A successful build does not prove visual fit or delivery timing. If no renderer is available, report visual validation as pending rather than inventing a screenshot check.
5. Rehearse local MCP stdio inspection before the browser controls. Show discovery, schema constraints, structured results, malformed input, and denied writes. Then show local deterministic analysis, synthetic named approval, four positions/2,196 units quarantined, replay with zero additional changes, and local audit. Label the local API's in-process MCP separately from real stdio and the hosted custom CLI/JSON bridge.
6. Keep the hosted section separate: fixed sequential specialists, tool-free supervisor synthesis, read-only tools. The default local browser is not a hosted-agent invocation. The opt-in online branch is not deployed proof. Do not describe routing, shared live state, Toolboxes, MCP Apps, or event triggers as demonstrated features without fresh evidence.
7. Use only genuine captured response/version/identity/trace evidence for an authorized hosted demonstration. No cloud invocation, evaluation rerun, sign-in, provisioning, deployment, or spending is authorized by rehearsal alone. Without current evidence, use the runbook's four-minute source fallback and explicitly label it a source walkthrough, not successful execution. Label saved screenshots as saved evidence and diagrams as schematic, never real traces.
8. Time the actual delivery: terminal segment 75 seconds, local demo finished by 11:00, hosted segment finished by 17:00, closing slide at 20:30, and three minutes for questions before 25:00. Report measured timings and unresolved content/visual/cloud gates; lengthy notes are preparation material, not proof the talk fits.

## Event Build

From the repository root in PowerShell, after confirming build output changes are authorized:

```powershell
$Python = './caldova-recall-control/.venv/Scripts/python.exe'
if (-not (Test-Path $Python)) { throw 'Select the existing project Python 3.13 environment.' }
& $Python caldova-recall-control/presentation/build_event_deck.py
```

On macOS/Linux substitute `caldova-recall-control/.venv/bin/python`; invoke it directly in a POSIX shell. Use the [local demo skill](../caldova-local-demo/SKILL.md) for server/testing steps and the [evaluation skill](../caldova-evaluation/SKILL.md) for evidence review. Preserve unrelated work, synthetic-data boundaries, artwork attribution, and ignored generated output. Never commit or push as part of rehearsal.