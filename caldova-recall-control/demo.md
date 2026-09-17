# Caldova Demonstration Guide

This guide runs the five demonstrations used by the story-led presentation. All recall data is fictional and synthetic.

## Live site

[Caldova Recall Control Tower](https://caldova-web-ti3pdz737nyvg.azurewebsites.net/)

The hosted site requires Microsoft Entra authentication. Use only an account authorised for this demo. Keep credentials, tokens, identity claims, approval handles, and private trace data off-screen.

## Before the session

1. Open the live site and complete sign-in before presenting.
2. Confirm the page identifies the runtime as `HOSTED` and the analysis source as `FOUNDRY HOSTED AGENT`.
3. Confirm the signed-in identity shown by the application is the intended presenter account and is authorised to approve.
4. Reset only your own synthetic scenario. Do not reset after Demo 2; Demos 4 and 5 reuse that assessment and session.
5. Keep the live site open in one browser tab and the relevant Foundry deployment, version, identity, and trace evidence in separate prepared tabs.
6. Open PowerShell at the repository root and activate the existing project environment:

   ```powershell
   Set-Location (git rev-parse --show-toplevel)
   .\caldova-recall-control\.venv\Scripts\Activate.ps1
   ```

7. Run the MCP inspection once before the session and leave its output available:

   ```powershell
   python .\caldova-recall-control\scripts\inspect_mcp.py
   ```

8. Open the story deck in Presenter View. Its architecture slide precedes Demo 1, and the five divider slides are labelled `DEMO 01` through `DEMO 05`.

The terminal inspector launches an independent MCP stdio server with isolated synthetic fixtures. It does not read or change the live website session.

## Demo 1: Find the stock

**Surface:** Prepared PowerShell terminal  
**Target window:** 3:00-5:00  
**Purpose:** Show MCP connection, discovery, schema inspection, and a structured read without a model.

### Run

From the repository root:

```powershell
python .\caldova-recall-control\scripts\inspect_mcp.py
```

The script runs all seven checks without pausing. For this demo, focus on output sections 1-4 and leave sections 5-7 visible for Demo 3.

### Show

1. `CONNECT`: point out the negotiated MCP protocol version.
2. `DISCOVER`: show the tools returned by `tools/list`.
3. `CONTRACT`: inspect the `locate_inventory` input schema, generic output schema, and annotations.
4. Explain that annotations such as `readOnlyHint` describe intent but do not grant permission.
5. `CALL`: show the exact argument `{"batch_id": "B-2408-AX7"}`.
6. `structuredContent`: verify `total_units` is `2196`, `locations` is `4`, and inspect the four inventory positions.

### Explain

- No model produced the inventory rows.
- MCP standardises discovery and tool calls; domain code still owns inventory facts and policy.
- Seven tools may be discoverable, while hosted agents receive only the explicitly allow-listed read tools.
- A structured response is easier to check, but the current generic object schema does not itself prove the inventory invariants.

### Success check

Do not call the demo successful until the observed result reports 2,196 units across four locations and the call has no MCP error.

### Fallback

Show the `locate_inventory` handler and fixture assertions as **source evidence**. State that this is expected behaviour, not a live passing invocation.

## Demo 2: Produce the decision brief

**Surface:** [Caldova Recall Control Tower](https://caldova-web-ti3pdz737nyvg.azurewebsites.net/)  
**Target window:** 6:30-9:00  
**Purpose:** Run the Foundry-hosted, read-only agent workflow and inspect its retained response evidence.

### Run

1. Return to the authenticated live site.
2. Confirm `HOSTED` and `FOUNDRY HOSTED AGENT` are visible.
3. Confirm the scenario is at its initial assessment state and has not already been quarantined.
4. Select **Run analysis** once.
5. Wait for the request to complete. Do not repeatedly submit while an analysis is active.
6. Keep the resulting response ID and request correlation visible.

### Show

1. Triage establishes batch `B-2408-AX7`.
2. Inventory evidence reports 2,196 units and four locations.
3. Supplier/compliance evidence preserves constraints and uncertainty.
4. The supervisor produces a decision brief without receiving mutation tools.
5. Where prepared and authorised, correlate the response with the deployed agent version and matching trace.

### Explain

- The implemented workflow is a fixed sequential collaboration, not dynamic supervisor routing.
- The final response is advice, not authority.
- The hosted agent has read-only tools and cannot approve or quarantine stock.
- A configured Model Router label is not evidence of which underlying model handled a particular step.

### Success check

The final assistant response must be nonempty, retain the 2,196-unit/four-location facts, preserve supplier uncertainty, require human action, and expose genuine response/request correlation.

### Fallback

After 30 seconds without useful output, use genuine saved evidence that includes its date and immutable agent version. Otherwise walk through `build_agents` and `build_workflow` as **source evidence**. Do not describe either fallback as a successful live invocation.

## Demo 3: Investigate a failure

**Surface:** The terminal output retained from Demo 1  
**Target window:** 9:00-13:00  
**Purpose:** Distinguish input validation from authorisation failure and verify that denied work did not mutate state.

### Run

Use sections 5-7 from the existing `inspect_mcp.py` output. If the output is unavailable, rerun:

```powershell
python .\caldova-recall-control\scripts\inspect_mcp.py
```

State clearly that a rerun starts a new isolated server and does not continue the previous process state.

### Show

1. `VALIDATION`: the malformed batch value `bad batch!` is rejected with `isError: true`.
2. Contrast it with the valid read from Demo 1. The repair belongs in the tool argument, not in a stronger prompt.
3. `POLICY`: a schema-valid quarantine call using an invalid approval credential is denied with `isError: true`.
4. `VERIFY`: the follow-up inventory read reports `inventory_unchanged: true` and `model_calls: 0`.

### Explain

- Schema validity and business authority are separate checks.
- MCP `isError`, an HTTP status from the website, and an SDK exception belong to different failure layers.
- A retry with the same invalid approval must not become authorised.
- Start diagnosis at the first divergence: tool input, tool result, workflow handoff, then synthesis.

### Success check

Both invalid calls must fail, and the post-denial inventory must exactly equal the earlier valid inventory result.

### Fallback

Use the script and test assertions labelled **expected behaviour, not a live pass**. Never expose a real approval token while explaining the denial path.

## Demo 4: Give authority to the person

**Surface:** The same authenticated live-site tab used in Demo 2  
**Target window:** 13:00-16:00  
**Purpose:** Move from a model recommendation to an authenticated, application-controlled action.

### Run

1. Return to the existing live-site tab without resetting or starting another assessment.
2. Verify that the decision brief and its response ID still match Demo 2.
3. Confirm inventory remains available and the application shows the authenticated approver identity.
4. Select **Approve quarantine**.
5. Review the approval dialog and submit the action once. Submission approves and quarantines; there is no separate second action.
6. Keep credentials and identity claims off-screen.

### Show

1. The model-facing tools remain read-only.
2. The application checks the signed-in caller and binds approval to the actor, batch, action, session generation, and expiry.
3. Under **Quarantine evidence**, inspect **First authorised call**.
4. Verify four positions changed and 2,196 units were processed.
5. Inspect the audit entry without revealing any reusable approval credential.

### Explain

- A disabled button is not the security boundary; server-side application policy is.
- The presenter identity is real and authenticated. Asha Rao and the recall are fictional scenario elements.
- The terminal denial in Demo 3 proves its isolated MCP policy path, not the deployed EasyAuth boundary.

### Success check

The action is successful only when the observed first authorised result reports four changed positions and 2,196 processed units, with a matching audit record.

### Fallback

Use a saved view only as an illustration and label the expected transition explicitly. Do not claim that the current operation passed. If the assessment failed, do not attempt approval.

## Demo 5: Prove the outcome

**Surface:** The unchanged authenticated live-site tab from Demo 4  
**Target window:** 16:00-17:00  
**Purpose:** Prove idempotent replay through business state and audit evidence.

### Run

1. Continue only after Demo 4 has a successful first authorised operation.
2. Select **Replay quarantine** once.
3. Compare **First authorised call** with **Latest replay** under **Quarantine evidence**.
4. Refresh the page and verify the same brief, response ID, and replay evidence remain visible.
5. Inspect the corresponding audit records.

### Show

1. The first call changed four positions.
2. The replay changed zero additional positions.
3. Both results may report 2,196 processed units because that value describes the batch, not new mutations.
4. No reusable approval token appears in the UI or audit output.

### Explain

- A finished badge is not proof; compare the actual state transition and replay effect.
- Actor-scoped Blob state retains the hosted session evidence and uses conditional updates.
- This demonstrates replay and refresh for this hosted session. It does not prove every restart, regional failure, or cross-replica failure mode.

### Success check

The latest replay must report zero additional changed positions while preserving the first-operation evidence and audit history.

### Fallback

If Demo 4 failed, do not present replay as proof. Use the slide's expected first-call and replay values as acceptance criteria, clearly labelled as expected rather than observed.

## After the demonstrations

1. Do not reset until audience questions and evidence inspection are complete.
2. Record the observed agent version, response ID, request ID, first-operation result, replay result, and any failure or fallback used.
3. Do not record credentials, tokens, approval handles, raw identity claims, or sensitive trace content.
4. Finish the demonstrations by 17:00 in the presentation schedule. Stop an incomplete demo at its hard limit and use the documented fallback.

## Local browser fallback

The local Control Tower is deterministic and does not invoke the hosted model. Use it only when the live-site demonstration is unavailable, and label it `LOCAL / NO MODEL`.

From the repository root:

```powershell
python -m uvicorn control_tower_api:app --app-dir .\caldova-recall-control\src --host 127.0.0.1 --port 8091
```

Open `http://127.0.0.1:8091`. Local named approval is demonstration input, not verified Microsoft Entra identity.

## Related presenter material

- [Story stage script](presentation/mcp-community-connect-bengaluru-story-stage-script.md)
- [Presenter runbook](presentation/RUNBOOK.md)
- [Story deck builder](presentation/build_story_deck.py)
- [MCP inspection script](scripts/inspect_mcp.py)
- [Security guidance](../SECURITY.md)
