"""Statuszahlen gehören der Reparaturdomäne und benötigen nur einen Lese-Port."""

from unittest.mock import Mock

import pytest

from app.domains.repairs.dto import SystemReadAccess
from app.domains.repairs.errors import AuthenticationRequired
from app.domains.repairs.get_status_overview.dto import Command, StatusOverview
from app.domains.repairs.get_status_overview.handler import GetStatusOverview


@pytest.mark.parametrize("owner", [None, 0, -1, True, "1", SystemReadAccess.ALL_REPAIRS])
def test_invalid_owner_never_reads_counts(owner):
    repository = Mock()
    with pytest.raises(AuthenticationRequired):
        GetStatusOverview(repository).execute(Command(owner))
    repository.count_by_status.assert_not_called()


def test_missing_status_groups_are_zero():
    repository = Mock()
    repository.count_by_status.return_value = {"in_progress": 3}
    assert GetStatusOverview(repository).execute(Command(7)) == StatusOverview(0, 3, 0)
    repository.count_by_status.assert_called_once_with(7)


def test_no_cases_returns_three_zero_counts():
    repository = Mock()
    repository.count_by_status.return_value = {}
    assert GetStatusOverview(repository).execute(Command(7)) == StatusOverview(0, 0, 0)


def test_each_call_reads_current_counts():
    repository = Mock()
    repository.count_by_status.side_effect = [{"open": 2}, {"open": 1, "completed": 1}]
    handler = GetStatusOverview(repository)
    assert handler.execute(Command(7)) == StatusOverview(2, 0, 0)
    assert handler.execute(Command(7)) == StatusOverview(1, 0, 1)
