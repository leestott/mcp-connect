import asyncio
import json
import os
import sys
from pathlib import Path
from collections.abc import Callable
from contextvars import ContextVar
from typing import Any

from agent_framework import Agent, AgentExecutor, WorkflowAgent, WorkflowBuilder
from agent_framework.foundry import FoundryChatClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

SOURCE_DIR = Path(__file__).resolve().parent
MCP_BRIDGE = SOURCE_DIR / "mcp_v2_bridge.py"


def _bounded_env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, default))
    except ValueError:
        return default
    return min(max(value, minimum), maximum)


MCP_TIMEOUT_SECONDS = _bounded_env_int("CALDOVA_MCP_TIMEOUT_SECONDS", 25, 5, 30)
MCP_MAX_CONCURRENCY = _bounded_env_int("CALDOVA_MCP_MAX_CONCURRENCY", 2, 1, 4)
MCP_CALL_LIMIT = asyncio.Semaphore(MCP_MAX_CONCURRENCY)


class RequestIsolatedWorkflowAgent(WorkflowAgent):
    def __init__(self, workflow_factory: Callable[[], WorkflowAgent]):
        self._workflow_factory = workflow_factory
        template = workflow_factory()
        super().__init__(template.workflow, name=template.name, description=template.description)
        self._request_agent: ContextVar[WorkflowAgent | None] = ContextVar(
            f"caldova_request_agent_{self.id}", default=None
        )

    def run(self, *args: Any, **kwargs: Any):
        agent = self._request_agent.get()
        if agent is None:
            agent = self._workflow_factory()
            self._request_agent.set(agent)
        return agent.run(*args, **kwargs)


async def _call_mcp_read_tool(tool_name: str, batch_id: str) -> dict[str, Any]:
    mcp_python = os.getenv("CALDOVA_MCP_PYTHON", sys.executable)
    async with MCP_CALL_LIMIT:
        try:
            process = await asyncio.create_subprocess_exec(
                mcp_python,
                str(MCP_BRIDGE),
                tool_name,
                json.dumps({"batch_id": batch_id}),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError:
            raise RuntimeError("Caldova recall data is temporarily unavailable") from None
        try:
            stdout, _ = await asyncio.wait_for(
                process.communicate(), timeout=MCP_TIMEOUT_SECONDS
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            raise RuntimeError("Caldova recall data is temporarily unavailable") from None

    if process.returncode != 0:
        raise RuntimeError("Caldova recall data is temporarily unavailable")

    try:
        return json.loads(stdout)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise RuntimeError("Caldova recall data returned an invalid response") from None


async def get_recall_notice(batch_id: str) -> dict[str, Any]:
    """Return validated recall notice details for a Caldova batch."""
    return await _call_mcp_read_tool("get_recall_notice", batch_id)


async def locate_inventory(batch_id: str) -> dict[str, Any]:
    """Return affected inventory positions and totals for a Caldova batch."""
    return await _call_mcp_read_tool("locate_inventory", batch_id)


async def get_supplier_status(batch_id: str) -> dict[str, Any]:
    """Return supplier acknowledgement and replacement status for a Caldova batch."""
    return await _call_mcp_read_tool("get_supplier_status", batch_id)


def build_agents(client: FoundryChatClient) -> tuple[Agent, Agent, Agent, Agent]:
    triage_agent = Agent(
        client=client,
        name="recall_triage",
        instructions=(
            "You are Caldova's Recall Triage specialist. Extract the batch identifier "
            "from the request, call get_recall_notice exactly once, validate whether the "
            "notice exists, and report the product, supplier, risk tier, reason, and next "
            "required analysis. Never infer missing facts or recommend approval."
        ),
        tools=[get_recall_notice],
    )

    inventory_agent = Agent(
        client=client,
        name="inventory_impact",
        instructions=(
            "You are Caldova's Inventory Impact specialist. Use the validated batch from "
            "the preceding triage output, call locate_inventory exactly once, and report "
            "the tool-provided total units, location count, and positions. Flag empty or "
            "inconsistent results. Never approve or mutate inventory."
        ),
        tools=[locate_inventory],
    )

    compliance_agent = Agent(
        client=client,
        name="supplier_compliance",
        instructions=(
            "You are Caldova's Supplier and Compliance specialist. Use the batch in the "
            "preceding inventory output, call get_supplier_status exactly once, and state "
            "what is known, unknown, and operationally relevant. You may recommend that "
            "the application request human approval, but you cannot approve or quarantine."
        ),
        tools=[get_supplier_status],
    )

    supervisor_agent = Agent(
        client=client,
        name="supervisor",
        instructions=(
            "You are Caldova's Recall Supervisor. Use the original user question and the "
            "three specialist outputs. For a focused question, answer only the requested fact "
            "in one or two sentences, adding uncertainty only when the fact is unknown. For a "
            "broad recall assessment, produce a concise full decision brief with sections "
            "Facts, Recommendation, Uncertainty, and Required Human Action. Do not claim "
            "approval or quarantine occurred. For any action or quarantine question, state "
            "that the application must collect named human approval before any quarantine."
        ),
    )

    return triage_agent, inventory_agent, compliance_agent, supervisor_agent


def build_workflow(client: FoundryChatClient):
    triage_agent, inventory_agent, compliance_agent, supervisor_agent = build_agents(client)

    triage = AgentExecutor(triage_agent, context_mode="last_agent")
    inventory = AgentExecutor(inventory_agent, context_mode="full")
    compliance = AgentExecutor(compliance_agent, context_mode="full")
    supervisor = AgentExecutor(supervisor_agent, context_mode="full")

    return (
        WorkflowBuilder(
            start_executor=triage,
            output_from=[supervisor],
            name="caldova_recall_workflow",
        )
        .add_edge(triage, inventory)
        .add_edge(inventory, compliance)
        .add_edge(compliance, supervisor)
        .build()
        .as_agent()
    )


def main():
    from agent_framework_foundry_hosting import ResponsesHostServer

    client = FoundryChatClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )
    server = ResponsesHostServer(RequestIsolatedWorkflowAgent(lambda: build_workflow(client)))
    server.run()


if __name__ == "__main__":
    main()
