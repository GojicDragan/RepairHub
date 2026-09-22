from sqlalchemy import func, or_, select

from app.data.devices.model import Device
from app.data.devices.queries import device_dto
from app.data.queries.ownership import owned_devices
from app.domains.devices.dto import DevicePage
from app.extensions import db


class ListDevicesRepository:
    def list(self, owner_id, offset, limit, snapshot, search=""):
        statement = owned_devices(owner_id)
        # Alle Suchteile müssen vorkommen, dürfen aber verschiedene Gerätefelder treffen.
        # Dieselbe Eigentums-/Suchabfrage gilt für Maximum, Trefferzahl und jedes Fenster.
        for term in search.split():
            statement = statement.where(
                or_(
                    *(
                        field.icontains(term, autoescape=True)
                        for field in (Device.name, Device.manufacturer, Device.model)
                    )
                )
            )
        if snapshot is None:
            snapshot = db.session.scalar(select(func.max(statement.subquery().c.id))) or 0
        # Neue Geräte verändern laufende Fenster nicht; Textänderungen können Treffer ändern.
        statement = statement.where(Device.id <= snapshot)
        total = db.session.scalar(select(func.count()).select_from(statement.subquery()))
        rows = db.session.scalars(statement.order_by(Device.id).offset(offset).limit(limit))
        return DevicePage(tuple(device_dto(row) for row in rows), total, snapshot, offset)
