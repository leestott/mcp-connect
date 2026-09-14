from __future__ import annotations

from pathlib import Path
import sys
from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from mcp import Client
from pydantic import BaseModel, Field

AGENT_SOURCE = Path(__file__).with_name("agent-framework-workflows-responses")
sys.path.insert(0, str(AGENT_SOURCE))

from caldova_domain import STORE  # noqa: E402
from caldova_mcp import mcp  # noqa: E402


BATCH_ID = "B-2408-AX7"
STATIC_DIR = Path(__file__).with_name("control_tower_static")
STAGES = [
    {"id": "triage", "name": "Recall Triage", "tool": "get_recall_notice"},
    {"id": "inventory", "name": "Inventory Impact", "tool": "locate_inventory"},
    {"id": "compliance", "name": "Supplier / Compliance", "tool": "get_supplier_status"},
    {"id": "supervisor", "name": "Supervisor", "tool": None},
]


class ApprovalRequest(BaseModel):
    approver: str = Field(min_length=3, max_length=120)


class QuarantineRequest(BaseModel):
    approval_id: str = Field(min_length=8, max_length=64)


class DemoRuntime:
    def __init__(self) -> None:
        self.approvals: dict[str, str] = {}
        self.calls: list[dict[str, Any]] = []
        self.workflow = [{**stage, "status": "pending"} for stage in STAGES]
        self.last_result: dict[str, Any] | None = None
        self.correlation_id: str | None = None

    def reset(self) -> None:
        self.approvals.clear()
        self.calls.clear()
        self.workflow = [{**stage, "status": "pending"} for stage in STAGES]
        self.last_result = None
        self.correlation_id = None


runtime = DemoRuntime()


app = FastAPI(title="Caldova Recall Control Tower")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def snapshot() -> dict[str, Any]:
    notice = STORE.get_recall_notice(BATCH_ID)
    inventory = STORE.locate_inventory(BATCH_ID)
    supplier = STORE.get_supplier_status(BATCH_ID)
    return {
        "scenario": "fictional",
        "runtime": "local",
        "protocol": "2026-07-28",
        "model_deployment": "caldova-model-router",
        "notice": notice,
        "inventory": inventory,
        "supplier": supplier,
        "workflow": runtime.workflow,
        "calls": runtime.calls,
        "audit": STORE.audit_events(),
        "last_result": runtime.last_result,
        "correlation_id": runtime.correlation_id,
    }


async def invoke(request: Request, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    started = perf_counter()
    call = {
        "tool": tool_name,
        "input": {key: value for key, value in arguments.items() if key != "approval_token"},
        "protocol": "2026-07-28",
        "correlation_id": runtime.correlation_id,
        "outcome": "running",
    }
    runtime.calls.insert(0, call)
    try:
        async with Client(mcp, raise_exceptions=True) as client:
            result = await client.call_tool(tool_name, arguments)
        call["outcome"] = "success"
        return result.structured_content or {}
    except Exception:
        call["outcome"] = "error"
        raise HTTPException(status_code=503, detail="Recall operation is temporarily unavailable") from None
    finally:
        call["duration_ms"] = round((perf_counter() - started) * 1000, 1)


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    return Response(status_code=204)


@app.get("/api/state")
async def get_state() -> dict[str, Any]:
    return snapshot()


@app.post("/api/analysis")
async def run_analysis(request: Request) -> dict[str, Any]:
    runtime.calls.clear()
    runtime.workflow = [{**stage, "status": "pending"} for stage in STAGES]
    runtime.correlation_id = uuid4().hex

    outputs: dict[str, dict[str, Any]] = {}
    for index, stage in enumerate(STAGES[:3]):
        runtime.workflow[index]["status"] = "running"
        try:
            outputs[stage["id"]] = await invoke(
                request, stage["tool"], {"batch_id": BATCH_ID}
            )
        except HTTPException:
            runtime.workflow[index]["status"] = "error"
            raise
        runtime.workflow[index]["status"] = "complete"

    runtime.workflow[3]["status"] = "complete"
    runtime.last_result = {
        "status": "approval_required",
        "facts": {
            "risk_tier": outputs["triage"]["risk_tier"],
            "units": outputs["inventory"]["total_units"],
            "locations": outputs["inventory"]["locations"],
            "supplier_acknowledged": outputs["compliance"]["supplier_acknowledged"],
        },
        "recommendation": "Quarantine all affected positions after named human approval.",
        "uncertainty": "Replacement stock is expected in 36 hours; credit note remains drafted.",
        "required_human_action": "A pharmacist or compliance lead must approve the exact mutation.",
    }
    return snapshot()


@app.post("/api/approval")
async def request_approval(body: ApprovalRequest, request: Request) -> dict[str, Any]:
    runtime.correlation_id = runtime.correlation_id or uuid4().hex
    result = await invoke(
        request,
        "request_approval",
        {"batch_id": BATCH_ID, "approver": body.approver},
    )
    token = result.pop("approval_token")
    approval_id = uuid4().hex[:12]
    runtime.approvals[approval_id] = token
    return {
        "status": result["status"],
        "batch_id": BATCH_ID,
        "approval_id": approval_id,
        "approver": body.approver,
    }


@app.post("/api/quarantine")
async def quarantine(body: QuarantineRequest, request: Request) -> dict[str, Any]:
    token = runtime.approvals.get(body.approval_id)
    if token is None:
        raise HTTPException(status_code=403, detail="Valid named approval is required")
    runtime.last_result = await invoke(
        request,
        "quarantine_batch",
        {"batch_id": BATCH_ID, "approval_token": token},
    )
    return snapshot()


@app.post("/api/reset")
async def reset(request: Request) -> dict[str, Any]:
    runtime.correlation_id = uuid4().hex
    await invoke(request, "reset_demo", {})
    runtime.reset()
    return snapshot()
