from app.domains.users.dto import UserIdentity

from .dto import Command
from .ports import Gateway


class AuthenticateApiKey:
    def __init__(self, gateway: Gateway):
        self._gateway = gateway

    def execute(self, command: Command) -> UserIdentity | None:
        return self._gateway.authenticate(command)
