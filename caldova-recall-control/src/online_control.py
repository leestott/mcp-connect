from __future__ import annotations

import asyncio
import base64
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
import os
from time import time
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, Request

from caldova_domain import InventoryPosition, RecallStore
from hosted_analysis import analyze


BATCH_ID = "B-2408-AX7"
ANALYSIS_TIMEOUT_SECONDS = 180


def enabled() -> bool:
    return os.environ.get("CALDOVA_HOSTED") == "1"


@dataclass(frozen=True)
class Caller:
    tenant: str
    object_id: str
    name: str
    can_approve: bool

    @property
    def key(self) -> str:
        return sha256(f"{self.tenant}:{self.object_id}".encode()).hexdigest()


def caller(request: Request) -> Caller:
    if not os.environ.get("WEBSITE_HOSTNAME"):
        raise HTTPException(503, "Hosted authentication requires the configured App Service host.")
    try:
        principal = json.loads(base64.b64decode(request.headers.get("x-ms-client-principal", ""), validate=True))
        if not isinstance(principal, dict) or not isinstance(principal.get("claims"), list):
            raise ValueError()
        name_type = principal.get("name_typ", "name")
        if not isinstance(name_type, str) or not name_type.strip():
            raise ValueError()
        claims = {}
        identity_claims = {
            "tid", "oid", "http://schemas.microsoft.com/identity/claims/tenantid",
            "http://schemas.microsoft.com/identity/claims/objectidentifier",
            name_type,
        }
        for item in principal["claims"]:
            if not isinstance(item, dict) or not all(isinstance(item.get(field), str) and item[field] for field in ("typ", "val")):
                raise ValueError()
            if item["typ"] in identity_claims and item["typ"] in claims and claims[item["typ"]] != item["val"]:
                raise ValueError()
            claims[item["typ"]] = item["val"]
        for short, qualified in (
            ("tid", "http://schemas.microsoft.com/identity/claims/tenantid"),
            ("oid", "http://schemas.microsoft.com/identity/claims/objectidentifier"),
        ):
            if short in claims and qualified in claims and claims[short] != claims[qualified]:
                raise ValueError()
        tenant = claims.get("http://schemas.microsoft.com/identity/claims/tenantid", claims.get("tid"))
        object_id = claims.get("http://schemas.microsoft.com/identity/claims/objectidentifier", claims.get("oid"))
        name = claims.get(name_type, object_id)
        if principal.get("auth_typ") != "aad" or not all(isinstance(value, str) and value for value in [tenant, object_id, name]):
            raise ValueError()
    except (ValueError, TypeError, KeyError, RecursionError):
        raise HTTPException(401, "Sign in to access the demo.") from None
    allowed = os.environ.get("CALDOVA_ALLOWED_USERS", "").split(",")
    if tenant != os.environ.get("AZURE_TENANT_ID") or object_id not in allowed:
        raise HTTPException(403, "This identity is not authorized for the demo.")
    if request.method != "GET":
        if request.headers.get("origin") != os.environ.get("CALDOVA_PUBLIC_ORIGIN") or request.headers.get("x-caldova-request") != "1":
            raise HTTPException(403, "A same-origin application request is required.")
    return Caller(tenant, object_id, name, object_id in os.environ.get("CALDOVA_APPROVERS", "").split(","))


def initial_state() -> dict[str, Any]:
    store = RecallStore()
    return {
        "generation": uuid4().hex,
        "inventory": [asdict(item) for item in store.inventory],
        "approvals": {}, "handles": {}, "audit": [],
        "last_result": None, "assessment": None, "correlation_id": None,
        "analysis_until": 0, "next_analysis_at": 0,
    }


def domain(state: dict[str, Any]) -> RecallStore:
    store = RecallStore()
    store.inventory = [InventoryPosition(**item) for item in state["inventory"]]
    store.approvals = state["approvals"]
    store.audit_log = state["audit"]
    return store


def approval_is_bound(approval: dict[str, Any], state: dict[str, Any], identity: Caller) -> bool:
    return (
        identity.can_approve
        and approval.get("actor") == identity.key
        and approval.get("generation") == state["generation"]
        and approval.get("batch_id") == BATCH_ID
        and approval.get("action") == "quarantine"
    )


def view(state: dict[str, Any], identity: Caller) -> dict[str, Any]:
    store = domain(state)
    return {
        "scenario": "fictional", "runtime": "hosted", "protocol": "2026-07-28",
        "model_deployment": os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", "caldova-model-router"),
        "notice": store.get_recall_notice(BATCH_ID),
        "inventory": store.locate_inventory(BATCH_ID),
        "supplier": store.get_supplier_status(BATCH_ID),
        "workflow": [], "calls": [], "audit": state["audit"],
        "last_result": state["last_result"], "correlation_id": state["correlation_id"],
        "assessment": state.get("assessment") or (
            state["last_result"] if state["last_result"] and state["last_result"].get("agent_text") else None
        ),
        "identity": {"name": identity.name, "can_approve": identity.can_approve},
        "analysis_running": state["analysis_until"] > time(),
        "replay_approval_id": next((
            handle for handle, approval in state["handles"].items()
            if approval.get("consumed") is True and approval_is_bound(approval, state, identity)
        ), None),
    }


