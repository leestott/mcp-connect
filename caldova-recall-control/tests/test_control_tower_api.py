import sys
import asyncio
import base64
import copy
import json
from pathlib import Path

import httpx
import pytest
from azure.core.credentials import AccessToken
from azure.core.pipeline.transport import AsyncHttpResponse, AsyncHttpTransport
from fastapi.testclient import TestClient


SOURCE = Path(__file__).parents[1] / "src"
sys.path.insert(0, str(SOURCE))

from control_tower_api import app  # noqa: E402
from hosted_analysis import HostedAnalysisError, analyze, parse_answer  # noqa: E402
from hosted_analysis import HostedAnswer  # noqa: E402
import online_control  # noqa: E402
from fastapi import HTTPException  # noqa: E402


class FakeSessions:
    def __init__(self):
        self.states = {}
        self.revisions = {}

    async def load(self, key):
        return copy.deepcopy(self.states.get(key, online_control.initial_state())), self.revisions.get(key)

    async def save(self, key, state, etag):
        if self.revisions.get(key) != etag:
            raise HTTPException(409, "Demo state changed.")
        self.states[key] = copy.deepcopy(state)
        self.revisions[key] = str(int(etag or "0") + 1)
        return self.revisions[key]


def identity_headers(object_id="approver"):
    principal = {"auth_typ": "aad", "name_typ": "name", "claims": [
        {"typ": "tid", "val": "tenant"}, {"typ": "oid", "val": object_id},
        {"typ": "name", "val": f"Verified {object_id}"},
    ]}
    return {
        "x-ms-client-principal": base64.b64encode(json.dumps(principal).encode()).decode(),
        "origin": "https://demo.azurewebsites.net", "x-caldova-request": "1",
    }


@pytest.fixture
def hosted_api(monkeypatch):
    monkeypatch.setenv("CALDOVA_HOSTED", "1")
    monkeypatch.setenv("WEBSITE_HOSTNAME", "demo.azurewebsites.net")
    monkeypatch.setenv("AZURE_TENANT_ID", "tenant")
    monkeypatch.setenv("CALDOVA_ALLOWED_USERS", "approver,viewer,other")
    monkeypatch.setenv("CALDOVA_APPROVERS", "approver,other")
    monkeypatch.setenv("CALDOVA_PUBLIC_ORIGIN", "https://demo.azurewebsites.net")
    sessions = FakeSessions()
    async def answer(correlation_id):
        return HostedAnswer("Actual hosted answer <script>alert(1)</script>", "resp_live", "remote_id")
    monkeypatch.setattr(app.state, "online_sessions", sessions, raising=False)
    monkeypatch.setattr(app.state, "online_analyze", answer, raising=False)
    client = TestClient(app)
    yield client, sessions
    client.close()


def test_hosted_api_denies_anonymous_unlisted_and_cross_origin(hosted_api):
    client, _ = hosted_api
    assert client.get("/api/state").status_code == 401
    assert client.get("/", headers=identity_headers("unlisted")).status_code == 403
    headers = identity_headers()
    headers["origin"] = "https://untrusted.example"
    assert client.post("/api/reset", headers=headers).status_code == 403
    headers = identity_headers()
    del headers["x-caldova-request"]
    assert client.post("/api/analysis", headers=headers).status_code == 403


@pytest.mark.parametrize("extra_claim", [
    {"typ": "oid", "val": "unlisted"},
    {"typ": "http://schemas.microsoft.com/identity/claims/objectidentifier", "val": "unlisted"},
    {"typ": "roles", "val": ["approver"]},
])
def test_hosted_api_rejects_malformed_or_ambiguous_principals(hosted_api, extra_claim):
    client, sessions = hosted_api
    headers = identity_headers()
    principal = json.loads(base64.b64decode(headers["x-ms-client-principal"]))
    principal["claims"].insert(0, extra_claim)
    headers["x-ms-client-principal"] = base64.b64encode(json.dumps(principal).encode()).decode()
    assert client.get("/api/state", headers=headers).status_code == 401
    assert sessions.states == {}


@pytest.mark.parametrize("principal", [
    None, [], "aad", 42,
    {"auth_typ": "aad", "claims": None},
    {"auth_typ": "aad", "claims": [None]},
    {"auth_typ": "aad", "claims": [{"typ": [], "val": "tenant"}]},
    {"auth_typ": "aad", "name_typ": [], "claims": []},
])
def test_hosted_api_malformed_principal_shapes_are_unauthorized(hosted_api, principal):
    client, _ = hosted_api
    headers = identity_headers()
    headers["x-ms-client-principal"] = base64.b64encode(json.dumps(principal).encode()).decode()
    assert client.get("/api/state", headers=headers).status_code == 401


