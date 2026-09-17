---
name: caldova-online-controls
description: 'Inspect and test Caldova opt-in online safety contracts and deployment prerequisites. Use when: reviewing CALDOVA_HOSTED, EasyAuth identity, managed identity, Blob session concurrency, live-agent failures, approval binding, replay, or authenticated online-demo readiness.'
---

# Caldova Online Controls

## Scope

The opt-in online implementation is work in progress in the working tree at authoring time, not committed or cloud-proven evidence. Recheck its current diff and tests. The [README](../../../caldova-recall-control/README.md), [security guidance](../../../SECURITY.md), and [delivery checklist](../../../caldova-recall-control/TODO.md) may describe the earlier disconnected local/hosted boundary; use source for implemented behavior and actual deployment evidence for operational claims.

## Workflow

1. Read the opt-in routing and lifespan in [control_tower_api.py](../../../caldova-recall-control/src/control_tower_api.py), then [online_control.py](../../../caldova-recall-control/src/online_control.py) and [hosted_analysis.py](../../../caldova-recall-control/src/hosted_analysis.py). `CALDOVA_HOSTED=1` selects online controls; local mode remains deterministic. Do not turn the flag on against real resources just to run unit tests.
2. Inspect configuration presence without printing values or tokens. Discover `CALDOVA_AGENT_ENDPOINT`, `CALDOVA_STATE_CONTAINER_URL`, `CALDOVA_PUBLIC_ORIGIN`, `CALDOVA_ALLOWED_USERS`, `CALDOVA_APPROVERS`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, and `AZURE_AI_MODEL_DEPLOYMENT_NAME` from the intended environment. `WEBSITE_HOSTNAME` is a platform prerequisite, not proof of authentication. Do not invent endpoints or identity IDs.
3. Verify the identity boundary: code trusts the platform-injected `x-ms-client-principal` header. It does not validate a JWT itself. A deployed host must enforce restricted Entra sign-in, prevent direct backend/header spoofing, and preserve trusted header handling. Test tenant/user restrictions, ambiguous claims, same-origin mutation checks, and approver authorization. A named local approval is not equivalent to a verified caller.
4. Verify state semantics: sessions are keyed by tenant/object identity, not an independent browser-tab session. Approval handles bind actor, batch, action, generation, and expiry; reset invalidates earlier generations. Review conditional Blob creation and ETag updates, conflict responses, atomic persistence of approval consumption and inventory, replay, analysis leases, cooldown, timeout, and cancellation. Local simulated transport tests do not prove deployed Blob concurrency or isolation.
5. Verify live analysis accepts only completed, nonempty assistant text and retains real response/request correlation. Empty, partial, tool-only, timeout, and upstream failures must fail visibly without authorizing a mutation or silently substituting deterministic analysis. Never invent specialist traces or infer an underlying routed model from the configured deployment label. Keep hosted agent tools read-only.
6. Run the focused offline API tests below. Report mocked/transport-tested behavior separately from missing deployed proof. Use existing fixtures; do not replace them with live credentials or broaden allowlists to make tests pass.
7. Before any separately requested deployment, prepare a plan covering HTTPS/EasyAuth enforcement, restricted audience, least-privilege managed identity for Foundry and Blob, durable storage, approved costs, rollback, and authenticated desktop/mobile verification. Verify anonymous and unauthorized denial, identity isolation, actual agent output, approval/quarantine/replay/reset, concurrency, and failure states against the deployed URL before claiming completion.

## Local Check

From the repository root, in PowerShell with the existing project Python 3.13 environment:

```powershell
$Python = './caldova-recall-control/.venv/Scripts/python.exe'
if (-not (Test-Path $Python)) { throw 'Select the existing project Python 3.13 environment.' }
& $Python -m pytest caldova-recall-control/tests/test_control_tower_api.py -q
```

On macOS/Linux substitute `caldova-recall-control/.venv/bin/python`; invoke it directly in a POSIX shell. The [API tests](../../../caldova-recall-control/tests/test_control_tower_api.py) include offline SDK/transport checks. They are not a cloud smoke test.

## Deployment Handoff

No cloud operations, resource changes, dependency installs, commits, or pushes are authorized by this skill. Obtain separate explicit scope and approval before spending or deployment. If available, use the current official `microsoft-foundry` workflow for the agent and appropriate Azure preparation/validation/deployment workflow for the website. These skills are optional installations, not repository prerequisites. Otherwise consult [hosted-agent deployment](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/deploy-hosted-agent), [App Service authentication](https://learn.microsoft.com/en-us/azure/app-service/overview-authentication-authorization), and [Blob concurrency](https://learn.microsoft.com/en-us/azure/storage/blobs/concurrency-manage) before producing a plan. Use the root [azure.yaml](../../../azure.yaml) for existing azd work; it is not evidence that website infrastructure is implemented. Do not rerun agent initialization.