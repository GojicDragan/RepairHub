from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    owner_id: int
    repair_id: int
    hours: str
    hourly_rate: str
