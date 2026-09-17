# Caldova 25-Minute Presenter Runbook

## Story-led edition

For the problem -> decision -> demonstration -> evidence -> lesson presentation, use
[the final deck](mcp-community-connect-bengaluru-final.pptx) and its
[stage script](mcp-community-connect-bengaluru-story-stage-script.md).
It has 18 main slides, six hidden appendices, and a hidden Demo Index (slide 25), with Asha's synthetic recall decision
as the narrative. The script is also embedded in PowerPoint Presenter View.
Visible slide 4 is the application architecture diagram, immediately before `DEMO 01` on slide 5.
The timed sequence includes this architecture introduction before the first demonstration
and five full-slide breaks labelled DEMO for deliberate terminal and browser handoffs.

Budget 22 minutes including demonstrations and three minutes for actual audience questions.
The script contains the new timing checkpoints, observations to verify, and honest fallbacks;
the original-edition schedule below does not apply to the story deck. Live timing remains
to be rehearsed. Supervisor routing and parallelism are comparisons, not live implementations.

Build from the repository root without overwriting the original edition:

```powershell
.\caldova-recall-control\.venv\Scripts\python.exe .\caldova-recall-control\presentation\build_story_deck.py
```

### Demo navigation and rehearsal

Use the story edition for the current event rehearsal. Main slides 2-18 link to the hidden
Demo Index; its five entries return to the labelled demo break slides. Demo breaks 1 and 3
cue a manual switch to the prepared MCP terminal; breaks 2, 4 and 5 cue the authenticated
hosted Control Tower. There are no executable links or unverified hosted URLs in the deck.

- Close the final deck in PowerPoint before rebuilding it, then reopen it in Presenter View.
- Rehearse the terminal inspection once; keep its valid read and failure output available.
- Use a dedicated local demo instance and reset only your own synthetic scenario before presenting.
- Confirm the local header says LOCAL / NO MODEL and the approval field identifies a demo name.
- On slide 8, inspect the first recorded quarantine result. On slide 9, replay and compare
	First authorised call with Latest replay in Quarantine evidence. Values come from the
	current batch's audit records, not expected counts. Not recorded means evidence is absent.
- Keep hosted execution separate. Prepare authorised access and genuine dated/versioned
	evidence, or use the stage script's labelled source fallback after 30 seconds without useful output.
- Rehearse the actual window switches: stock by 5:00, hosted brief by 9:00, failure lab by
	13:00, approval by 16:00, replay by 17:00, and questions from 22:00 to 25:00.

## Original speaker edition (reference)

The original [mcp-community-connect-bengaluru-speaker.pptx](mcp-community-connect-bengaluru-speaker.pptx)
was prepared for **From Prototype to Production: Engineering Agent Systems with MCP,
Multi-Agent Patterns and Real Work**, 11:00-11:25 IST on 26 September 2026.
It contains 14 main slides and four hidden appendices: clickable sources, MCP roles and
primitives, server/client code, and failure handling. Extensive Presenter View notes are
also available in [the speaker-notes companion](mcp-community-connect-bengaluru-speaker-notes.md).
Use the timed SAY sections live; the engineering detail is preparation and Q&A material,
not a script to read verbatim in 25 minutes.

The event deck combines the local MCP demo with a short hosted verification sequence.
It uses the event artwork and community branding, keeps platform-independent lessons
in the foreground, and identifies Microsoft Foundry as the hosting example.

The implemented agent pattern is sequential specialization followed by supervisor synthesis.
Dynamic routing and parallel execution are comparisons, not live features. Describe the
session abstract's routing promise accordingly.

[build_deck.py](build_deck.py) and [build_teams_deck.py](build_teams_deck.py) retain
older technical and Teams material. Their generated drafts are ignored. Recheck fixed
version, timing, test-count, architecture, and deployment claims before showing them.

Rebuild the event deck from the workspace root:

```powershell
.\caldova-recall-control\.venv\Scripts\python.exe .\caldova-recall-control\presentation\build_event_deck.py
```

## Developer and AI engineer learning goals

The operational scenario supplies consequences; the protocol inspection supplies MCP
evidence. Do not let the dashboard become the only demonstration. The audience should
leave able to reproduce a tool call without a model and explain what each boundary owns.

| What attendees learn | Where they see it | What it does not prove |
|---|---|---|
| Host, client, server and transport roles | Architecture; appendix 16 | MCP is not an agent router |
| Discovery and schema inspection | Slide 4; terminal sections 1-3 | Discovered tools are not automatically authorized |
| Typed input and structured results | Terminal inventory call; appendix 17 | A generic output object does not enforce inventory facts |
| Validation versus authorization | Terminal malformed input and denied write | A typed approver name is not authenticated identity |
| MCP versus application errors | MCP `isError`; optional FastAPI HTTP 403 | HTTP 403 is not an MCP JSON-RPC error |
| Tool quality versus model quality | Local evidence, then separate hosted brief | A passing tool call does not guarantee a grounded answer |

