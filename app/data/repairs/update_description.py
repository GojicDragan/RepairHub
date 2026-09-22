from app.data.queries.ownership import owned_repairs
from app.data.repairs.model import Repair
from app.data.repairs.queries import OwnershipQueries, repair_dto
from app.data.transactions import transaction
from app.extensions import db


class UpdateDescriptionRepository(OwnershipQueries):
    def update(self, owner_id, repair_id, description):
        with transaction():
            # Eigentumsfilter auch beim Schreiben; Sperre gilt bis zum Commit.
            row = db.session.scalar(
                owned_repairs(owner_id).where(Repair.id == repair_id).with_for_update(of=Repair)
            )
            if row is None:
                return None
            row.description = description
            result = repair_dto(row)
        return result
