"""Reparaturdaten verlassen die Domäne ohne ORM- oder HTTP-Abhängigkeiten."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Repair:
    id: int
    device_id: int
    device_name: str
    description: str
    status: str
    created_at: datetime


@dataclass(frozen=True)
class Step:
    id: int
    repair_id: int
    description: str
    completed: bool


@dataclass(frozen=True)
class RepairPage:
    items: tuple[Repair, ...]
    total: int
    offset: int
    snapshot: int


@dataclass(frozen=True)
class RepairDetails:
    repair: Repair
    steps: tuple[Step, ...]
    step_total: int
    step_offset: int
