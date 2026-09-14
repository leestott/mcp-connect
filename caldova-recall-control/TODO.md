# Caldova Recall Control Tower - Implementation Plan and Checklist

This preserves implementation history for [SPEC.md](SPEC.md). Checked cloud, evaluation, and presentation items describe previous development observations, not the current status of a public clone. Revalidate them in your own environment. See the [application README](README.md) for current execution boundaries and [SECURITY.md](../SECURITY.md) for limitations.

## Public-sharing follow-up

- [x] Deploy the solution to a new Microsoft Foundry project named `leestott-mcpconnect`, using the account `authorised-deployment-identity`. Deployed 2026-09-14 in ai-team / North Central US after target, permissions, quota, and usage-charge review. Hosted agent version 1 is active; the read-only smoke test returned 2,196 units across four locations, and the final doctor check passed (11 passed, 0 failed). Evaluation and trace review remain separate follow-up work.
- [ ] Verify the hosted deployment, traces, and evaluation results afresh before presenting cloud evidence.
- [ ] Complete a timed rehearsal using the speaker edition and updated runbook.
- [ ] Add verified caller identity and durable transactional state before any production use.
- [ ] Deliver the complete demo online from a hosted website, integrated with the live Foundry agent. This is now a required release gate; the browser and agent currently run separately.

## Required online demo delivery

The complete presenter scenario must work from an HTTPS website without a local server, terminal, or developer credentials. A read-only online preview is an intermediate milestone, not completion of this requirement. Keep the existing local demonstration available as a fallback.

- [ ] Deploy the frontend and API with reproducible infrastructure, restricted Entra sign-in, managed identity, least-privilege project access, and documented hosting costs.
- [ ] Connect browser analysis through the backend to the live `leestott-mcpconnect` agent. Render its actual response safely and record agent version, response ID, and request correlation; never silently substitute local analysis.
- [ ] Make recall inspection, analysis, named approval, quarantine, replay, audit, and authorized demo reset work entirely online with synthetic data.
- [ ] Bind approval to a verified pharmacist/compliance identity and the exact batch-scoped action. Enforce authorization server-side; retain read-only tools on the hosted agent.
- [ ] Replace shared in-memory mutation state with durable, isolated demo-session state, atomic approval consumption, replay protection, and concurrency controls. Do not expose the current unauthenticated mutation endpoints online.
- [ ] Show truthful runtime and tool evidence, including loading, denied, empty, timeout, partial-failure, disconnected, and replay states. Do not fabricate specialist traces.
- [ ] Resolve the hosted empty-response failures and invalid judge output without lowering grading criteria. Latest new-project baseline (2026-09-14, agent version 1): 3 passed / 4 failed / 0 reported platform errors across 7 cases; all four failed responses were empty and one judge result was nonnumeric.
- [ ] Rerun all seven unchanged golden cases and inspect per-item responses, evaluator thresholds, and correlated traces before claiming evaluation success.
- [ ] Validate authenticated desktop/mobile browser journeys against the deployed URL, including an actual live-agent response, denied anonymous access, denied unauthorized mutations, cross-session isolation, approval, quarantine, replay, and reset.
- [ ] Record the deployed website URL, immutable agent version, deployment/rollback steps, evaluation evidence, and a complete online rehearsal in the README and runbook.
- [ ] Publish repository changes through a reviewed PR in the private `leestott/mcp-connect` repository; exclude credentials, local environments, and private generated evidence.

## Status and gates

| Gate | Exit condition | Status |
|---|---|---|
| G0 - Contract | Scenario, architecture, standards, and acceptance criteria are documented | Complete |
| G1 - Deterministic core | Domain safety tests pass in `.venv` | Complete |
| G2 - MCP boundary | MCP v2 discovery, calls, schemas, errors, and stdio tests pass | Complete |
| G3 - Agent workflow | Four least-privilege agents pass a local recall smoke test through Model Router configuration | Complete |
| G4 - Demo UI | Complete approval flow passes Playwright desktop/mobile checks | Complete |
| G5 - Cloud | Foundry project, Model Router, Hosted Agent, traces, and evaluation are verified live | Complete (quality follow-up open) |
| G6 - Session ready | Deck, runbook, fallback, and 25-minute rehearsal pass | In progress |
| G7 - Complete online demo | Authenticated website runs the full scenario against the live agent with durable controls and verified end-to-end evidence | Not implemented |

