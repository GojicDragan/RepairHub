from dataclasses import dataclass

from app.domains.devices.dto import DeviceValues


@dataclass(frozen=True)
class Command:
    owner_id: int
    device_id: int
    values: DeviceValues
