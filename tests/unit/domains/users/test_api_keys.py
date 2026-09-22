from unittest.mock import Mock

from app.domains.users.authenticate_api_key.dto import Command as Authenticate
from app.domains.users.authenticate_api_key.handler import AuthenticateApiKey
from app.domains.users.create_api_key.dto import Command as Create
from app.domains.users.create_api_key.handler import CreateApiKey
from app.domains.users.dto import ApiKeyStatus, GeneratedApiKey, UserIdentity
from app.domains.users.get_api_key.dto import Command as Get
from app.domains.users.get_api_key.handler import GetApiKey
from app.domains.users.revoke_api_key.dto import Command as Revoke
from app.domains.users.revoke_api_key.handler import RevokeApiKey


def test_explicit_gateway_injection_without_framework():
    gateway = Mock()
    gateway.create.return_value = GeneratedApiKey("private-key", "2026-09-22")
    gateway.authenticate.return_value = UserIdentity(1, "example")
    gateway.status.return_value = ApiKeyStatus(True, "2026-09-22")
    assert CreateApiKey(gateway).execute(Create(1)).value == "private-key"
    assert GetApiKey(gateway).execute(Get(1)).active
    assert AuthenticateApiKey(gateway).execute(Authenticate("private-key")).id == 1
    RevokeApiKey(gateway).execute(Revoke(1))
    gateway.revoke.assert_called_once_with(Revoke(1))
    assert "private-key" not in repr(Authenticate("private-key"))
    assert "private-key" not in repr(gateway.create.return_value)
