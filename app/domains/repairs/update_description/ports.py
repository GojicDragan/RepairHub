from typing import Protocol

from app.domains.repairs.dto import Repair


class Repository(Protocol):
    def owns_repair(self, owner_id: int, repair_id: int) -> bool: ...
    def update(self, owner_id: int, repair_id: int, description: str) -> Repair | None: ...
