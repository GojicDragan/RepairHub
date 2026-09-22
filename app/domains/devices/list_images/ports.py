from typing import Protocol

from app.domains.devices.dto import ImagePage


class Repository(Protocol):
    def owns(self, owner_id: int, parent_id: int) -> bool: ...
    def list(self, owner_id: int, parent_id: int, offset: int, limit: int) -> ImagePage: ...
