from typing import Protocol

from app.domains.users.dto import SystemApiIdentity, UserIdentity

from .dto import Command


class Gateway(Protocol):
    def authenticate(self, command: Command) -> UserIdentity | SystemApiIdentity | None: ...
