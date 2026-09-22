from typing import Protocol

from app.domains.devices.dto import DevicePage


class Repository(Protocol):
    def list(
        self, owner_id: int, offset: int, limit: int, snapshot: int | None, search: str = ""
    ) -> DevicePage: ...
