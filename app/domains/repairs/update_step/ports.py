from typing import Protocol

from app.domains.repairs.dto import Step


class Repository(Protocol):
    def owns_step(self, owner_id: int, repair_id: int, step_id: int) -> bool: ...
    def update(
        self, owner_id: int, repair_id: int, step_id: int, description: str, completed: bool
    ) -> Step | None: ...
