from app.data.queries.ownership import owned_repairs
from app.data.repairs.model import Repair
from app.data.repairs.queries import OwnershipQueries, repair_dto
from app.data.transactions import transaction
from app.extensions import db


class UpdateWorkRepository(OwnershipQueries):
    def update(self, owner_id, repair_id, hours, hourly_rate):
        with transaction():
            row = db.session.scalar(
                owned_repairs(owner_id).where(Repair.id == repair_id).with_for_update(of=Repair)
            )
            if row is None:
                return None
            row.hours, row.hourly_rate = hours, hourly_rate
            result = repair_dto(row)
        return result