## Execution order

1. Finish and freeze the deterministic MCP contract.
2. Resolve the MCP v2/Foundry hosting integration boundary.
3. Replace the generated sample with the Caldova agent workflow.
4. Build the API and operational UI against the same domain/MCP contracts.
5. Add observability, security, developer tooling, and CI checks.
6. Validate locally, then provision and deploy Azure resources.
7. Evaluate the deployed workflow and finish presentation assets.

## Demo 1 - Local MCP and orchestration

- [x] Script the six-minute local walkthrough in the facilitator runbook.
- [x] Show MCP `2026-07-28` tool discovery, schemas, outputs, and annotations.
- [x] Show the local deterministic stage timeline; the separate hosted workflow uses sequential specialists and supervisor synthesis, not routing.
- [ ] Demonstrate one sanitized, recoverable failure before the successful path.
- [x] Demonstrate rejection without approval, named approval, quarantine, and idempotent replay.
- [x] Show correlated local traces and sanitized audit events.
- [x] Verify Demo 1 runs entirely from `.venv` without Azure connectivity.
- [x] Capture a fallback recording or screenshot sequence for Demo 1.

## Demo 2 - Foundry production operations

- [x] Script the five-minute hosted walkthrough in the facilitator runbook.
- [x] Show `azure.yaml`, deployment version, and live Hosted Agent status.
- [x] Invoke the deployed recall workflow and show hosted MCP tool activity.
- [x] Show `caldova-model-router` plus the underlying routed model where available.
- [x] Show runtime managed identity and data-plane RBAC scope.
- [x] Contrast deployment control-plane permissions with runtime permissions.
- [x] Show a correlated Application Insights trace without sensitive values.
- [ ] Show CI validation, environment promotion, rollback, and evaluation evidence.
- [ ] Capture a fallback recording or screenshot sequence for Demo 2.

## 1. Scenario and documentation

- [x] Define the fictional Caldova pharmaceutical recall scenario for batch `B-2408-AX7`.
- [x] Implement the deterministic recall domain with approval-gated, idempotent quarantine.
- [x] Add focused domain tests for authorization and replay safety.
- [x] Rewrite the README around the Caldova solution, demo story, architecture, and current status.
- [x] Create the normative implementation and session specification.
- [ ] Add a security architecture document covering MCP trust boundaries and production controls.
- [ ] Add a control-plane versus data-plane RBAC matrix with least-privilege roles and scopes.
- [x] Add a timed facilitator runbook for the 25-minute session.

## 2. MCP 2026-07-28 server

- [x] Create and use the project-local `.venv` for MCP v2 development and tests.
- [x] Resolve the published dependency conflict with an owned client adapter and isolated MCP v2 runtime.
- [x] Implement the server with `MCPServer` from MCP Python SDK v2.
- [x] Expose typed recall, inventory, supplier, approval, quarantine, audit, and reset tools.
- [x] Mark each tool with accurate read-only, destructive, idempotent, and open-world annotations.
- [x] Keep mutation authorization in deterministic domain code, not model instructions.
- [x] Add in-memory protocol tests with `Client(server)` and assert protocol `2026-07-28`.
- [x] Verify strict input schemas, structured outputs, sanitized errors, and mutation replay behavior.
- [x] Verify direct stdio operation without non-protocol output on stdout.
- [x] Verify approval credentials never appear in audit output, tool text, logs, or traces.
- [x] Record the validated MCP v2 integration path in the architecture documentation.

## 3. Microsoft Foundry Hosted Agent workflow

- [x] Configure `caldova-model-router` (`model-router` `2025-11-18`, Global Standard) as the azd-managed model deployment.
- [x] Provision Model Router and verify that every agent invocation uses its deployment name.
- [x] Replace the writer/legal/formatter sample with Caldova specialist agents.
- [x] Implement Recall Triage, Inventory Impact, Supplier/Compliance, and Supervisor roles.
- [x] Give each agent only the MCP tools required for its role.
- [x] Preserve explicit human approval before stock quarantine.
- [x] Configure trace correlation across Agent Framework and MCP OpenTelemetry spans.
- [x] Add local workflow construction, policy, bridge, and representative recall adapter tests.
- [ ] Add failure handling for unavailable model, unavailable MCP process, tool timeout, and partial specialist output.
- [x] Verify no agent receives approval or quarantine tools and the bridge rejects mutation tools.

