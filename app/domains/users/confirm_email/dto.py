from dataclasses import dataclass, field


@dataclass(frozen=True)
class Command:
    token: str = field(repr=False)
