from datetime import datetime
from typing import Protocol

from app.domains.repairs.dto import Repair


class Repository(Protocol):
    def owns_device(self, owner_id: int, device_id: int) -> bool: ...
    def create(
        self, owner_id: int, device_id: int, description: str, status: str, created_at: datetime
    ) -> Repair | None: ...
