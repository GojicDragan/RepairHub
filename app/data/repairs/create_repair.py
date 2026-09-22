from app.data.devices.model import Device
from app.data.queries.ownership import owned_devices
from app.data.repairs.model import Repair
from app.data.repairs.queries import OwnershipQueries, repair_dto
from app.data.transactions import transaction
from app.extensions import db


class CreateRepairRepository(OwnershipQueries):
    def create(self, owner_id, device_id, description, status, created_at):
        with transaction():
            # Gerät erneut eigentumsgebunden laden und bis zum Commit sperren;
            # die Vorprüfung des Handlers allein autorisiert keinen späteren INSERT.
            parent = db.session.scalar(
                owned_devices(owner_id).where(Device.id == device_id).with_for_update()
            )
            if parent is None:
                return None
            row = Repair(
                device_id=parent.id, description=description, status=status, created_at=created_at
            )
            db.session.add(row)
            db.session.flush()
            result = repair_dto(row)
        return result
