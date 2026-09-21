"""Anwendungsfallvertrag ohne Flask, Datenbank oder echten Identitätsanbieter prüfen."""

import pytest

from app.domains.users.check_reset_link.dto import Command
from app.domains.users.check_reset_link.handler import CheckResetLink
from app.domains.users.dto import UserResult


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
        def check_reset(self, command):
            received.append(command)
            return result

    command = Command("secret-token")
    assert CheckResetLink(FakeGateway()).execute(command) is result
    assert received == [command]
    assert "secret-password" not in repr(command)
    assert "secret-token" not in repr(command)
