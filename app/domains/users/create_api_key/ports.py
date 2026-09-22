from typing import Protocol

from app.domains.users.dto import GeneratedApiKey

from .dto import Command


class Gateway(Protocol):
    def create(self, command: Command) -> GeneratedApiKey | None: ...