@pytest.mark.parametrize("encoded", ["", "not base64!", "/w==", "ew=="])
def test_hosted_api_bad_principal_encoding_is_unauthorized(hosted_api, encoded):
    client, _ = hosted_api
    headers = {**identity_headers(), "x-ms-client-principal": encoded}
    assert client.get("/api/state", headers=headers).status_code == 401


@pytest.mark.parametrize("name_type", [None, 0, False, "", [], {}])
def test_hosted_api_rejects_malformed_name_claim_type(hosted_api, name_type):
    client, _ = hosted_api
    headers = identity_headers()
    principal = json.loads(base64.b64decode(headers["x-ms-client-principal"]))
    principal["name_typ"] = name_type
    headers["x-ms-client-principal"] = base64.b64encode(json.dumps(principal).encode()).decode()
    assert client.get("/api/state", headers=headers).status_code == 401


def test_hosted_api_denial_has_security_headers(hosted_api):
    client, _ = hosted_api
    response = client.get("/api/state")
    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_hosted_api_snapshot_exposes_only_owned_consumed_replay_id(hosted_api, monkeypatch):
    client, sessions = hosted_api
    headers = identity_headers()
    assert client.get("/api/state", headers=headers).json()["replay_approval_id"] is None
    client.post("/api/analysis", headers=headers)
    approval = client.post("/api/approval", headers=headers, json={"approver": "Spoofed"}).json()
    assert client.get("/api/state", headers=headers).json()["replay_approval_id"] is None
    body = {"approval_id": approval["approval_id"]}
    assert client.post("/api/quarantine", headers=headers, json=body).status_code == 200
    state = next(iter(sessions.states.values()))
    token = state["handles"][approval["approval_id"]]["token"]
    monkeypatch.setattr(online_control, "time", lambda: state["handles"][approval["approval_id"]]["expires"] + 1)
    refreshed = client.get("/api/state", headers=headers).json()
    assert refreshed["replay_approval_id"] == approval["approval_id"]
    assert token not in json.dumps(refreshed)
    assert "handles" not in refreshed
    assert client.get("/api/state", headers=identity_headers("other")).json()["replay_approval_id"] is None
    replay = client.post("/api/quarantine", headers=headers, json={"approval_id": refreshed["replay_approval_id"]})
    assert replay.json()["last_result"]["positions_changed"] == 0
    monkeypatch.setenv("CALDOVA_APPROVERS", "other")
    assert client.get("/api/state", headers=headers).json()["replay_approval_id"] is None
    assert client.post("/api/quarantine", headers=headers, json=body).status_code == 403
    monkeypatch.setenv("CALDOVA_APPROVERS", "approver,other")
    assert client.post("/api/reset", headers=headers).json()["replay_approval_id"] is None
    assert client.post("/api/quarantine", headers=headers, json=body).status_code == 403


@pytest.mark.parametrize("field,value", [
    ("actor", "other"), ("generation", "old-generation"),
    ("batch_id", "other-batch"), ("action", "other-action"),
])
def test_hosted_api_approval_binding_is_checked_even_in_own_state(hosted_api, field, value):
    client, sessions = hosted_api
    headers = identity_headers()
    client.post("/api/analysis", headers=headers)
    approval = client.post("/api/approval", headers=headers, json={"approver": "Spoofed"}).json()
    state = next(iter(sessions.states.values()))
    state["handles"][approval["approval_id"]][field] = value
    before = copy.deepcopy(state)
    assert client.post("/api/quarantine", headers=headers, json={"approval_id": approval["approval_id"]}).status_code == 403
    assert next(iter(sessions.states.values())) == before
    state["handles"][approval["approval_id"]]["consumed"] = True
    assert client.get("/api/state", headers=headers).json()["replay_approval_id"] is None


def test_hosted_api_expiry_boundary_is_exclusive(hosted_api, monkeypatch):
    client, sessions = hosted_api
    headers = identity_headers()
    client.post("/api/analysis", headers=headers)
    approval = client.post("/api/approval", headers=headers, json={"approver": "Spoofed"}).json()
    state = next(iter(sessions.states.values()))
    expires = state["handles"][approval["approval_id"]]["expires"]
    monkeypatch.setattr(online_control, "time", lambda: expires)
    assert client.post("/api/quarantine", headers=headers, json={"approval_id": approval["approval_id"]}).status_code == 403


