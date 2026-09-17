---
name: caldova-local-demo
description: 'Run and troubleshoot the Caldova deterministic local demo. Use when: setting up the Control Tower, inspecting real MCP stdio tools and schemas, rehearsing approval and quarantine replay, or testing local recall contracts without cloud calls.'
---

# Caldova Local Demo

## Scope

Use synthetic batch `B-2408-AX7`: 2,196 units across four locations. This is educational software, not a clinical recall system. Read the [application guide](../../../caldova-recall-control/README.md) and [security boundary](../../../SECURITY.md).

The browser API calls MCP in process and constructs its brief deterministically. Its stage rail is not model telemetry. The separate Foundry workflow runs sequential specialists and a tool-free supervisor; it cannot approve or quarantine. Its outer subprocess bridge is custom CLI/JSON IPC, with MCP in process inside the child. Only the inspection command below demonstrates actual MCP stdio.

## Workflow

1. Confirm the working directory is the repository root containing the root [README](../../../README.md). Inspect existing environments and running tasks before changing anything. Use Python 3.13 and the project environment; do not install MCP v2 into the separate Foundry hosting environment.
2. If setup is explicitly requested and the environment is missing, select a Python 3.13 interpreter, create `caldova-recall-control/.venv`, and install the existing [UI requirements](../../../caldova-recall-control/requirements-ui.txt) and [test requirements](../../../caldova-recall-control/requirements-test.txt) with that interpreter. Otherwise report missing prerequisites rather than installing automatically.
3. Run the focused local contract checks and stdio inspection below. Check discovery, schemas, structured inventory, malformed-input rejection, and denied mutation with unchanged stock. The inspection owns independent synthetic state and does not create usable approval credentials.
4. Reuse the **Run Caldova Control Tower** VS Code task with the selected project interpreter, or run the server command below. Stay on `127.0.0.1`; never expose the unauthenticated demo through a public bind or tunnel. If the port is occupied, reuse a verified demo instance or choose another free local port without killing unknown processes.
5. At `http://127.0.0.1:8091`, run analysis, enter a synthetic approver name, and submit approval/quarantine. Expect four positions and 2,196 units changed; replay must change zero additional positions. A typed name is not authentication, and local audit/state is in memory. Reset only the presenter's own synthetic scenario when authorized.
6. Report commands, actual results, URL/port, and whether state was reset. Do not infer hosted-agent success from local checks. For failures, start with the relevant [API tests](../../../caldova-recall-control/tests/test_control_tower_api.py) or [MCP tests](../../../caldova-recall-control/tests/test_caldova_mcp.py), not a dependency upgrade.

## Commands

All commands run from the repository root in PowerShell. On macOS/Linux use `caldova-recall-control/.venv/bin/python`; in a POSIX shell invoke that executable directly instead of PowerShell's `& $Python`.

```powershell
$Python = './caldova-recall-control/.venv/Scripts/python.exe'
if (-not (Test-Path $Python)) { throw 'Select or set up the project Python 3.13 environment first.' }
& $Python -m pytest caldova-recall-control/tests/test_caldova_domain.py caldova-recall-control/tests/test_caldova_mcp.py -q
& $Python caldova-recall-control/scripts/inspect_mcp.py
& $Python -m uvicorn control_tower_api:app --app-dir caldova-recall-control/src --host 127.0.0.1 --port 8091
```

Run the server only after the checks finish successfully, in its own long-running terminal. Ensure `CALDOVA_HOSTED` is not `1` for this deterministic walkthrough; do not silently override a deliberately configured online environment. No Azure sign-in, provisioning, deployment, evaluation, or spending is part of this skill.