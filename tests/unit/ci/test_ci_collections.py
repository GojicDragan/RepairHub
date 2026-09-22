from subprocess import TimeoutExpired
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scripts.ci import install_collections


@pytest.mark.parametrize(
    ("results", "expected", "pauses"),
    [
        ([0], 0, []),
        ([1, 0], 0, [5]),
        ([1, 1, 0], 0, [5, 15]),
        ([1, 1, 1], 1, [5, 15]),
        (["timeout", 0], 0, [5]),
        (["timeout", "timeout", "timeout"], 1, [5, 15]),
    ],
)
def test_installation_retries_are_bounded_and_fail_closed(monkeypatch, results, expected, pauses):
    run = Mock(
        side_effect=[
            TimeoutExpired("ansible-galaxy", 180)
            if result == "timeout"
            else SimpleNamespace(returncode=result)
            for result in results
        ]
    )
    sleep = Mock()
    monkeypatch.setattr(install_collections.subprocess, "run", run)
    monkeypatch.setattr(install_collections.time, "sleep", sleep)
    assert install_collections.install() == expected
    assert run.call_count == len(results)
    assert [call.args[0] for call in sleep.call_args_list] == pauses
    for call in run.call_args_list:
        assert call.args[0] == [
            "ansible-galaxy",
            "collection",
            "install",
            "-r",
            "deploy/ansible/requirements.yml",
        ]
        assert call.kwargs == {"check": False, "timeout": 180}
