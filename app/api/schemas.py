"""Explizites JSON-Schema: keine ORM-Objekte oder internen Identitätsdaten ausgeben."""

from app.domains.repairs.dto import Repair, RepairDetails


def repair_document(detail: RepairDetails) -> dict:
    repair = detail.repair
    return {
        "id": repair.id,
        "device": {"id": repair.device_id, "name": repair.device_name},
        "description": repair.description,
        "status": repair.status,
        "created_at": repair.created_at.isoformat(),
        "steps": [
            {"id": step.id, "description": step.description, "completed": step.completed}
            for step in detail.steps
        ],
        "parts": [
            {
                "id": part.id,
                "name": part.name,
                "quantity": part.quantity,
                "unit_price": format(part.unit_price, ".2f"),
                "total": format(part.total, ".2f"),
            }
            for part in detail.parts
        ],
        "work": {
            "hours": format(detail.hours, ".2f"),
            "hourly_rate": format(detail.hourly_rate, ".2f"),
        },
        "costs": {
            "currency": "CHF",
            "labor": format(detail.labor_cost, ".2f"),
            "parts": format(detail.parts_cost, ".2f"),
            "total": format(detail.total_cost, ".2f"),
        },
    }


def repair_summary(repair: Repair) -> dict:
    return {
        "id": repair.id,
        "device": {"id": repair.device_id, "name": repair.device_name},
        "description": repair.description,
        "status": repair.status,
        "created_at": repair.created_at.isoformat(),
    }
