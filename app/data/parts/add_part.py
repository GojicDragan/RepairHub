from app.data.parts.model import PartItem
from app.data.parts.queries import OwnershipQueries, part_dto
from app.data.queries.ownership import owned_repairs
from app.data.repairs.model import Repair
from app.data.transactions import transaction
from app.extensions import db


class AddPartRepository(OwnershipQueries):
    def add(self, owner_id, repair_id, name, unit_price, quantity):
        with transaction():
            # Eigentum unmittelbar vor der Änderung prüfen und die Bezugszeile sperren.
            parent = db.session.scalar(
                owned_repairs(owner_id).where(Repair.id == repair_id).with_for_update(of=Repair)
            )
            if parent is None:
                return None
            row = PartItem(repair_id=parent.id, name=name, unit_price=unit_price, quantity=quantity)
            db.session.add(row)
            db.session.flush()
            result = part_dto(row)
        return result
