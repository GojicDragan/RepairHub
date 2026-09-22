from decimal import Decimal
from typing import Protocol

from app.domains.parts.dto import Part


class Repository(Protocol):
    def owns_part(self, owner_id: int, repair_id: int, part_id: int) -> bool: ...
    def update(
        self,
        owner_id: int,
        repair_id: int,
        part_id: int,
        name: str,
        unit_price: Decimal,
        quantity: int,
    ) -> Part | None: ...
