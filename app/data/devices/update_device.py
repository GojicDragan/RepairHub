from app.data.devices.get_device import GetDeviceRepository
from app.data.devices.model import Device
from app.data.devices.queries import device_dto
from app.data.queries.ownership import owned_devices
from app.data.transactions import transaction
from app.extensions import db


class UpdateDeviceRepository(GetDeviceRepository):
    def update(self, owner_id, device_id, values):
        with transaction():
            # Zeile bis zum Commit sperren, damit parallele Änderungen nicht
            # zwischen Laden und Schreiben in dieselbe Operation eingreifen.
            row = db.session.scalar(
                owned_devices(owner_id).where(Device.id == device_id).with_for_update()
            )
            if row is None:
                return None
            row.name, row.manufacturer, row.model = values.name, values.manufacturer, values.model
            result = device_dto(row)
        return result
