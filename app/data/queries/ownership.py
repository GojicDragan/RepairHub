from sqlalchemy import select

from app.data.devices.model import Device


def owned_devices(owner_id):
    # Derselbe Eigentumsfilter gilt für Lesen und Schreiben, niemals nur für Listen.
    return select(Device).where(Device.owner_id == owner_id)
