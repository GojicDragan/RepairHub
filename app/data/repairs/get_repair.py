from sqlalchemy import func, select

from app.data.parts.model import PartItem
from app.data.repairs.model import Repair, RepairStep
from app.data.repairs.queries import repair_dto, step_dto
from app.data.repairs.read_access import readable_parts, readable_repairs, readable_steps
from app.domains.repairs.dto import PartPosition, RepairDetails
from app.extensions import db


class GetRepairRepository:
    def get(self, owner_id, repair_id, offset, limit):
        row = db.session.scalar(readable_repairs(owner_id).where(Repair.id == repair_id))
        if row is None:
            return None
        query = readable_steps(owner_id, repair_id)
        total = db.session.scalar(select(func.count()).select_from(query.subquery()))
        steps = db.session.scalars(query.order_by(RepairStep.id).offset(offset).limit(limit))
        # Schritte hier materialisieren: Die Webschicht erhält weder eine
        # laufende Abfrage noch ORM-Objekte mit nachladbaren Beziehungen.
        return RepairDetails(
            repair_dto(row),
            tuple(step_dto(step) for step in steps),
            total,
            offset,
            hours=row.hours,
            hourly_rate=row.hourly_rate,
            parts=tuple(
                PartPosition(p.id, p.name, p.unit_price, p.quantity)
                for p in db.session.scalars(
                    readable_parts(owner_id, repair_id).order_by(PartItem.id)
                )
            ),
        )
