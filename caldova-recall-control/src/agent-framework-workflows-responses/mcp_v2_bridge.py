from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from mcp import Client

from caldova_mcp import mcp

READ_ONLY_TOOLS = frozenset(
    {"get_recall_notice", "locate_inventory", "get_supplier_status"}
)


async def call_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if tool_name not in READ_ONLY_TOOLS:
        raise ValueError("Bridge only permits Caldova read-only tools")

    async with Client(mcp, raise_exceptions=True) as client:
        result = await client.call_tool(tool_name, arguments)

    if result.structured_content is None:
        raise RuntimeError("MCP tool returned no structured content")
    return result.structured_content


async def run() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("tool_name")
    parser.add_argument("arguments_json")
    args = parser.parse_args()

    arguments = json.loads(args.arguments_json)
    result = await call_tool(args.tool_name, arguments)
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    asyncio.run(run())
