from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    owner_id: int
    parent_id: int
    image_id: str