@pytest.mark.parametrize("failure", [RuntimeError("private credential detail"), TimeoutError("private timeout")])
def test_hosted_api_unexpected_analysis_failure_releases_lease(hosted_api, monkeypatch, failure):
    client, _ = hosted_api
    async def fail(correlation_id):
        raise failure
    monkeypatch.setattr(app.state, "online_analyze", fail)
    response = client.post("/api/analysis", headers=identity_headers())
    assert response.status_code in (502, 504)
    assert "private" not in response.text
    state = client.get("/api/state", headers=identity_headers()).json()
    assert state["analysis_running"] is False
    assert state["last_result"] is None
    assert client.post("/api/approval", headers=identity_headers(), json={"approver": "Spoofed"}).status_code == 409


@pytest.mark.asyncio
async def test_hosted_api_cancellation_releases_lease(hosted_api, monkeypatch):
    from starlette.requests import Request
    _, sessions = hosted_api
    async def cancel(correlation_id):
        raise asyncio.CancelledError()
    monkeypatch.setattr(app.state, "online_analyze", cancel)
    request = Request({"type": "http", "method": "POST", "app": app,
                       "headers": [(name.encode(), value.encode()) for name, value in identity_headers().items()]})
    with pytest.raises(asyncio.CancelledError):
        await online_control.execute(request, "analysis")
    state = next(iter(sessions.states.values()))
    assert state["analysis_until"] == 0
    assert state["last_result"] is None


def test_hosted_api_analysis_deadline_releases_lease(hosted_api, monkeypatch):
    client, _ = hosted_api
    async def stall(correlation_id):
        await asyncio.Event().wait()
    monkeypatch.setattr(app.state, "online_analyze", stall)
    monkeypatch.setattr(online_control, "ANALYSIS_TIMEOUT_SECONDS", 0.01, raising=False)
    response = client.post("/api/analysis", headers=identity_headers())
    assert response.status_code == 504
    assert client.get("/api/state", headers=identity_headers()).json()["analysis_running"] is False


@pytest.mark.parametrize("fail", [False, True])
def test_hosted_api_stale_analysis_cannot_overwrite_new_generation(hosted_api, monkeypatch, fail):
    client, sessions = hosted_api
    async def concurrent_reset(correlation_id):
        key = next(iter(sessions.states))
        replacement = online_control.initial_state()
        replacement["audit"] = [{"event": "newer_reset"}]
        await sessions.save(key, replacement, sessions.revisions[key])
        if fail:
            raise HostedAnalysisError("Failed old request")
        return HostedAnswer("Stale answer", "old-response", None)
    monkeypatch.setattr(app.state, "online_analyze", concurrent_reset)
    assert client.post("/api/analysis", headers=identity_headers()).status_code == 409
    state = client.get("/api/state", headers=identity_headers()).json()
    assert state["last_result"] is None
    assert state["audit"] == [{"event": "newer_reset"}]


def test_hosted_api_quarantine_conflict_does_not_consume_approval(hosted_api, monkeypatch):
    client, sessions = hosted_api
    headers = identity_headers()
    client.post("/api/analysis", headers=headers)
    approval = client.post("/api/approval", headers=headers, json={"approver": "Spoofed"}).json()
    before = copy.deepcopy(sessions.states)
    save = sessions.save
    async def conflict(*args):
        raise HTTPException(409, "Demo state changed.")
    monkeypatch.setattr(sessions, "save", conflict)
    body = {"approval_id": approval["approval_id"]}
    assert client.post("/api/quarantine", headers=headers, json=body).status_code == 409
    assert sessions.states == before
    monkeypatch.setattr(sessions, "save", save)
    assert client.post("/api/quarantine", headers=headers, json=body).json()["last_result"]["positions_changed"] == 4


