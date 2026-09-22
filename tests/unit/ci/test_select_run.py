import json
import subprocess
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scripts.ci import select_run


def pull(repository="owner/repo", branch="feature/api", state="open"):
    return {"state": state, "head": {"ref": branch, "repo": {"full_name": repository}}}


@pytest.mark.parametrize(
    "event,ref",
    [
        ("release", "refs/tags/v1"),
        ("workflow_dispatch", "refs/heads/feature"),
        ("pull_request", "refs/pull/22/merge"),
        ("push", "refs/heads/main"),
    ],
)
def test_independent_events_do_not_query_pull_requests(monkeypatch, event, ref):
    run = Mock(side_effect=AssertionError("No API request expected"))
    monkeypatch.setattr(select_run.subprocess, "run", run)
    assert select_run.should_run(event, "owner/repo", ref)
    run.assert_not_called()


@pytest.mark.parametrize(
    "pages,expected",
    [
        ([[]], True),
        ([[pull()]], False),
        ([[], [pull()]], False),
        ([[pull(repository="other/repo")]], True),
        ([[pull(branch="different")]], True),
        ([[pull(state="closed")]], True),
    ],
)
def test_only_open_pr_from_same_repository_suppresses_push(monkeypatch, pages, expected):
    run = Mock(return_value=SimpleNamespace(stdout=json.dumps(pages)))
    monkeypatch.setattr(select_run.subprocess, "run", run)
    assert select_run.should_run("push", "owner/repo", "refs/heads/feature/api") is expected
    assert "head=owner:feature/api" in run.call_args.args[0]
    assert "--paginate" in run.call_args.args[0]
    assert run.call_args.kwargs["check"] is True


@pytest.mark.parametrize(
    "error",
    [
        subprocess.CalledProcessError(1, "gh"),
        subprocess.TimeoutExpired("gh", 60),
    ],
)
def test_api_failure_never_silently_skips_checks(monkeypatch, error):
    monkeypatch.setattr(select_run.subprocess, "run", Mock(side_effect=error))
    with pytest.raises(type(error)):
        select_run.should_run("push", "owner/repo", "refs/heads/feature/api")


def test_job_output(monkeypatch, tmp_path):
    output = tmp_path / "output"
    for key, value in {
        "GITHUB_OUTPUT": str(output),
        "GITHUB_EVENT_NAME": "push",
        "GITHUB_REPOSITORY": "owner/repo",
        "GITHUB_REF": "refs/heads/feature",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(select_run, "should_run", lambda *args: False)
    select_run.main()
    assert output.read_text() == "run_checks=false\n"
