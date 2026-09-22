from sqlalchemy import func

from app.data.queries.ownership import owned_repairs
from app.data.repairs.model import Repair
from app.extensions import db


class GetStatusOverviewRepository:
    def count_by_status(self, owner_id: int):
        # Die gemeinsame Eigentumsabfrage begrenzt schon die Aggregation.
        # Keine Falldetails laden und keine Begrenzung durch das virtuelle Fenster.
        statement = (
            owned_repairs(owner_id)
            .with_only_columns(Repair.status, func.count())
            .group_by(Repair.status)
        )
        return dict(db.session.execute(statement).all())
