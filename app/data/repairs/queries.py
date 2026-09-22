"""Gemeinsame Eigentumsabfragen und explizite Kopien in frameworkfreie DTOs."""

from app.data.devices.model import Device
from app.data.queries.ownership import owned_devices, owned_repairs, owned_steps
from app.data.repairs.model import Repair, RepairStep
from app.domains.repairs.dto import Repair as RepairData
from app.domains.repairs.dto import Step
from app.extensions import db


def repair_dto(row):
    device_name = db.session.scalar(owned_devices_for_repair(row))
    return RepairData(
        row.id, row.device_id, device_name, row.description, row.status, row.created_at
    )


def owned_devices_for_repair(row):
    # Der Aufrufer hat den Fall bereits mit geprüftem Lesezugriff geladen
    # (Eigentümer oder Systemschlüssel); hier wird nur der Gerätename ergänzt.
    from sqlalchemy import select

    return select(Device.name).where(Device.id == row.device_id)


def step_dto(row):
    return Step(row.id, row.repair_id, row.description, row.completed)


class OwnershipQueries:
    def owns_device(self, owner_id, device_id):
        return db.session.scalar(owned_devices(owner_id).where(Device.id == device_id)) is not None

    def owns_repair(self, owner_id, repair_id):
        return db.session.scalar(owned_repairs(owner_id).where(Repair.id == repair_id)) is not None

    def owns_step(self, owner_id, repair_id, step_id):
        return (
            db.session.scalar(owned_steps(owner_id, repair_id).where(RepairStep.id == step_id))
            is not None
        )
