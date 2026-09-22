from app.data.devices.model import Device
from app.data.devices.queries import device_dto
from app.data.transactions import transaction
from app.extensions import db


class RegisterDeviceRepository:
    def create(self, owner_id, values):
        with transaction():
            row = Device(
                owner_id=owner_id,
                name=values.name,
                manufacturer=values.manufacturer,
                model=values.model,
            )
            db.session.add(row)
            db.session.flush()
            result = device_dto(row)
        return result
