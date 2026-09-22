from typing import Protocol

from app.domains.devices.dto import Device, DeviceValues


class Repository(Protocol):
    def get(self, owner_id: int, device_id: int) -> Device | None: ...
    def update(self, owner_id: int, device_id: int, values: DeviceValues) -> Device | None: ...