def test_hosted_api_complete_isolated_approval_replay_and_reset(hosted_api):
    client, _ = hosted_api
    headers = identity_headers()
    response = client.post("/api/analysis", headers=headers).json()
    assert response["runtime"] == "hosted"
    assert response["last_result"]["response_id"] == "resp_live"
    assessment = response["assessment"]
    assert assessment == response["last_result"]
    assert response["workflow"] == []
    assert response["calls"] == []
    approval = client.post("/api/approval", headers=headers, json={"approver": "Spoofed Name"}).json()
    assert approval["approver"] == "Verified approver"
    body = {"approval_id": approval["approval_id"]}
    assert client.post("/api/quarantine", headers=identity_headers("other"), json=body).status_code == 403
    first = client.post("/api/quarantine", headers=headers, json=body).json()
    assert first["last_result"]["positions_changed"] == 4
    assert first["assessment"] == assessment
    replay = client.post("/api/quarantine", headers=headers, json=body).json()
    assert replay["last_result"]["positions_changed"] == 0
    assert replay["last_result"]["idempotent_replay"] is True
    assert replay["assessment"] == assessment
    assert client.get("/api/state", headers=headers).json()["assessment"] == assessment
    other = client.get("/api/state", headers=identity_headers("other")).json()
    assert all(item["status"] == "available" for item in other["inventory"]["positions"])
    assert other["last_result"] is None
    assert other["assessment"] is None
    assert "approval_token" not in json.dumps(first)
    assert "handles" not in first
    reset = client.post("/api/reset", headers=headers).json()
    assert reset["audit"][-1]["event"] == "demo_reset"
    assert reset["assessment"] is None
    assert client.post("/api/quarantine", headers=headers, json=body).status_code == 403


def test_hosted_api_viewer_cannot_approve_and_failed_analysis_cannot_authorize(hosted_api, monkeypatch):
    client, sessions = hosted_api
    assert client.post("/api/approval", headers=identity_headers("viewer"), json={"approver": "Spoofed"}).status_code == 403
    assert client.post("/api/analysis", headers=identity_headers()).json()["assessment"]["response_id"] == "resp_live"
    for stored in sessions.states.values():
        stored["next_analysis_at"] = 0
    async def unavailable(correlation_id):
        raise HostedAnalysisError("Live agent unavailable")
    monkeypatch.setattr(app.state, "online_analyze", unavailable)
    assert client.post("/api/analysis", headers=identity_headers()).status_code == 502
    result = client.get("/api/state", headers=identity_headers()).json()
    assert result["last_result"] is None
    assert result["assessment"] is None
    assert result["analysis_running"] is False
    assert client.post("/api/approval", headers=identity_headers(), json={"approver": "Spoofed"}).status_code == 409


def test_hosted_api_expired_approval_and_storage_conflict_fail_closed(hosted_api, monkeypatch):
    client, sessions = hosted_api
    headers = identity_headers()
    client.post("/api/analysis", headers=headers)
    approval = client.post("/api/approval", headers=headers, json={"approver": "Spoofed"}).json()
    state = next(iter(sessions.states.values()))
    state["handles"][approval["approval_id"]]["expires"] = 0
    assert client.post("/api/quarantine", headers=headers, json={"approval_id": approval["approval_id"]}).status_code == 403
    async def conflict(*args):
        raise HTTPException(409, "Demo state changed.")
    monkeypatch.setattr(sessions, "save", conflict)
    assert client.post("/api/reset", headers=headers).status_code == 409
    current = client.get("/api/state", headers=headers).json()
    assert all(item["status"] == "available" for item in current["inventory"]["positions"])


def test_hosted_answer_rejects_empty_partial_and_tool_only_output() -> None:
    for payload in [
        {"id": "resp_1", "status": "completed", "output": []},
        {"id": "resp_1", "status": "incomplete", "output": []},
        {"id": "resp_1", "status": "completed", "output": [{"type": "function_call"}]},
        {"status": "completed", "output": []},
    ]:
        with pytest.raises(HostedAnalysisError):
            parse_answer(payload, None)


def test_hosted_answer_rejects_partial_assistant_message() -> None:
    with pytest.raises(HostedAnalysisError):
        parse_answer({"id": "response", "status": "completed", "output": [
            {"type": "message", "role": "assistant", "status": "incomplete",
             "content": [{"type": "output_text", "text": "Partial decision"}]},
        ]}, None)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["timeout", "disconnect", "invalid-json", "invalid-shape", "credential"])
