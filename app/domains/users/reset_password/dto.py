from dataclasses import dataclass, field


@dataclass(frozen=True)
class Command:
    token: str = field(repr=False)
    password: str = field(repr=False)
    password_confirm: str = field(repr=False)
