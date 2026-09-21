from typing import Protocol

from app.domains.users.dto import UserResult

from .dto import Command


class Gateway(Protocol):
    def reset(self, command: Command) -> UserResult: ...
