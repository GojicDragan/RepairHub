"""Fachregeln und Eigentumsverträge ohne Flask oder Datenbank prüfen."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.domains.devices.dto import Device, DeviceValues
from app.domains.devices.errors import AuthenticationRequired, DeviceNotFound, InvalidDevice
from app.domains.devices.get_device.handler import GetDevice
from app.domains.devices.list_devices.handler import ListDevices
from app.domains.devices.register_device.handler import RegisterDevice
from app.domains.devices.update_device.handler import UpdateDevice

VALUES = DeviceValues(" Radio ", " Maker ", " Model ")


@pytest.mark.parametrize("handler", [RegisterDevice, UpdateDevice])
def test_write_uses_trusted_owner_and_validated_values(handler):
    repository = Mock()
    command = SimpleNamespace(owner_id=7, device_id=12, values=VALUES)
    handler(repository).execute(command)
    method = repository.create if handler is RegisterDevice else repository.update
    expected = (7, DeviceValues("Radio", "Maker", "Model"))
    if handler is UpdateDevice:
        expected = (7, 12, expected[-1])
    method.assert_called_once_with(*expected)


@pytest.mark.parametrize("handler", [RegisterDevice, UpdateDevice, GetDevice, ListDevices])
@pytest.mark.parametrize("owner", [None, 0, -1, True, "7"])
def test_anonymous_or_invalid_owner_never_reaches_repository(handler, owner):
    repository = Mock()
    with pytest.raises(AuthenticationRequired):
        handler(repository).execute(SimpleNamespace(owner_id=owner))
    assert repository.mock_calls == []


@pytest.mark.parametrize("field", ["name", "manufacturer", "model"])
@pytest.mark.parametrize("value", [None, "", " \t ", "x" * 121, "a\x00b", []])
def test_invalid_values_never_write(field, value):
    values = {"name": "Radio", "manufacturer": "Maker", "model": "R1", field: value}
    repository = Mock()
    with pytest.raises(InvalidDevice) as error:
        RegisterDevice(repository).execute(
            SimpleNamespace(owner_id=1, values=DeviceValues(**values))
        )
    assert field in error.value.errors
    repository.create.assert_not_called()


def test_foreign_update_returns_not_found_before_validation():
    repository = Mock()
    repository.get.return_value = None
    with pytest.raises(DeviceNotFound):
        UpdateDevice(repository).execute(SimpleNamespace(owner_id=1, device_id=2, values=None))
    repository.get.assert_called_once_with(1, 2)
    repository.update.assert_not_called()


def test_get_returns_dto_and_scopes_query():
    repository = Mock()
    repository.get.return_value = Device(2, "Radio", "Maker", "R1")
    assert GetDevice(repository).execute(SimpleNamespace(owner_id=1, device_id=2)).id == 2
    repository.get.assert_called_once_with(1, 2)


@pytest.mark.parametrize("limit", [0, 61, -1, "20", True])
def test_list_rejects_unbounded_or_invalid_windows(limit):
    repository = Mock()
    with pytest.raises(ValueError):
        ListDevices(repository).execute(
            SimpleNamespace(owner_id=1, offset=0, limit=limit, snapshot=None)
        )
    repository.list.assert_not_called()
