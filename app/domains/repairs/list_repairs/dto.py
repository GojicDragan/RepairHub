from dataclasses import dataclass

from app.domains.repairs.dto import SystemReadAccess


@dataclass(frozen=True)
class Command:
    owner_id: int | SystemReadAccess
    device_id: int | None = None
    offset: int = 0
    limit: int = 20
    snapshot: int | None = None
    search: str = ""
    status_filter: str = ""
