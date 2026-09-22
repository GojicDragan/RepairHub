from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    owner_id: int
    repair_id: int
    step_id: int
    description: str
    completed: bool