## 4. Demo application

- [x] Build the Caldova Recall Control Tower API and operational dashboard.
- [x] Show incident details, affected locations, stock totals, and agent activity.
- [x] Show MCP tool calls and the audit trail without exposing approval credentials.
- [x] Add an explicit pharmacist/compliance approval interaction.
- [x] Show quarantine success, idempotent replay, errors, and demo reset states.
- [x] Show local versus Microsoft Foundry runtime status.
- [x] Validate desktop and mobile layouts with Playwright screenshots and overlap checks.
- [x] Start the local demo server and record its URL in the README.
- [ ] Add loading, empty, denied, partial-failure, disconnected, and replay states.
- [x] Clearly label all scenario data as fictional and synthetic.

## 5. Developer experience and quality

- [x] Update and pin public dependencies, including isolated MCP v2 and Foundry debugging dependencies.
- [x] Add VS Code launch and task configurations.
- [x] Customize `.env.example`, Dockerfile, and agent metadata for this solution.
- [x] Run the complete unit, protocol, API, and workflow test suite.
- [x] Run focused syntax/type/lint checks available in the environment.
- [ ] Add correlated local logging without secrets or approval credentials.
- [ ] Add troubleshooting steps for auth, protocol mismatch, tool failure, routing, and deployment.

## 6. DevOps, GitOps, and governance

- [x] Add CI checks for unit, MCP protocol, API, workflow, schema, and presentation builds. (`.github/workflows/ci.yml`)
- [x] Add dependency and secret scanning. (CI `pip-audit` on requirements + secret-pattern scan)
- [x] Keep instructions, schemas, infrastructure, and evaluation data reviewable in source control.
- [ ] Document dev/prod azd environment separation and promotion.
- [x] Configure workload identity federation for CI/CD; do not store client secrets. (CI `deploy` job uses GitHub OIDC federated login)
- [x] Validate infrastructure before deployment (azd provision --preview / what-if, Bicep compile).
- [ ] Record immutable Hosted Agent version and rollback metadata after deployment.

## 7. Presentation assets

- [x] Create the PowerPoint decks with speaker notes (three Microsoft-branded decks: Demo 1 MCP/multi-agent, Demo 2 Foundry, Teams deployment).
- [x] Keep presentation content to about 12 minutes and live demos to about 9 minutes.
- [x] Reserve about 4 minutes for opening, transitions, questions, and close.
- [x] Include architecture, MCP design, multi-agent pattern, security, observability, and production lessons.
- [x] Validate the generated `.pptx` and rehearse the hard-stop timing.
- [ ] Prepare a local fallback recording or screenshot sequence for both demos.
- [x] Verify the deck explicitly teaches orchestration, governance, scale, RBAC planes, debugging, and GitOps.
- [x] Build a Microsoft Teams deployment deck (`caldova-teams-deployment.pptx`) with a deploy-in-Teams demo scenario.

## 8. Azure provisioning and deployment

- [x] Verify the deploying identity, tenant, subscription, and required roles (configured per environment via `scripts/setup_azd_env.py`; never committed).
- [x] Select `northcentralus` and confirm suitable model availability.
- [x] Validate the final root and application `azure.yaml` manifests and compile the infrastructure inputs.
- [x] Create/select `caldova-recall-demo` and set `AZURE_AI_MODEL_DEPLOYMENT_NAME=caldova-model-router`.
- [x] Complete pre-deployment validation, including a local Docker build when Docker Desktop is available.
- [x] Provision the new Microsoft Foundry project and supporting resources.
- [x] Deploy the Hosted Agent workflow.
- [x] Invoke the deployed agent with the Caldova recall scenario.
- [x] Confirm logs, traces, resource names, endpoint, and deployment status.
- [x] Confirm telemetry reports the underlying model selected by Model Router for representative agent steps.
- [x] Add a small evaluation dataset (`tests/golden.jsonl`) for the Foundry evaluation smoke test.
- [x] Deploy `caldova-evaluator` (`gpt-5.4-mini` `2026-03-17`, Global Standard) and run the Foundry evaluation suite against `tests/golden.jsonl` (baseline: 1 passed, 6 failed, 0 errored; six partial prompts returned empty responses).
- [x] Isolate concurrent Hosted Agent workflow runs and rerun the same seven-case smoke suite against version 4 (4 passed, 3 failed, 0 errored; all seven responses were substantive).
- [ ] Make focused answers concise and configure a judge that receives the dataset ground truth, then rerun the same suite.
- [ ] Compare Model Router quality, latency, routed-model distribution, and estimated cost on representative prompts.

