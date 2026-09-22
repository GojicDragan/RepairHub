from typing import Protocol

from app.domains.repairs.dto import RepairDetails


class Repository(Protocol):
    def get(
        self, owner_id: int, repair_id: int, offset: int, limit: int
    ) -> RepairDetails | None: ...
