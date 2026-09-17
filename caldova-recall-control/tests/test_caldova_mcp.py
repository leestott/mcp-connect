import sys
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters


SOURCE = Path(__file__).parents[1] / "src" / "agent-framework-workflows-responses"
sys.path.insert(0, str(SOURCE))

from caldova_domain import STORE  # noqa: E402
from caldova_mcp import mcp  # noqa: E402


BATCH_ID = "B-2408-AX7"
TOOL_NAMES = [
    "get_recall_notice",
    "locate_inventory",
    "get_supplier_status",
    "request_approval",
    "quarantine_batch",
    "get_audit_events",
    "reset_demo",
]


@pytest.fixture(autouse=True)
def reset_store() -> None:
    STORE.reset()


@pytest.mark.asyncio
async def test_protocol_tools_schemas_and_annotations() -> None:
    async with Client(mcp, raise_exceptions=True) as client:
        listing = await client.list_tools()

        assert client.protocol_version == "2026-07-28"
        assert [tool.name for tool in listing.tools] == TOOL_NAMES

        tools = {tool.name: tool for tool in listing.tools}
        for tool in tools.values():
            assert tool.input_schema["type"] == "object"
            assert tool.output_schema is not None
            assert tool.annotations is not None
            assert tool.annotations.open_world_hint is False

        assert tools["get_recall_notice"].annotations.read_only_hint is True
        assert tools["locate_inventory"].annotations.read_only_hint is True
        assert tools["get_supplier_status"].annotations.read_only_hint is True
        assert tools["get_audit_events"].annotations.read_only_hint is True
        assert tools["request_approval"].annotations.destructive_hint is False
        assert tools["request_approval"].annotations.idempotent_hint is True
        assert tools["quarantine_batch"].annotations.destructive_hint is True
        assert tools["quarantine_batch"].annotations.idempotent_hint is True
        assert tools["reset_demo"].annotations.destructive_hint is True
        assert tools["reset_demo"].annotations.idempotent_hint is True

        batch_schema = tools["get_recall_notice"].input_schema["properties"]["batch_id"]
        assert batch_schema["pattern"] == "^[A-Z0-9-]+$"
        token_schema = tools["quarantine_batch"].input_schema["properties"]["approval_token"]
        assert token_schema["minLength"] == token_schema["maxLength"] == 16


@pytest.mark.asyncio
async def test_direct_stdio_transport() -> None:
    server = StdioServerParameters(command=sys.executable, args=[str(SOURCE / "caldova_mcp.py")])

    async with Client(server, raise_exceptions=True) as client:
        protocol_version = client.protocol_version
        result = await client.call_tool("locate_inventory", {"batch_id": BATCH_ID})

    assert protocol_version == "2026-07-28"
    assert result.structured_content["total_units"] == 2196
    assert result.structured_content["locations"] == 4


@pytest.mark.asyncio
async def test_read_tools_return_structured_recall_facts() -> None:
    async with Client(mcp, raise_exceptions=True) as client:
        notice = await client.call_tool("get_recall_notice", {"batch_id": BATCH_ID})
        inventory = await client.call_tool("locate_inventory", {"batch_id": BATCH_ID})
        supplier = await client.call_tool("get_supplier_status", {"batch_id": BATCH_ID})

    assert notice.structured_content["found"] is True
    assert notice.structured_content["risk_tier"] == "high"
    assert inventory.structured_content["total_units"] == 2196
    assert inventory.structured_content["locations"] == 4
    assert supplier.structured_content["supplier_acknowledged"] is True


@pytest.mark.asyncio
async def test_quarantine_failure_is_sanitized() -> None:
    invalid_token = "0" * 16
    async with Client(mcp) as client:
        result = await client.call_tool(
            "quarantine_batch",
            {"batch_id": BATCH_ID, "approval_token": invalid_token},
        )

    error_text = " ".join(getattr(item, "text", "") for item in result.content)
    assert result.is_error is True
    assert error_text == "Error executing tool quarantine_batch"
    assert invalid_token not in error_text
    assert "Traceback" not in error_text
    assert "caldova_domain.py" not in error_text
    assert "approval token" not in error_text


@pytest.mark.asyncio
async def test_approval_quarantine_audit_and_replay() -> None:
    async with Client(mcp, raise_exceptions=True) as client:
        approval = await client.call_tool(
            "request_approval",
            {"batch_id": BATCH_ID, "approver": "Asha Rao, Responsible Pharmacist"},
        )
        token = approval.structured_content["approval_token"]

        first = await client.call_tool(
            "quarantine_batch",
            {"batch_id": BATCH_ID, "approval_token": token},
        )
        replay = await client.call_tool(
            "quarantine_batch",
            {"batch_id": BATCH_ID, "approval_token": token},
        )
        audit = await client.call_tool("get_audit_events")

    assert first.structured_content["positions_changed"] == 4
    assert first.structured_content["units_quarantined"] == 2196
    assert first.structured_content["idempotent_replay"] is False
    assert replay.structured_content["positions_changed"] == 0
    assert replay.structured_content["idempotent_replay"] is True
    audit_events = audit.structured_content["result"]
    assert [event["event"] for event in audit_events] == [
        "approval_issued",
        "batch_quarantined",
        "batch_quarantined",
    ]
    assert token not in repr(audit_events)