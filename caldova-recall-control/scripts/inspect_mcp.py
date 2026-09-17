"""Inspect the synthetic MCP server without a model or cloud connection."""

import asyncio
import json
from pathlib import Path
import sys

from mcp import Client, StdioServerParameters


SERVER = Path(__file__).resolve().parents[1] / "src" / "agent-framework-workflows-responses" / "caldova_mcp.py"
BATCH_ID = "B-2408-AX7"


def show(title: str, value: object) -> None:
    print(f"\n{title}")
    print(json.dumps(value, indent=2))


async def inspect() -> None:
    server = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    async with asyncio.timeout(30), Client(server) as client:
        show("1. CONNECT: negotiated MCP protocol", client.protocol_version)

        listing = await client.list_tools()
        show("2. DISCOVER: tools/list", [tool.name for tool in listing.tools])
        inventory_tool = next(tool for tool in listing.tools if tool.name == "locate_inventory")
        show("3. CONTRACT: inventory inputSchema", inventory_tool.input_schema)
        show("   outputSchema (generic object, not a strict inventory DTO)", inventory_tool.output_schema)
        show("   annotations (hints, not permissions)", inventory_tool.annotations.model_dump(by_alias=True))

        arguments = {"batch_id": BATCH_ID}
        show("4. CALL: tools/call params", {"name": "locate_inventory", "arguments": arguments})
        result = await client.call_tool("locate_inventory", arguments)
        show("   structuredContent", result.structured_content)
        assert not result.is_error
        assert result.structured_content["total_units"] == 2196
        assert result.structured_content["locations"] == 4

        invalid = await client.call_tool("locate_inventory", {"batch_id": "bad batch!"})
        show("5. VALIDATION: malformed batch rejected", {"isError": invalid.is_error})
        assert invalid.is_error

        denied = await client.call_tool(
            "quarantine_batch",
            {"batch_id": BATCH_ID, "approval_token": "0" * 16},
        )
        show("6. POLICY: schema-valid but unapproved write", {
            "isError": denied.is_error,
            "content": [item.text for item in denied.content if hasattr(item, "text")],
        })
        assert denied.is_error
        after = await client.call_tool("locate_inventory", arguments)
        assert after.structured_content == result.structured_content
        show("7. VERIFY", {"inventory_unchanged": True, "model_calls": 0})

    print("\nIndependent child-process fixtures; the browser's state was not changed.")


if __name__ == "__main__":
    asyncio.run(inspect())