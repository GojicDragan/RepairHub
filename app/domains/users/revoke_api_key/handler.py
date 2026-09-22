from .dto import Command
from .ports import Gateway


class RevokeApiKey:
    def __init__(self, gateway: Gateway):
        self._gateway = gateway

    def execute(self, command: Command) -> None:
        return self._gateway.revoke(command)
