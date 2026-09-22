"""Eigentum und Validierung vor jedem Schreibzugriff, ohne Framework."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.domains.parts.add_part.handler import AddPart
from app.domains.parts.dto import Part
from app.domains.parts.errors import AuthenticationRequired, InvalidPart, PartNotFound
from app.domains.parts.update_part.handler import UpdatePart
from app.domains.repairs.errors import InvalidRepair, RepairNotFound
from app.domains.repairs.update_work.handler import UpdateWork


def command(**overrides):
    return SimpleNamespace(
        **dict(
            owner_id=1,
            repair_id=2,
            part_id=3,
            name="Cable",
            unit_price="0.10",
            quantity="3",
            **overrides,
        )
    )


@pytest.mark.parametrize("handler,method", [(AddPart, "add"), (UpdatePart, "update")])
def test_part_returns_shared_cost_calculation(handler, method):
    repo = Mock()
    getattr(repo, method).return_value = Part(3, 2, "Cable", Decimal("0.10"), 3)
    result = handler(repo).execute(command())
    assert result.total == Decimal("0.30")


@pytest.mark.parametrize("handler", [AddPart, UpdatePart])
@pytest.mark.parametrize(
    "field,value",
    [
        ("name", ""),
        ("name", "x" * 201),
        ("name", "bad\x00"),
        ("unit_price", "NaN"),
        ("unit_price", "-1"),
        ("unit_price", 0.1),
        ("quantity", 0),
        ("quantity", "1.5"),
    ],
)
def test_invalid_part_never_writes(handler, field, value):
    repo = Mock()
    cmd = command()
    setattr(cmd, field, value)
    with pytest.raises(InvalidPart):
        handler(repo).execute(cmd)
    assert all(call[0].startswith("owns_") for call in repo.mock_calls)


@pytest.mark.parametrize("handler,ownership", [(AddPart, "owns_repair"), (UpdatePart, "owns_part")])
def test_foreign_part_rejected_before_validation(handler, ownership):
    repo = Mock()
    getattr(repo, ownership).return_value = False
    cmd = command()
    cmd.unit_price = "bad"
    with pytest.raises(PartNotFound):
        handler(repo).execute(cmd)
    assert len(repo.mock_calls) == 1


@pytest.mark.parametrize("handler", [AddPart, UpdatePart])
def test_no_identity_never_accesses_repository(handler):
    repo = Mock()
    cmd = command()
    cmd.owner_id = True
    with pytest.raises(AuthenticationRequired):
        handler(repo).execute(cmd)
    assert not repo.mock_calls


@pytest.mark.parametrize(
    "field,value",
    [
        ("hours", "1000000"),
        ("hourly_rate", "1000000000"),
        ("hours", "-1"),
        ("hourly_rate", "Infinity"),
        ("hours", True),
    ],
)
def test_work_values_validate_before_write(field, value):
    repo = Mock()
    cmd = SimpleNamespace(owner_id=1, repair_id=2, hours="2", hourly_rate="80")
    setattr(cmd, field, value)
    with pytest.raises(InvalidRepair):
        UpdateWork(repo).execute(cmd)
    repo.update.assert_not_called()


def test_work_requires_owned_case_and_passes_decimals():
    repo = Mock()
    cmd = SimpleNamespace(owner_id=1, repair_id=2, hours="2", hourly_rate="80")
    UpdateWork(repo).execute(cmd)
    repo.update.assert_called_once_with(1, 2, Decimal("2"), Decimal("80"))
    repo.owns_repair.return_value = False
    with pytest.raises(RepairNotFound):
        UpdateWork(repo).execute(cmd)


@pytest.mark.parametrize("handler,method", [(AddPart, "add"), (UpdatePart, "update")])
def test_disappearing_owned_reference_is_not_found(handler, method):
    repo = Mock()
    getattr(repo, method).return_value = None
    with pytest.raises(PartNotFound):
        handler(repo).execute(command())
