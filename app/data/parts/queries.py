from app.data.parts.model import PartItem
from app.data.queries.ownership import owned_parts, owned_repairs
from app.data.repairs.model import Repair
from app.domains.parts.dto import Part
from app.extensions import db


def part_dto(row):
    return Part(row.id, row.repair_id, row.name, row.unit_price, row.quantity)


class OwnershipQueries:
    def owns_repair(self, owner_id, repair_id):
        return db.session.scalar(owned_repairs(owner_id).where(Repair.id == repair_id)) is not None

    def owns_part(self, owner_id, repair_id, part_id):
        return (
            db.session.scalar(owned_parts(owner_id, repair_id).where(PartItem.id == part_id))
            is not None
        )
