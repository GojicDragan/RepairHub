from typing import Protocol

from app.domains.devices.dto import Device, DeviceValues


class Repository(Protocol):
    def create(self, owner_id: int, values: DeviceValues) -> Device: ...