## 9. Post-rename (Caldova) validation and redeploy

- [x] Rename Cordova to Caldova across code, docs, presentation, filenames, and the project folder.
- [x] Validate the solution after the rename (tests pass, both decks build, no `cordova` residue).
- [x] Recreate the `caldova-recall-demo` azd environment after the previous (wrong-name) deployment was deleted.
- [x] Provision the Microsoft Foundry project and supporting resources under the Caldova names.
- [x] Redeploy the Hosted Agent to Microsoft Foundry.
- [x] Confirm the deployed application/agent endpoint URL and record it.
- [x] Validate all content and resources for public sharing (no secrets, accurate READMEs).

## Definition of done

- [ ] The complete demo works online from an authenticated HTTPS website, including live-agent analysis and safe approval/quarantine/replay/reset; no local runtime is required.
- [ ] A presenter can run the complete scenario locally without cloud dependency.
- [x] The same workflow is deployed and successfully invoked as a Microsoft Foundry Hosted Agent.
- [x] The MCP implementation negotiates `2026-07-28` and passes protocol/security tests.
- [ ] The UI and PowerPoint support a rehearsed 25-minute presentation and demo.
- [x] Control-plane deployment identity and data-plane runtime identity are documented and independently verified.
- [x] CI validates the same contracts used by the local and Hosted Agent paths.

## 10. Optional follow-ups (completed)

- [x] Add a CI pipeline (`.github/workflows/ci.yml`): tests, deck build, brand-residue check, manifest check.
- [x] Add a reproducible CI/test dependency set (`requirements-test.txt`).
- [x] Configure the CI deploy job to use GitHub OIDC workload identity federation (no client secret).
- [x] Confirm routed-model telemetry in Application Insights (`caldova-model-router` -> `model-router-2025-11-18`, correlated with agent, tools, and prompts).
- [x] Validate both decks are rehearsal-ready (11 slides each, presenter notes, one live-demo slide).
- [x] Add a golden evaluation dataset (`tests/golden.jsonl`).
- [x] Fix and document the local Control Tower run command (working-directory error).
- [x] Run the full Foundry evaluation suite with `caldova-evaluator` (`gpt-5.4-mini`) against `tests/golden.jsonl`; retain run IDs and per-item output evidence under `.foundry/results/`.

## 11. Microsoft Teams enterprise deployment handover (IT / Teams administrator)

> Handover checklist to publish the Caldova Recall Control Tower to an enterprise Microsoft 365 / Teams tenant as a **Teams personal/team tab** backed by the Microsoft Foundry Hosted Agent. Complete phases A–H in order. Roles referenced: **Global Administrator**, **Teams Service Administrator**, **Cloud Application Administrator**, **Azure subscription Owner/Contributor**.

### A. Scope, licensing, and prerequisites
- [ ] Confirm the target tenant ID, primary domain, and the named admins for each role above.
- [ ] Confirm licensing: Microsoft Teams, and Microsoft Entra ID P1/P2 (for Conditional Access and access reviews).
- [ ] In **Teams admin center → Teams apps → Manage apps → Org-wide app settings**, confirm **Custom apps** upload/publish is permitted (or plan to enable for the pilot).
- [ ] Identify the target rollout audience as an Entra security group (pilot group + production group).
- [ ] Data classification sign-off: the demo ships **synthetic data only**; confirm no regulated/PII data before production exposure.
- [ ] Nominate an application owner, support/escalation contact, and change-approver.