The server exposes tools, not MCP resources or prompts. Those primitives are explained
as possible extensions. The hosted application registers explicit wrappers; it does not
dynamically register every tool discovered from the server.

## Before the session

This checklist and the schedule below belong to the original speaker edition. For the
current story deck, use Demo navigation and rehearsal above and the story stage script.

- Open the speaker edition in PowerPoint and enable Presenter View.
- Start the Control Tower on `http://127.0.0.1:8091` and reset the scenario.
- Keep a terminal open in the project root for the local tests.
- Run [inspect_mcp.py](../scripts/inspect_mcp.py) once and rehearse the seven numbered output sections. It starts its own stdio server with independent synthetic state and needs no model or cloud connection.
- Open the deployed Foundry Agent, its latest successful trace, and deployment identity in separate tabs.
- Confirm Demo 2 with a fresh invocation before presenting. If it is unavailable, use the fallback below and describe it as the intended production path, not live evidence.

## Hard schedule

| Time | Slide | Presenter action | Proof point |
|---|---:|---|---|
| 0:00-0:45 | 1 | Introduce the engineering question. | MCP patterns transfer across hosts. |
| 0:45-1:30 | 2 | Establish batch, count, locations and approval. | Testable invariants. |
| 1:30-3:00 | 3 | Explain the two execution paths. | No UI-to-hosted integration. |
| 3:00-4:00 | 4 | Inspect a concrete MCP tool contract. | Protocol versus policy. |
| 4:00-5:15 | 5 | Compare sequential, routing, and parallel patterns. | Only sequential is implemented. |
| 5:15-6:00 | 6 | Show the fixed four-agent graph. | Supervisor synthesis, not routing. |
| 6:00-11:00 | 7 | Inspect MCP in the terminal, then use the browser. | Discovery, schemas, calls, errors, policy, replay. |
| 11:00-11:30 | 8 | Summarize live evidence or label the saved screenshot. | First mutation vs replay. |
| 11:30-13:00 | 9 | Explain debugging and the schematic trace. | Diagram, not captured telemetry. |
| 13:00-17:00 | 10 | Run the prepared hosted verification. | Version, identity, result and actual trace. |
| 17:00-18:30 | 11 | Explain identity and state limitations. | Hosting does not prove readiness. |
| 18:30-19:30 | 12 | Discuss MCP Live-inspired design questions. | Extensions are not implemented features. |
| 19:30-20:30 | 13 | Cover implementation lessons and release checks. | Evidence before readiness claims. |
| 20:30-22:00 | 14 | Deliver the closing principle. | Engineering makes capability accountable. |
| 22:00-25:00 | 14 | Questions; keep the Control Tower ready. | Revisit denial or replay on request. |

At 20:30, stop any unfinished demo and move to slide 14. Protect the close and
question time. Slides 15-18 are hidden references and technical deep dives, not part of the timed talk.

## MCP Live additions and attribution

