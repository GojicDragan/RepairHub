from typing import Protocol

from app.domains.repairs.dto import Step


class Repository(Protocol):
    def owns_repair(self, owner_id: int, repair_id: int) -> bool: ...
    def add(
        self, owner_id: int, repair_id: int, description: str, completed: bool
    ) -> Step | None: ...
