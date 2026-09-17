import asyncio
import json
import sys
from pathlib import Path

import pytest


SOURCE = Path(__file__).parents[1] / "src" / "agent-framework-workflows-responses"
sys.path.insert(0, str(SOURCE))

from main import (  # noqa: E402
    RequestIsolatedWorkflowAgent,
    _bounded_env_int,
    build_agents,
    build_workflow,
    get_recall_notice,
    get_supplier_status,
    locate_inventory,
)
from mcp_v2_bridge import call_tool  # noqa: E402


BATCH_ID = "B-2408-AX7"
GOLDEN_DATASET = Path(__file__).with_name("golden.jsonl")


def _tool_names(agent) -> list[str]:
    return [tool.name for tool in agent.default_options.get("tools", [])]


def test_mcp_runtime_limits_are_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CALDOVA_TEST_LIMIT", "300")
    assert _bounded_env_int("CALDOVA_TEST_LIMIT", 15, 5, 30) == 30

    monkeypatch.setenv("CALDOVA_TEST_LIMIT", "invalid")
    assert _bounded_env_int("CALDOVA_TEST_LIMIT", 15, 5, 30) == 15


def test_four_agents_have_least_privilege_tool_access() -> None:
    triage, inventory, compliance, supervisor = build_agents(object())

    assert [agent.name for agent in (triage, inventory, compliance, supervisor)] == [
        "recall_triage",
        "inventory_impact",
        "supplier_compliance",
        "supervisor",
    ]
    assert _tool_names(triage) == ["get_recall_notice"]
    assert _tool_names(inventory) == ["locate_inventory"]
    assert _tool_names(compliance) == ["get_supplier_status"]
    assert _tool_names(supervisor) == []


def test_supervisor_instructions_distinguish_focused_questions() -> None:
    *_, supervisor = build_agents(object())

    instructions = supervisor.default_options["instructions"]
    assert "answer only the requested fact" in instructions
    assert "full decision brief" in instructions
    assert "named human approval" in instructions


def test_golden_dataset_uses_supported_expected_behavior_field() -> None:
    rows = [json.loads(line) for line in GOLDEN_DATASET.read_text().splitlines()]

    assert len(rows) == 7
    assert all(set(row) == {"query", "expected_behavior"} for row in rows)
    assert all(row["expected_behavior"] for row in rows)


def test_real_agent_framework_workflow_builds() -> None:
    assert type(build_workflow(object())).__name__ == "WorkflowAgent"


@pytest.mark.asyncio
async def test_hosted_workflows_are_isolated_per_run() -> None:
    created_agents = []
    streamed_agents_by_task = {}

    def tracked_factory():
        agent = build_workflow(object())
        created_agents.append(agent)

        async def tracked_stream(*args, **kwargs):
            task = asyncio.current_task()
            streamed_agents_by_task.setdefault(task, []).append(id(agent))
            if False:
                yield None

        agent._run_stream_impl = tracked_stream
        return agent

    isolated = RequestIsolatedWorkflowAgent(tracked_factory)
    created_agents.clear()

    async def consume(stream) -> None:
        async for _ in stream:
            pass

    async def restore_then_run(index: int) -> tuple[int, int]:
        await consume(
            isolated.run(
                stream=True,
                checkpoint_id=f"checkpoint-{index}",
                checkpoint_storage=object(),
            )
        )
        await asyncio.sleep(0)
        await consume(isolated.run([f"request-{index}"], stream=True))
        return tuple(streamed_agents_by_task[asyncio.current_task()])

    restored_pairs = await asyncio.gather(*(restore_then_run(index) for index in range(7)))

    assert all(restored == continued for restored, continued in restored_pairs)
    assert len({restored for restored, _ in restored_pairs}) == 7
    assert len(created_agents) == 7


@pytest.mark.asyncio
async def test_workflow_read_tools_use_mcp_v2_boundary() -> None:
    notice = await get_recall_notice(BATCH_ID)
    inventory = await locate_inventory(BATCH_ID)
    supplier = await get_supplier_status(BATCH_ID)

    assert notice["risk_tier"] == "high"
    assert inventory["total_units"] == 2196
    assert inventory["locations"] == 4
    assert supplier["supplier_acknowledged"] is True


@pytest.mark.asyncio
async def test_workflow_tool_failure_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CALDOVA_MCP_PYTHON", "missing-caldova-python")

    with pytest.raises(RuntimeError, match="^Caldova recall data is temporarily unavailable$"):
        await locate_inventory(BATCH_ID)


@pytest.mark.asyncio
async def test_bridge_rejects_mutation_tools() -> None:
    with pytest.raises(ValueError, match="read-only tools"):
        await call_tool(
            "quarantine_batch",
            {"batch_id": BATCH_ID, "approval_token": "0" * 16},
        )
