from typing import Protocol

from .dto import Command


class Gateway(Protocol):
    def revoke(self, command: Command) -> None: ...
