from app.domains.users.dto import UserResult

from .dto import Command
from .ports import Gateway


class ConfirmEmail:
    """Einstieg des Anwendungsfalls; technische Identitätsarbeit an den Port delegieren."""

    def __init__(self, gateway: Gateway):
        self._gateway = gateway

    def execute(self, command: Command) -> UserResult:
        return self._gateway.confirm(command)
