from app.data.queries.ownership import owned_steps
from app.data.repairs.model import RepairStep
from app.data.repairs.queries import OwnershipQueries, step_dto
from app.data.transactions import transaction
from app.extensions import db


class UpdateStepRepository(OwnershipQueries):
    def update(self, owner_id, repair_id, step_id, description, completed):
        with transaction():
            row = db.session.scalar(
                owned_steps(owner_id, repair_id)
                .where(RepairStep.id == step_id)
                .with_for_update(of=RepairStep)
            )
            if row is None:
                return None
            # Expliziter Zielzustand statt Toggle: Wiederholte Requests kehren ihn nicht um.
            row.description, row.completed = description, completed
            result = step_dto(row)
        return result
