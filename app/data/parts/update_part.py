from app.data.parts.model import PartItem
from app.data.parts.queries import OwnershipQueries, part_dto
from app.data.queries.ownership import owned_parts
from app.data.transactions import transaction
from app.extensions import db


class UpdatePartRepository(OwnershipQueries):
    def update(self, owner_id, repair_id, part_id, name, unit_price, quantity):
        with transaction():
            # Eigentum unmittelbar vor der Änderung prüfen und die Bezugszeile sperren.
            row = db.session.scalar(
                owned_parts(owner_id, repair_id)
                .where(PartItem.id == part_id)
                .with_for_update(of=PartItem)
            )
            if row is None:
                return None
            row.name, row.unit_price, row.quantity = name, unit_price, quantity
            result = part_dto(row)
        return result
