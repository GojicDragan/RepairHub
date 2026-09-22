from app.data.devices.model import Device
from app.data.devices.queries import device_dto
from app.data.queries.ownership import owned_devices
from app.extensions import db


class GetDeviceRepository:
    def get(self, owner_id, device_id):
        row = db.session.scalar(owned_devices(owner_id).where(Device.id == device_id))
        return device_dto(row) if row else None
