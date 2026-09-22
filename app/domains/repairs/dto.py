"""Reparaturdaten verlassen die Domäne ohne ORM- oder HTTP-Abhängigkeiten."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum


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
class PartPosition:
    id: int
    name: str
    unit_price: Decimal
    quantity: int
    total: Decimal = Decimal("0.00")


@dataclass(frozen=True)
class RepairDetails:
    repair: Repair
    steps: tuple[Step, ...]
    step_total: int
    step_offset: int
    hours: Decimal = Decimal("0.00")
    hourly_rate: Decimal = Decimal("0.00")
    parts: tuple[PartPosition, ...] = ()
    part_total: int = 0
    part_offset: int = 0
    labor_cost: Decimal = Decimal("0.00")
    parts_cost: Decimal = Decimal("0.00")
    total_cost: Decimal = Decimal("0.00")


class SystemReadAccess(Enum):
    """Explizite Leseberechtigung; niemals als Eigentümer für Schreibabläufe verwenden."""

    ALL_REPAIRS = "all_repairs"
