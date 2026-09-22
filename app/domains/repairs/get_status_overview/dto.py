from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    owner_id: int


@dataclass(frozen=True)
class StatusOverview:
    open: int
    in_progress: int
    completed: int