Slide 12 draws topics from the published chapter list of
[MCP Live!](https://www.youtube.com/watch?v=uydwDk91Y9Y), accessed 14 September 2026:

- [1:20:23 - Toolboxes in Microsoft Foundry](https://www.youtube.com/watch?v=uydwDk91Y9Y&t=4823s), Viswajeeet Balaji: a question about curating tool access.
- [2:32:29 - Evolution of MCP auth](https://www.youtube.com/watch?v=uydwDk91Y9Y&t=9149s), Den Delimarsky: a question about remote caller identity and authority.
- [3:21:05 - Building MCP Apps](https://www.youtube.com/watch?v=uydwDk91Y9Y&t=12065s), Jeremiah Lowin: a possible interactive evidence-review surface.
- [3:45:08 - Event-driven agents](https://www.youtube.com/watch?v=uydwDk91Y9Y&t=13508s), Clare Liguori: a possible recall-arrival trigger for analysis, not approval.

These are original design questions inspired by the published agenda, not speaker
quotes or a full-transcript summary. Toolboxes, MCP Apps and event-driven integration
have not been added to this demo. A Teams tab is not an MCP App. The source links
are clickable in the appendix and included in speaker notes.

## Demo 1: local control path

**6:00-7:15: Make MCP visible.** Run the command below. Show the negotiated version,
`tools/list`, the inventory input constraints, and its generic object `outputSchema`.
Point to the call arguments and actual `structuredContent`: four positions, 2,196 units.
The script then rejects malformed input and a schema-valid invalid approval credential,
and reads inventory again to verify it is unchanged. It creates no usable approval token.

```powershell
./caldova-recall-control/.venv/Scripts/python.exe caldova-recall-control/scripts/inspect_mcp.py
```

Ask: "If the credential passes the schema, must the action succeed?" Explain why policy
still rejects it. Ask: "Does `readOnlyHint` enforce permissions?" No; it is metadata.
The terminal uses real MCP stdio. The hosted bridge instead uses custom CLI/JSON IPC and
an in-process MCP client inside its child. The local UI also uses in-process MCP.

**7:15-11:00: Demonstrate the separate browser controls.**

1. Reset the Control Tower and point out four locations and 2,196 units. The initial badge may say `ASSESSMENT`.
2. Select **Run analysis**. Explain that Python calls MCP tools and assembles the summary; the stage rail is not live model execution.
3. Point out the narrow MCP calls. Approval and quarantine tools exist in the local application but are not exposed to the separate hosted agents.
4. Optionally send the prepared denial request below. Confirm HTTP 403 and unchanged stock. This is an application gate, not the MCP error just shown. Skip it if the terminal segment ran long.
5. Select **Approve quarantine** and enter `Asha Rao, Responsible Pharmacist` as a synthetic name. Submitting the dialog both approves and quarantines.
6. Confirm four positions and 2,196 units changed.
7. Select **Replay quarantine**. Confirm zero additional positions changed.
8. Show the audit trail. A typed name is not authenticated identity. Audit and replay protection are local, in-memory demonstrations.

Recovery: use [the saved quarantine screenshot](assets/control-tower-quarantined.png) on slide 8 and label it as saved evidence. See [asset attribution](assets/README.md) for artwork and screenshots.

## Demo 2: Foundry production path

Use this prompt in the prepared hosted-agent client:

```text
Assess recall batch B-2408-AX7. Report affected units, location count and inventory
positions, supplier acknowledgement and constraints, and required human action.
Distinguish known facts from uncertainty. Prepare a supervisor decision brief.
Do not claim approval or quarantine occurred.
```

1. Show the deployed Hosted Agent version and managed identity.
2. Invoke batch `B-2408-AX7` with the prepared recall prompt.
3. Show the response contains the same four locations and 2,196-unit total.
4. Open an actual correlated trace where available. Describe only captured fields; do not infer a routed model, latency, or outcome from a schematic.
5. Show the source-controlled deployment version and the narrow runtime role assignment.
6. State explicitly that approval and quarantine remain outside agent tool access. The browser does not call this workflow and their live state is not shared.

Fallback: keep slide 10 visible and label it as the intended verification sequence.
Do not claim a routed model, trace, managed identity, or evaluation result that is
not visible from a successful deployed run. Continue with slides 11 through 13 as
extension ideas and release requirements.

### Four-minute source fallback

Use this only when hosted invocation or tracing is unavailable. Say: "This is a source
walkthrough of the configured agent path, not a successful hosted execution."

1. **First minute:** Open [main.py](../src/agent-framework-workflows-responses/main.py) at `build_agents`. Show the three explicit read-tool lists and tool-free supervisor. Discovery does not automatically expose all server tools to these agents.
2. **Second minute:** Show `build_workflow` in the same file. Trace the three fixed edges. The supervisor summarizes evidence; it does not choose the next agent.
3. **Third minute:** Follow `_call_mcp_read_tool` into [mcp_v2_bridge.py](../src/agent-framework-workflows-responses/mcp_v2_bridge.py). Show `READ_ONLY_TOOLS` and `Client(mcp)`. The outer process exchange is custom CLI/JSON, while MCP runs in process inside the child.
4. **Final minute:** Return to the terminal's inventory result and describe how a future hosted response should preserve those facts. Do not invent a model answer or trace. Move to slide 11's production requirements.

Keep the technical appendices for questions. Do not spend the fallback installing
dependencies, signing in, provisioning resources, or trying a new deployment.

## Rehearsal gates

The generated deck and runnable local checks can be verified automatically; delivery
timing and current cloud evidence require a separate rehearsal. Do not equate extensive
speaker notes with a script that fits the allotted time.

- **Content check:** Attendees should see `tools/list`, actual input constraints, `tools/call`, structured inventory, and an MCP error before the browser approval flow.
- **Local preflight:** Run the MCP inspection and local tests. Confirm denial leaves inventory unchanged and replay changes no additional positions. Use synthetic names only.
- **Display check:** Use Presenter View and a readable terminal font. Rehearse scrolling to the seven numbered sections rather than reading the entire JSON payload.
- **Hosted preflight, still required:** Verify a fresh invocation, current version, and genuine trace in the presentation environment, or choose the source fallback explicitly.
- **Timed rehearsal, still required:** Complete the terminal section in 75 seconds, local demo by 11:00, hosted segment by 17:00, and move to the close at 20:30. Preserve three minutes for questions.
- **Audience check:** Ask who sends the MCP call, whether annotations authorize it, and whether a structured result guarantees a correct agent answer. The expected answers are client, no, and no.

## Prepared commands

From the repository root, after following the [local setup instructions](../README.md):

```powershell
./caldova-recall-control/.venv/Scripts/python.exe -m uvicorn control_tower_api:app --app-dir caldova-recall-control/src --host 127.0.0.1 --port 8091
./caldova-recall-control/.venv/Scripts/python.exe -m pytest caldova-recall-control/tests -q
```

PowerShell 7 denial request, while the local server is running:

```powershell
Invoke-WebRequest http://127.0.0.1:8091/api/quarantine -Method POST -ContentType 'application/json' -Body '{"approval_id":"not-approved"}' -SkipHttpErrorCheck
```

## Final line

The model makes the system capable. Engineering makes it accountable.