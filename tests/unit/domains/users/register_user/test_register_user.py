"""Anwendungsfallvertrag ohne Flask, Datenbank oder echten Identitätsanbieter prüfen."""

import pytest

from app.domains.users.dto import UserResult
from app.domains.users.register_user.dto import Command
from app.domains.users.register_user.handler import RegisterUser


@pytest.mark.parametrize(
    "result",
    [
        UserResult(),
        UserResult("invalid", (("identity", ("Invalid input",)),)),
        UserResult("unavailable"),
    ],
)
def test_injected_gateway_receives_command_and_returns_result(result):
    received = []

    class FakeGateway:
        def register(self, command):
            received.append(command)
            return result

    command = Command("Lea", "lea@example.org", "secret-password", "secret-password")
    assert RegisterUser(FakeGateway()).execute(command) is result
    assert received == [command]
    assert "secret-password" not in repr(command)
    assert "secret-token" not in repr(command)
