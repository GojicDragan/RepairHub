from typing import Protocol

from app.domains.repairs.dto import RepairDetails, SystemReadAccess


class Repository(Protocol):
    def get(
        self, owner_id: int | SystemReadAccess, repair_id: int, offset: int, limit: int | None
    ) -> RepairDetails | None: ...
