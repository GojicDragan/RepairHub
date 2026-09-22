from sqlalchemy import func, select

from app.data.devices.model import Device
from app.data.devices.queries import device_dto
from app.data.queries.ownership import owned_devices
from app.domains.devices.dto import DevicePage
from app.extensions import db


class ListDevicesRepository:
    def list(self, owner_id, offset, limit, snapshot):
        if snapshot is None:
            snapshot = (
                db.session.scalar(select(func.max(Device.id)).where(Device.owner_id == owner_id))
                or 0
            )
        # Aufsteigende IDs und eine obere Grenze halten Positionen bei neuen Geräten stabil.
        # T06 löscht keine Geräte; Änderungen an Textfeldern ändern die Reihenfolge nicht.
        statement = owned_devices(owner_id).where(Device.id <= snapshot)
        total = db.session.scalar(select(func.count()).select_from(statement.subquery()))
        rows = db.session.scalars(statement.order_by(Device.id).offset(offset).limit(limit))
        return DevicePage(tuple(device_dto(row) for row in rows), total, snapshot, offset)
