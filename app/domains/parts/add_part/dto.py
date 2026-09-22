from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    owner_id: int
    repair_id: int
    name: str
    unit_price: str
    quantity: str
