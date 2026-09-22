from typing import Protocol

from app.domains.users.dto import ApiKeyStatus

from .dto import Command


class Gateway(Protocol):
    def status(self, command: Command) -> ApiKeyStatus: ...
