"""Anwendungsfallvertrag ohne Flask, Datenbank oder echten Identitätsanbieter prüfen."""

import pytest

from app.domains.users.dto import UserResult
from app.domains.users.reset_password.dto import Command
from app.domains.users.reset_password.handler import ResetPassword


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
        def reset(self, command):
            received.append(command)
            return result

    command = Command("secret-token", "secret-password", "secret-password")
    assert ResetPassword(FakeGateway()).execute(command) is result
    assert received == [command]
    assert "secret-password" not in repr(command)
    assert "secret-token" not in repr(command)
