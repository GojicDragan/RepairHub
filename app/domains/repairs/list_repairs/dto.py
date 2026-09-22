from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    owner_id: int
    device_id: int | None = None
    offset: int = 0
    limit: int = 20
    snapshot: int | None = None
