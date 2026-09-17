import sys
from pathlib import Path

import pytest


SOURCE = Path(__file__).parents[1] / "src" / "agent-framework-workflows-responses"
sys.path.insert(0, str(SOURCE))

from caldova_domain import RecallStore  # noqa: E402


def test_quarantine_requires_batch_specific_approval() -> None:
    store = RecallStore()

    with pytest.raises(PermissionError):
        store.quarantine_batch("B-2408-AX7", "not-approved")


def test_quarantine_is_approved_and_idempotent() -> None:
    store = RecallStore()
    approval = store.request_approval("B-2408-AX7", "Asha Rao, Responsible Pharmacist")

    first = store.quarantine_batch("B-2408-AX7", approval["approval_token"])
    replay = store.quarantine_batch("B-2408-AX7", approval["approval_token"])

    assert first == {
        "status": "quarantined",
        "batch_id": "B-2408-AX7",
        "positions_changed": 4,
        "units_quarantined": 2196,
        "idempotent_replay": False,
    }
    assert replay["positions_changed"] == 0
    assert replay["idempotent_replay"] is True


def test_audit_events_do_not_expose_approval_credentials() -> None:
    store = RecallStore()
    approval = store.request_approval("B-2408-AX7", "Asha Rao, Responsible Pharmacist")

    serialized_events = repr(store.audit_events())

    assert approval["approval_token"] not in serialized_events
    assert "approval_token" not in serialized_events
    assert "approval_id" in serialized_events