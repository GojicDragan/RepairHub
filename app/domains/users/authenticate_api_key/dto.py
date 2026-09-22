from dataclasses import dataclass, field


@dataclass(frozen=True)
class Command:
    key: str = field(repr=False)
