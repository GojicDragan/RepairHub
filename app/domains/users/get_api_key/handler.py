from app.domains.users.dto import ApiKeyStatus

from .dto import Command
from .ports import Gateway


class GetApiKey:
    def __init__(self, gateway: Gateway):
        self._gateway = gateway

    def execute(self, command: Command) -> ApiKeyStatus:
        return self._gateway.status(command)
