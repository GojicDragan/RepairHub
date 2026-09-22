from dataclasses import dataclass

from app.domains.repairs.dto import SystemReadAccess


@dataclass(frozen=True)
class Command:
    owner_id: int | SystemReadAccess
    repair_id: int
    offset: int = 0
    part_offset: int = 0
    complete: bool = False
