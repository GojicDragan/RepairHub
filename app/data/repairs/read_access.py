"""Eigentumsgebundene Abfragen mit expliziter Ausnahme für den System-Lesezugang."""

from sqlalchemy import select

from app.data.devices.model import Device
from app.data.parts.model import PartItem
from app.data.queries.ownership import owned_parts, owned_repairs, owned_steps
from app.data.repairs.model import Repair, RepairStep
from app.domains.repairs.dto import SystemReadAccess


def readable_repairs(access):
    if access is SystemReadAccess.ALL_REPAIRS:
        return select(Repair).join(Device, Repair.device_id == Device.id)
    return owned_repairs(access)


def readable_steps(access, repair_id):
    if access is SystemReadAccess.ALL_REPAIRS:
        return select(RepairStep).where(RepairStep.repair_id == repair_id)
    return owned_steps(access, repair_id)


def readable_parts(access, repair_id):
    if access is SystemReadAccess.ALL_REPAIRS:
        return select(PartItem).where(PartItem.repair_id == repair_id)
    return owned_parts(access, repair_id)
