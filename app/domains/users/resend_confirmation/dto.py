from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    email: str
