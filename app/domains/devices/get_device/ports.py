from typing import Protocol

from app.domains.devices.dto import Device


class Repository(Protocol):
    def get(self, owner_id: int, device_id: int) -> Device | None: ...
