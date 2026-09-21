from dataclasses import dataclass, field


@dataclass(frozen=True)
class Command:
    identity: str
    password: str = field(repr=False)
    remember: bool = False