### B. Identity and single sign-on (Microsoft Entra ID)
- [ ] Register a **single-tenant** Entra application for the web app (Cloud Application Administrator).
- [ ] Set the **Application ID URI** to `api://<hosted-domain>/<app-client-id>` and expose an `access_as_user` delegated scope.
- [ ] Pre-authorize the Microsoft Teams client application IDs for the exposed scope (Teams desktop/web/mobile well-known client IDs) to enable Teams SSO.
- [ ] Add redirect URIs for the hosted web app and grant **admin consent** for delegated Microsoft Graph `User.Read`.
- [ ] Enable **user assignment required** on the enterprise application and assign the target security group.
- [ ] Apply Conditional Access (MFA, compliant device) to the enterprise application per corporate policy.

### C. Host the application securely (data plane)
- [ ] Deploy the Control Tower web app to an approved host (**Azure App Service** or **Azure Container Apps**) over HTTPS with a custom domain and managed TLS certificate.
- [ ] Enforce **Entra authentication** at the host (App Service Authentication / Easy Auth) bound to the Entra app; deny anonymous access.
- [ ] **Add authorization to mutation endpoints** (approval/quarantine/reset) with Entra role/group checks — the demo binds to `127.0.0.1` and has no auth and must not be exposed org-wide without this control.
- [ ] Apply network controls (private endpoints / IP allow-list / WAF) per enterprise policy.
- [ ] Connect the hosted web app and the Foundry Hosted Agent to enterprise **Application Insights / Log Analytics**; confirm no secrets in logs.
- [ ] Record the control-plane (deployment) vs data-plane (agent managed identity) RBAC scopes for the change record.

### D. Build the Teams app package
- [ ] Author `manifest.json` (Teams schema 1.17+): new app GUID, developer info, name, short/long description, privacy and terms URLs.
- [ ] Add app icons: **color 192×192** and **outline 32×32** PNGs.
- [ ] Define a **static tab** (personal scope) and/or **configurable tab** (team/group chat scope) whose content URL is the hosted web app.
- [ ] Add `webApplicationInfo` with the Entra **app (client) ID** and **resource** (Application ID URI) to enable Teams SSO.
- [ ] Populate `validDomains` with the hosted domain(s); declare any `devicePermissions`.
- [ ] Zip `manifest.json` + both icons into the app package `.zip`.
- [ ] Validate the package in **Teams Developer Portal** (or Teams Toolkit) against the store validation checklist.

### E. Publish and target (Teams admin center)
- [ ] Upload the custom app: **Teams admin center → Teams apps → Manage apps → Upload new app** (or publish to org via Developer Portal).
- [ ] Review the app's **Permissions** and **Data handling**; set status to **Allowed**.
- [ ] Create/assign an **App permission policy** allowing the app for the target group.
- [ ] Create/assign an **App setup policy** to pin (and optionally pre-install) the app for the target group; assign via **group policy assignment**.
- [ ] Confirm availability scoping: targeted security group first, tenant-wide only after sign-off.

### F. Security, compliance, and governance
- [ ] Apply **Microsoft Purview** sensitivity labels, retention, and enable **audit logging** for app activity.
- [ ] Confirm Conditional Access, device compliance, and session controls apply to the app.
- [ ] Document data flow: Teams client → hosted web app (Entra SSO) → Foundry Hosted Agent → Model Router → deterministic MCP policy store.
- [ ] Confirm data residency (North Central US) meets policy; record cross-border considerations.
- [ ] Verify the app package and runtime carry **no secrets**; all auth uses Entra tokens/managed identity.
- [ ] Schedule **Entra access reviews** for the app's assigned group.

### G. Pilot, validate, and roll out
- [ ] Pilot to the small group; validate SSO, tab load, agent invocation, approval → quarantine → replay, and audit trail in Teams **desktop, web, and mobile**.
- [ ] Capture UAT evidence and obtain business sign-off.
- [ ] Stage rollout to the production group via the setup policy.
- [ ] Monitor **Teams admin center → Analytics & reports → Usage reports (Apps)** and Application Insights for adoption and errors.

### H. Operations, lifecycle, and rollback
- [ ] Define versioning: bump `manifest.json` version per update and re-upload to the catalog.
- [ ] Rollback plan: set app status to **Blocked** and/or remove the setup-policy assignment; revert to the prior package version.
- [ ] Decommission: remove the app from the catalog, delete the Entra app registration, run `azd down` on the Foundry environment, and revoke admin consents.
- [ ] Confirm SLA, patch cadence, owner, and support contact are recorded in the IT service catalog.
