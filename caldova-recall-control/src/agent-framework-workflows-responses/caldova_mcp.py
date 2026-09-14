from __future__ import annotations

from typing import Annotated, Any

from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from caldova_domain import STORE


BatchId = Annotated[
    str,
    Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Z0-9-]+$",
        description="Caldova product batch identifier, for example B-2408-AX7.",
    ),
]


mcp = MCPServer(
    "caldova-recall-operations",
    title="Caldova Recall Operations",
    description="Typed tools for the fictional Caldova pharmaceutical recall demonstration.",
    version="1.0.0",
    instructions=(
        "Use read-only tools to establish recall facts before recommending action. "
        "Never call quarantine_batch without a batch-specific approval token supplied "
        "by the application after explicit human approval."
    ),
)


@mcp.tool(
    title="Get recall notice",
    annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False),
)
def get_recall_notice(batch_id: BatchId) -> dict[str, Any]:
    """Return validated recall and product details for a Caldova batch."""
    return STORE.get_recall_notice(batch_id)


@mcp.tool(
    title="Locate affected inventory",
    annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False),
)
def locate_inventory(batch_id: BatchId) -> dict[str, Any]:
    """Return inventory positions, location count, and units for a Caldova batch."""
    return STORE.locate_inventory(batch_id)


@mcp.tool(
    title="Get supplier status",
    annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False),
)
def get_supplier_status(batch_id: BatchId) -> dict[str, Any]:
    """Return supplier acknowledgement, replacement ETA, and credit-note status."""
    return STORE.get_supplier_status(batch_id)


@mcp.tool(
    title="Record human approval",
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
def request_approval(
    batch_id: BatchId,
    approver: Annotated[
        str,
        Field(
            min_length=3,
            max_length=120,
            description="Name and role of the human pharmacist or compliance approver.",
        ),
    ],
) -> dict[str, str]:
    """Record explicit human approval and return a batch-scoped demo credential."""
    return STORE.request_approval(batch_id, approver)


@mcp.tool(
    title="Quarantine recalled batch",
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
def quarantine_batch(
    batch_id: BatchId,
    approval_token: Annotated[
        str,
        Field(
            min_length=16,
            max_length=16,
            pattern=r"^[a-f0-9]+$",
            description="Batch-scoped credential returned after explicit human approval.",
        ),
    ],
) -> dict[str, Any]:
    """Quarantine affected stock after deterministic approval validation."""
    return STORE.quarantine_batch(batch_id, approval_token)


@mcp.tool(
    title="Get sanitized audit events",
    annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False),
)
def get_audit_events() -> list[dict[str, Any]]:
    """Return recall audit events without approval credentials."""
    return STORE.audit_events()


@mcp.tool(
    title="Reset fictional demo state",
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
def reset_demo() -> dict[str, Any]:
    """Restore the synthetic inventory and clear approvals and audit events."""
    return STORE.reset()


if __name__ == "__main__":
    mcp.run(transport="stdio")