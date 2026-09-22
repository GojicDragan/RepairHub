from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    owner_id: int
    device_id: int