class BlobSessions:
    def __init__(self, credential: Any) -> None:
        from azure.storage.blob.aio import ContainerClient
        self.container = ContainerClient.from_container_url(
            os.environ["CALDOVA_STATE_CONTAINER_URL"], credential=credential,
            connection_timeout=10, read_timeout=20, retry_total=2,
        )

    async def close(self) -> None:
        await self.container.close()

    async def load(self, key: str) -> tuple[dict[str, Any], str | None]:
        from azure.core.exceptions import ResourceNotFoundError
        try:
            download = await self.container.get_blob_client(f"{key}.json").download_blob()
            return json.loads(await download.readall()), download.properties.etag
        except ResourceNotFoundError:
            return initial_state(), None

    async def save(self, key: str, state: dict[str, Any], etag: str | None) -> str:
        from azure.core import MatchConditions
        from azure.core.exceptions import ResourceExistsError, ResourceModifiedError
        conditions = {"etag": etag, "match_condition": MatchConditions.IfNotModified} if etag else {}
        try:
            result = await self.container.get_blob_client(f"{key}.json").upload_blob(
                json.dumps(state), overwrite=etag is not None, **conditions,
            )
            return result["etag"]
        except (ResourceExistsError, ResourceModifiedError):
            raise HTTPException(409, "Demo state changed. Refresh before retrying.") from None


async def execute(request: Request, operation: str, approval_id: str | None = None) -> dict[str, Any]:
    identity = caller(request)
    sessions = request.app.state.online_sessions
    try:
        state, etag = await sessions.load(identity.key)
        if operation == "state":
            return view(state, identity)
        if state["analysis_until"] > time():
            raise HTTPException(409, "An analysis is already running. Wait for it to finish.")
        if operation == "analysis":
            if state["next_analysis_at"] > time():
                raise HTTPException(429, "Please wait before requesting another analysis.")
            if any(item["status"] == "quarantined" for item in state["inventory"]):
                raise HTTPException(409, "Reset your synthetic demo before starting another agent assessment.")
            state["last_result"] = None
            state["assessment"] = None
            state["handles"] = {}
            state["approvals"] = {}
            state["correlation_id"] = uuid4().hex
            state["analysis_until"] = time() + ANALYSIS_TIMEOUT_SECONDS + 10
            state["next_analysis_at"] = time() + 60
            etag = await sessions.save(identity.key, state, etag)
            try:
                async with asyncio.timeout(ANALYSIS_TIMEOUT_SECONDS):
                    answer = await request.app.state.online_analyze(state["correlation_id"])
                state["last_result"] = {
                    "status": "approval_required", "agent_text": answer.text,
                    "response_id": answer.response_id, "request_id": answer.request_id,
                }
                state["assessment"] = dict(state["last_result"])
            except asyncio.CancelledError:
                state["analysis_until"] = 0
                try:
                    await sessions.save(identity.key, state, etag)
                finally:
                    raise
            except Exception as error:
                state["analysis_until"] = 0
                await sessions.save(identity.key, state, etag)
                if isinstance(error, TimeoutError):
                    raise HTTPException(504, "The live agent request timed out. No inventory was changed.") from None
                raise HTTPException(502, "The live agent did not complete the assessment. No inventory was changed.") from None
            state["analysis_until"] = 0
        else:
            if not identity.can_approve:
                raise HTTPException(403, "An authorized demo approver is required.")
            store = domain(state)
            if operation == "approval":
                if not state["last_result"] or state["last_result"]["status"] != "approval_required":
                    raise HTTPException(409, "Complete a live assessment before approving quarantine.")
                result = store.request_approval(BATCH_ID, identity.name)
                handle = uuid4().hex
                state["handles"][handle] = {
                    "token": result["approval_token"], "actor": identity.key,
                    "batch_id": BATCH_ID, "action": "quarantine",
                    "generation": state["generation"], "expires": time() + 600,
                    "consumed": False,
                }
                await sessions.save(identity.key, state, etag)
                return {"status": "approved", "approval_id": handle, "approver": identity.name, "batch_id": BATCH_ID}
            if operation == "quarantine":
                approval = state["handles"].get(approval_id)
                if not approval or not approval_is_bound(approval, state, identity) or (approval["consumed"] is not True and approval["expires"] <= time()):
                    raise HTTPException(403, "Valid approval for this demo session is required.")
                result = store.quarantine_batch(BATCH_ID, approval["token"])
                approval["consumed"] = True
                state["inventory"] = [asdict(item) for item in store.inventory]
                state["last_result"] = result
            elif operation == "reset":
                audit = state["audit"]
                next_analysis_at = state["next_analysis_at"]
                state = initial_state()
                state["next_analysis_at"] = next_analysis_at
                state["audit"] = audit + [{
                    "timestamp": datetime.now(UTC).isoformat(), "event": "demo_reset", "batch_id": BATCH_ID,
                    "details": {"actor": identity.object_id},
                }]
            else:
                raise HTTPException(400, "Unsupported operation.")
        await sessions.save(identity.key, state, etag)
        return view(state, identity)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, "Durable demo state is unavailable. Refresh before retrying.") from None


async def live_analysis(credential: Any, correlation_id: str) -> Any:
    async def token() -> str:
        return (await credential.get_token("https://ai.azure.com/.default")).token

    return await analyze(
        os.environ["CALDOVA_AGENT_ENDPOINT"],
        "Assess recall batch B-2408-AX7, report affected stock and supplier status, and prepare a supervisor decision brief. Do not quarantine stock without explicit approval.",
        correlation_id, token,
    )