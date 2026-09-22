from sqlalchemy import func, select

from app.data.devices.model import Device
from app.data.queries.ownership import owned_repairs
from app.data.repairs.model import Repair
from app.data.repairs.queries import OwnershipQueries
from app.domains.repairs.dto import Repair as RepairData
from app.domains.repairs.dto import RepairPage
from app.extensions import db


class ListRepairsRepository(OwnershipQueries):
    def list(self, owner_id, device_id, offset, limit, snapshot):
        query = owned_repairs(owner_id)
        if device_id is not None:
            query = query.where(Repair.device_id == device_id)
        # Die obere ID fixiert den Listenbestand für spätere AJAX-Fenster.
        # Neue Fälle verschieben so keine Offsets; Feldänderungen bleiben sichtbar.
        # Dies ist kein Datenbank-Snapshot; Löschungen sind hier nicht vorgesehen.
        if snapshot is None:
            snapshot = db.session.scalar(select(func.max(query.subquery().c.id))) or 0
        query = query.where(Repair.id <= snapshot)
        total = db.session.scalar(select(func.count()).select_from(query.subquery()))
        # Gerätenamen zusammen mit dem Fenster laden, keine einzelne Folgeabfrage pro Fall.
        rows = db.session.execute(
            query.add_columns(Device.name).order_by(Repair.id.desc()).offset(offset).limit(limit)
        )
        items = tuple(
            RepairData(row.id, row.device_id, name, row.description, row.status, row.created_at)
            for row, name in rows
        )
        return RepairPage(items, total, offset, snapshot)