async def test_hosted_analysis_transport_and_credential_errors_are_sanitized(failure):
    async def token():
        if failure == "credential":
            raise RuntimeError("private credential error")
        return "test-credential"
    def respond(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("private timeout", request=request)
        if failure == "disconnect":
            raise httpx.ConnectError("private disconnect", request=request)
        if failure == "invalid-json":
            return httpx.Response(200, text="private malformed response")
        return httpx.Response(200, json=[])
    endpoint = "https://test.services.ai.azure.com/api/projects/demo/agents/recall/endpoint/protocols/openai/responses"
    with pytest.raises(HostedAnalysisError) as caught:
        await analyze(endpoint, "Assess recall", "request", token, transport=httpx.MockTransport(respond))
    assert "private" not in str(caught.value)
    if failure == "timeout":
        assert isinstance(caught.value, TimeoutError)


class StorageResponse(AsyncHttpResponse):
    def __init__(self, request, status, headers, payload=b""):
        super().__init__(request, None)
        self.status_code = status
        self.headers = httpx.Headers(headers)
        self.reason = "Test response"
        self.content_type = headers.get("content-type")
        self.payload = payload

    def body(self):
        return self.payload

    async def load_body(self):
        return None

    async def read(self):
        return self.payload

    async def close(self):
        return None

    def stream_download(self, pipeline, **kwargs):
        payload = self.payload
        response = self
        class Chunks:
            def __init__(self):
                self.response = response
                self.content_length = len(payload)

            def __aiter__(self):
                return self.chunks()

            async def chunks(self):
                yield payload
        return Chunks()


class StorageTransport(AsyncHttpTransport):
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []
        self.closed = False

    async def open(self):
        return None

    async def close(self):
        self.closed = True

    async def __aexit__(self, *args):
        await self.close()

    async def send(self, request, **kwargs):
        self.requests.append(request)
        status, headers, payload = next(self.responses)
        return StorageResponse(request, status, headers, payload)


@pytest.mark.asyncio
async def test_blob_sessions_real_sdk_conditional_requests_and_roundtrip(monkeypatch):
    from azure.storage.blob.aio import ContainerClient
    state = online_control.initial_state()
    payload = json.dumps(state).encode()
    transport = StorageTransport([
        (201, {"etag": '"first"'}, b""),
        (206, {"etag": '"first"', "content-length": str(len(payload)),
               "content-range": f"bytes 0-{len(payload) - 1}/{len(payload)}",
               "x-ms-blob-type": "BlockBlob", "content-type": "application/json"}, payload),
        (201, {"etag": '"second"'}, b""),
        (412, {"x-ms-error-code": "ConditionNotMet"}, b""),
        (409, {"x-ms-error-code": "BlobAlreadyExists"}, b""),
        (404, {"x-ms-error-code": "BlobNotFound"}, b""),
    ])
    scopes = []
    class Credential:
        async def get_token(self, *requested_scopes, **kwargs):
            scopes.extend(requested_scopes)
            return AccessToken("test-storage-token", 9999999999)
    from_url = ContainerClient.from_container_url
    def container_from_url(*args, **kwargs):
        return from_url(*args, transport=transport, **kwargs)
    monkeypatch.setattr(ContainerClient, "from_container_url", container_from_url)
    monkeypatch.setenv("CALDOVA_STATE_CONTAINER_URL", "https://demo.blob.core.windows.net/sessions")
    sessions = online_control.BlobSessions(Credential())
    try:
        assert await sessions.save("session", state, None) == '"first"'
        loaded, etag = await sessions.load("session")
        assert loaded == state
        assert etag == '"first"'
        assert await sessions.save("session", loaded, etag) == '"second"'
        for stale_etag in ['"first"', None]:
            with pytest.raises(HTTPException) as caught:
                await sessions.save("session", state, stale_etag)
            assert caught.value.status_code == 409
        missing, etag = await sessions.load("missing")
        assert etag is None
        assert missing["handles"] == {}
    finally:
        await sessions.close()
    assert transport.closed
    assert transport.requests[0].headers["If-None-Match"] == "*"
    assert transport.requests[2].headers["If-Match"] == '"first"'
    assert "https://storage.azure.com/.default" in scopes


@pytest.mark.asyncio
async def test_live_analysis_uses_async_identity_scope_without_network(monkeypatch):
    from unittest.mock import AsyncMock
    from azure.identity.aio import ManagedIdentityCredential
    async def fake_analyze(endpoint, prompt, correlation_id, token_provider):
        assert await token_provider() == "test-foundry-token"
        assert correlation_id == "correlation"
        return HostedAnswer("Synthetic test answer", "response", None)
    monkeypatch.setenv("CALDOVA_AGENT_ENDPOINT", "https://test.services.ai.azure.com/endpoint/protocols/openai/responses")
    monkeypatch.setattr(online_control, "analyze", fake_analyze)
    async with ManagedIdentityCredential(client_id="test-client") as credential:
        get_token = AsyncMock(return_value=AccessToken("test-foundry-token", 9999999999))
        monkeypatch.setattr(credential, "get_token", get_token)
        answer = await online_control.live_analysis(credential, "correlation")
        assert answer.response_id == "response"
        get_token.assert_awaited_once_with("https://ai.azure.com/.default")


@pytest.mark.asyncio
async def test_hosted_analysis_uses_real_output_and_isolated_requests() -> None:
    requests = []

    async def token() -> str:
        return "test-credential"

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={
            "id": f"resp_{len(requests)}", "status": "completed",
            "output": [{"type": "message", "role": "assistant", "content": [
                {"type": "output_text", "text": "2,196 units across 4 locations."}
            ]}],
        }, headers={"x-ms-request-id": "remote-request"})

    endpoint = "https://test.services.ai.azure.com/api/projects/demo/agents/recall/endpoint/protocols/openai/responses"
    for correlation_id in ["first-request", "second-request"]:
        answer = await analyze(endpoint, "Assess recall", correlation_id, token, transport=httpx.MockTransport(respond))
        assert answer.text == "2,196 units across 4 locations."
        assert answer.request_id == "remote-request"
        assert answer.response_id.startswith("resp_")
    assert requests[0].headers["x-ms-client-request-id"] == "first-request"
    assert requests[1].headers["x-ms-client-request-id"] == "second-request"
    assert all(b"conversation" not in request.content for request in requests)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 403, 429, 500])
