from app.domains.users.dto import GeneratedApiKey

from .dto import Command
from .ports import Gateway


class CreateApiKey:
    def __init__(self, gateway: Gateway):
        self._gateway = gateway

    def execute(self, command: Command) -> GeneratedApiKey | None:
        return self._gateway.create(command)
