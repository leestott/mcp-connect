import sys
from pathlib import Path

from fastapi.testclient import TestClient


SOURCE = Path(__file__).parents[1] / "src"
sys.path.insert(0, str(SOURCE))

from control_tower_api import app  # noqa: E402


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
