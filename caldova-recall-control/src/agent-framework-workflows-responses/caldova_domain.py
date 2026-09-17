from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any


@dataclass
class InventoryPosition:
    location: str
    location_type: str
    batch_id: str
    units: int
    status: str = "available"


PRODUCTS = {
    "B-2408-AX7": {
        "product": "Caldova Relief 20 mg tablets",
        "gtin": "05012345001987",
        "supplier": "Northstar Therapeutics",
        "reason": "Temperature excursion reported during inbound transit",
    }
}

INITIAL_INVENTORY = [
    InventoryPosition("Bengaluru DC", "distribution_center", "B-2408-AX7", 1240),
    InventoryPosition("Mysuru Store 014", "retail_store", "B-2408-AX7", 84),
    InventoryPosition("Bengaluru Store 031", "retail_store", "B-2408-AX7", 112),
    InventoryPosition("Chennai DC", "distribution_center", "B-2408-AX7", 760),
]


class RecallStore:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> dict[str, Any]:
        self.inventory = [InventoryPosition(**asdict(item)) for item in INITIAL_INVENTORY]
        self.approvals: dict[str, dict[str, str]] = {}
        self.audit_log: list[dict[str, Any]] = []
        return {"status": "reset", "positions": len(self.inventory)}

    def get_recall_notice(self, batch_id: str) -> dict[str, Any]:
        product = PRODUCTS.get(batch_id)
        if product is None:
            return {"found": False, "batch_id": batch_id}
        return {"found": True, "batch_id": batch_id, **product, "risk_tier": "high"}

    def locate_inventory(self, batch_id: str) -> dict[str, Any]:
        positions = [asdict(item) for item in self.inventory if item.batch_id == batch_id]
        return {
            "batch_id": batch_id,
            "positions": positions,
            "total_units": sum(item["units"] for item in positions),
            "locations": len(positions),
        }

    def get_supplier_status(self, batch_id: str) -> dict[str, Any]:
        if batch_id not in PRODUCTS:
            return {"found": False, "batch_id": batch_id}
        return {
            "found": True,
            "batch_id": batch_id,
            "supplier_acknowledged": True,
            "replacement_eta_hours": 36,
            "credit_note_status": "drafted",
        }

    def request_approval(self, batch_id: str, approver: str) -> dict[str, str]:
        if batch_id not in PRODUCTS:
            raise ValueError(f"Unknown batch: {batch_id}")
        token = sha256(f"{batch_id}:{approver}:caldova-demo".encode()).hexdigest()[:16]
        self.approvals[token] = {"batch_id": batch_id, "approver": approver}
        self._audit(
            "approval_issued",
            batch_id,
            {"approver": approver, "approval_id": sha256(token.encode()).hexdigest()[:12]},
        )
        return {"status": "approved", "batch_id": batch_id, "approval_token": token}

    def quarantine_batch(self, batch_id: str, approval_token: str) -> dict[str, Any]:
        approval = self.approvals.get(approval_token)
        if approval is None or approval["batch_id"] != batch_id:
            raise PermissionError("A valid batch-specific approval token is required")

        changed = 0
        units = 0
        for item in self.inventory:
            if item.batch_id == batch_id:
                units += item.units
                if item.status != "quarantined":
                    item.status = "quarantined"
                    changed += 1

        outcome = {
            "status": "quarantined",
            "batch_id": batch_id,
            "positions_changed": changed,
            "units_quarantined": units,
            "idempotent_replay": changed == 0,
        }
        self._audit("batch_quarantined", batch_id, outcome)
        return outcome

    def audit_events(self) -> list[dict[str, Any]]:
        return list(self.audit_log)

    def _audit(self, event: str, batch_id: str, details: dict[str, Any]) -> None:
        self.audit_log.append(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "event": event,
                "batch_id": batch_id,
                "details": details,
            }
        )


STORE = RecallStore()