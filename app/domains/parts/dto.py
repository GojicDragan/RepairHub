from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Part:
    id: int
    repair_id: int
    name: str
    unit_price: Decimal
    quantity: int
    total: Decimal = Decimal("0.00")