async def test_hosted_analysis_sanitizes_upstream_failures(status: int) -> None:
    async def token() -> str:
        return "test-credential"

    endpoint = "https://test.services.ai.azure.com/api/projects/demo/agents/recall/endpoint/protocols/openai/responses"
    with pytest.raises(HostedAnalysisError) as caught:
        await analyze(endpoint, "Assess recall", "request", token, transport=httpx.MockTransport(
            lambda request: httpx.Response(status, text="sensitive upstream detail")
        ))
    assert "sensitive" not in str(caught.value)
    assert "test-credential" not in str(caught.value)


def test_control_tower_complete_approval_and_replay_flow() -> None:
    with TestClient(app) as client:
        client.post("/api/reset")

        state = client.get("/api/state")
        assert state.status_code == 200
        assert state.json()["inventory"]["total_units"] == 2196
        assert state.json()["inventory"]["locations"] == 4

        analysis = client.post("/api/analysis")
        assert analysis.status_code == 200
        analysis_body = analysis.json()
        assert [stage["status"] for stage in analysis_body["workflow"]] == [
            "complete",
            "complete",
            "complete",
            "complete",
        ]
        assert [call["tool"] for call in reversed(analysis_body["calls"])] == [
            "get_recall_notice",
            "locate_inventory",
            "get_supplier_status",
        ]
        assert analysis_body["last_result"]["status"] == "approval_required"

        denied = client.post("/api/quarantine", json={"approval_id": "missing-approval"})
        assert denied.status_code == 403

        approval = client.post(
            "/api/approval",
            json={"approver": "Asha Rao, Responsible Pharmacist"},
        )
        assert approval.status_code == 200
        approval_body = approval.json()
        assert "approval_token" not in repr(approval_body)

        first = client.post(
            "/api/quarantine",
            json={"approval_id": approval_body["approval_id"]},
        )
        assert first.status_code == 200
        assert first.json()["last_result"]["positions_changed"] == 4
        assert first.json()["last_result"]["idempotent_replay"] is False

        replay = client.post(
            "/api/quarantine",
            json={"approval_id": approval_body["approval_id"]},
        )
        assert replay.status_code == 200
        assert replay.json()["last_result"]["positions_changed"] == 0
        assert replay.json()["last_result"]["idempotent_replay"] is True
        assert "approval_token" not in repr(replay.json())


def test_control_tower_serves_operational_first_screen() -> None:
    with TestClient(app) as client:
        response = client.get("/")
        favicon = client.get("/favicon.ico")

    assert response.status_code == 200
    assert favicon.status_code == 204
    assert "Recall Control Tower" in response.text
    assert "ACTIVE RECALL" in response.text
    assert "Approve quarantine" in response.text
