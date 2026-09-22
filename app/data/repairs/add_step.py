from app.data.queries.ownership import owned_repairs
from app.data.repairs.model import Repair, RepairStep
from app.data.repairs.queries import OwnershipQueries, step_dto
from app.data.transactions import transaction
from app.extensions import db


class AddStepRepository(OwnershipQueries):
    def add(self, owner_id, repair_id, description, completed):
        with transaction():
            # Auch ein neuer Schritt benötigt einen eigenen Fall. Die Elternzeile
            # bleibt während der Anlage gesperrt und damit als Bezug erhalten.
            parent = db.session.scalar(
                owned_repairs(owner_id).where(Repair.id == repair_id).with_for_update(of=Repair)
            )
            if parent is None:
                return None
            row = RepairStep(repair_id=parent.id, description=description, completed=completed)
            db.session.add(row)
            db.session.flush()
            result = step_dto(row)
        return result
