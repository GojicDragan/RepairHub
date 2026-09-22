"""Fachliche Beispiele ohne Flask und Datenbank: Wiederaufnahme, Schritte und Eigentum."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.domains.repairs.add_step.handler import AddStep
from app.domains.repairs.change_status.handler import ChangeStatus
from app.domains.repairs.create_repair.handler import CreateRepair
from app.domains.repairs.errors import AuthenticationRequired, InvalidRepair, RepairNotFound
from app.domains.repairs.get_repair.handler import GetRepair
from app.domains.repairs.list_repairs.handler import ListRepairs
from app.domains.repairs.update_description.handler import UpdateDescription
from app.domains.repairs.update_step.handler import UpdateStep

HANDLERS = (
    CreateRepair,
    ListRepairs,
    GetRepair,
    UpdateDescription,
    ChangeStatus,
    AddStep,
    UpdateStep,
)
NOW = datetime(2026, 9, 22, tzinfo=UTC)


def make(handler, repository):
    return handler(repository, lambda: NOW) if handler is CreateRepair else handler(repository)


def command(**overrides):
    return SimpleNamespace(
        **{
            "owner_id": 1,
            "device_id": 2,
            "repair_id": 3,
            "step_id": 4,
            "description": "  Radio turns off\nwhen warm  ",
            "status": "in_progress",
            "completed": True,
            "offset": 0,
            "part_offset": 0,
            "complete": False,
            "limit": 20,
            "snapshot": None,
            **overrides,
        }
    )


@pytest.mark.parametrize("handler", HANDLERS)
@pytest.mark.parametrize("owner", [None, 0, -1, "1", True])
def test_untrusted_owner_is_rejected_without_data_access(handler, owner):
    repository = Mock()
    with pytest.raises(AuthenticationRequired):
        make(handler, repository).execute(command(owner_id=owner))
    assert repository.mock_calls == []


def test_new_case_starts_open_and_incomplete_step_is_added():
    repository = Mock()
    CreateRepair(repository, lambda: NOW).execute(command())
    repository.create.assert_called_once_with(1, 2, "Radio turns off\nwhen warm", "open", NOW)
    AddStep(repository).execute(command())
    repository.add.assert_called_once_with(1, 3, "Radio turns off\nwhen warm", False)


@pytest.mark.parametrize("state", ["open", "in_progress", "completed"])
def test_every_status_is_allowed_without_transition_locks(state):
    repository = Mock()
    ChangeStatus(repository).execute(command(status=state))
    repository.change.assert_called_once_with(1, 3, state)


@pytest.mark.parametrize("handler", [CreateRepair, UpdateDescription, AddStep, UpdateStep])
@pytest.mark.parametrize("value", [None, "", "  ", "bad\x00value", "x" * 10001])
def test_invalid_description_never_writes(handler, value):
    repository = Mock()
    with pytest.raises(InvalidRepair):
        make(handler, repository).execute(command(description=value))
    assert all(call[0].startswith("owns_") for call in repository.mock_calls)


@pytest.mark.parametrize("handler", [AddStep, UpdateStep])
def test_step_length_is_bounded(handler):
    with pytest.raises(InvalidRepair):
        handler(Mock()).execute(command(description="x" * 2001))


@pytest.mark.parametrize("value", ["closed", "", None, [], 1])
def test_unknown_status_is_rejected(value):
    with pytest.raises(InvalidRepair):
        ChangeStatus(Mock()).execute(command(status=value))


@pytest.mark.parametrize("value", ["true", "false", 0, 1, None])
def test_completed_requires_actual_boolean(value):
    with pytest.raises(InvalidRepair):
        UpdateStep(Mock()).execute(command(completed=value))


@pytest.mark.parametrize(
    "handler,check",
    [
        (CreateRepair, "owns_device"),
        (ListRepairs, "owns_device"),
        (UpdateDescription, "owns_repair"),
        (ChangeStatus, "owns_repair"),
        (AddStep, "owns_repair"),
        (UpdateStep, "owns_step"),
    ],
)
def test_foreign_parent_is_rejected_before_validating_content(handler, check):
    repository = Mock()
    getattr(repository, check).return_value = False
    with pytest.raises(RepairNotFound):
        make(handler, repository).execute(command(description="", status="invalid"))
    assert len(repository.mock_calls) == 1


@pytest.mark.parametrize(
    "handler,method",
    [
        (CreateRepair, "create"),
        (GetRepair, "get"),
        (UpdateDescription, "update"),
        (ChangeStatus, "change"),
        (AddStep, "add"),
        (UpdateStep, "update"),
    ],
)
def test_absent_result_including_lost_parent_is_not_found(handler, method):
    repository = Mock()
    getattr(repository, method).return_value = None
    with pytest.raises(RepairNotFound):
        make(handler, repository).execute(command())


@pytest.mark.parametrize("handler", [ListRepairs, GetRepair])
@pytest.mark.parametrize("value", [-1, True, "0", 2**63])
def test_invalid_pagination_is_rejected(handler, value):
    with pytest.raises(ValueError):
        make(handler, Mock()).execute(command(offset=value))


def test_windows_are_bounded():
    repository = Mock()
    ListRepairs(repository).execute(command())
    repository.list.assert_called_once_with(1, 2, 0, 20, None)
    from app.domains.repairs.dto import RepairDetails

    repository.get.return_value = RepairDetails(Mock(), (), 0, 0)
    GetRepair(repository).execute(command())
    repository.get.assert_called_once_with(1, 3, 0, 20)


@pytest.mark.parametrize(
    "field,value",
    [
        ("limit", 0),
        ("limit", 61),
        ("limit", True),
        ("limit", "20"),
        ("snapshot", -1),
        ("snapshot", True),
        ("snapshot", 2**63),
    ],
)
def test_repair_list_rejects_invalid_windows(field, value):
    repository = Mock()
    with pytest.raises(ValueError):
        ListRepairs(repository).execute(command(**{field: value}))
    repository.list.assert_not_called()


def test_repair_list_forwards_bounded_window_and_snapshot():
    repository = Mock()
    ListRepairs(repository).execute(command(offset=40, limit=60, snapshot=120))
    repository.list.assert_called_once_with(1, 2, 40, 60, 120)


def test_api_complete_detail_preserves_all_parts_and_steps():
    from decimal import Decimal

    from app.domains.repairs.dto import PartPosition, RepairDetails
    from app.domains.repairs.get_repair.dto import Command

    repository = Mock()
    repository.get.return_value = RepairDetails(
        Mock(),
        (),
        0,
        0,
        parts=tuple(PartPosition(i, "Cable", Decimal("0.10"), 3) for i in range(25)),
    )
    result = GetRepair(repository).execute(Command(1, 3, complete=True))
    repository.get.assert_called_once_with(1, 3, 0, None)
    assert len(result.parts) == 25 and result.total_cost == Decimal("7.50")


@pytest.mark.parametrize(
    "handler", [CreateRepair, UpdateDescription, ChangeStatus, AddStep, UpdateStep]
)
def test_system_read_access_never_authorizes_writes(handler):
    from app.domains.repairs.dto import SystemReadAccess

    repository = Mock()
    with pytest.raises(AuthenticationRequired):
        make(handler, repository).execute(command(owner_id=SystemReadAccess.ALL_REPAIRS))
    assert repository.mock_calls == []
