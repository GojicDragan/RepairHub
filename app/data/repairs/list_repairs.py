from sqlalchemy import func, or_, select

from app.data.devices.model import Device
from app.data.repairs.model import Repair
from app.data.repairs.queries import OwnershipQueries
from app.data.repairs.read_access import readable_repairs
from app.domains.repairs.dto import Repair as RepairData
from app.domains.repairs.dto import RepairPage
from app.extensions import db


class ListRepairsRepository(OwnershipQueries):
    def list(self, owner_id, device_id, offset, limit, snapshot, search="", status_filter=""):
        query = readable_repairs(owner_id)
        if device_id is not None:
            query = query.where(Repair.device_id == device_id)
        if status_filter:
            query = query.where(Repair.status == status_filter)
        # Jedes Wort muss in mindestens einem Feld vorkommen. Wildcards werden
        # als Text behandelt; Eigentum, Trefferzahl und Fenster nutzen dieselbe Abfrage.
        for term in search.split():
            query = query.where(
                or_(
                    *(
                        field.icontains(term, autoescape=True)
                        for field in (
                            Repair.description,
                            Device.name,
                            Device.manufacturer,
                            Device.model,
                        )
                    )
                )
            )
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
