from sqlalchemy import select

from app.data.devices.model import Device


def owned_devices(owner_id):
    # Derselbe Eigentumsfilter gilt für Lesen und Schreiben, niemals nur für Listen.
    return select(Device).where(Device.owner_id == owner_id)


def owned_repairs(owner_id):
    from app.data.repairs.model import Repair

    return (
        select(Repair)
        .join(Device, Repair.device_id == Device.id)
        .where(Device.owner_id == owner_id)
    )


def owned_steps(owner_id, repair_id):
    from app.data.repairs.model import Repair, RepairStep

    # Beide IDs prüfen: Ein eigener Schritt aus einem anderen Fall gehört nicht zum Ziel.
    return (
        select(RepairStep)
        .join(Repair, RepairStep.repair_id == Repair.id)
        .join(Device, Repair.device_id == Device.id)
        .where(Device.owner_id == owner_id, Repair.id == repair_id)
    )


def owned_parts(owner_id, repair_id):
    from app.data.parts.model import PartItem
    from app.data.repairs.model import Repair

    return (
        select(PartItem)
        .join(Repair, PartItem.repair_id == Repair.id)
        .join(Device, Repair.device_id == Device.id)
        .where(Device.owner_id == owner_id, Repair.id == repair_id)
    )
