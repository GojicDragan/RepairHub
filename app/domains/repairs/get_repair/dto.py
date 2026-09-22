from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    owner_id: int
    repair_id: int
    offset: int = 0
