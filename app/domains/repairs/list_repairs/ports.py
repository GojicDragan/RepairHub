from typing import Protocol

from app.domains.repairs.dto import RepairPage


class Repository(Protocol):
    def owns_device(self, owner_id: int, device_id: int) -> bool: ...
    def list(
        self, owner_id: int, device_id: int | None, offset: int, limit: int, snapshot: int | None
    ) -> RepairPage: ...
