"""Production gates check current main and immutable tag-to-commit identity."""

from types import SimpleNamespace

import pytest

from scripts.ci import check_release_ref as release

COMMIT = "a" * 40


@pytest.mark.parametrize("ref", ["refs/heads/main", "refs/tags/v1.0.0", "refs/tags/releases/v1"])
@pytest.mark.parametrize("event", ["push", "release", "workflow_dispatch"])
def test_current_release_is_allowed(monkeypatch, ref, event):
    monkeypatch.setattr(release, "remote_commit", lambda *args: COMMIT)
    release.check_release("owner/repo", ref, COMMIT, event)


@pytest.mark.parametrize(
    ("ref", "event"),
    [
        ("refs/heads/feature/a", "push"),
        ("refs/heads/main", "pull_request"),
        ("refs/tags/v1", "pull_request_target"),
    ],
)
def test_untrusted_context_never_queries_production(monkeypatch, ref, event):
    def unexpected(*args):
        pytest.fail("Untrusted event must be rejected before querying GitHub")

    monkeypatch.setattr(release, "remote_commit", unexpected)
    with pytest.raises(ValueError):
        release.check_release("owner/repo", ref, COMMIT, event)


@pytest.mark.parametrize("ref", ["refs/heads/main", "refs/tags/v1"])
def test_stale_or_non_main_commit_is_rejected(monkeypatch, ref):
    monkeypatch.setattr(release, "remote_commit", lambda *args: "b" * 40)
    with pytest.raises(ValueError, match="main-Stand"):
        release.check_release("owner/repo", ref, COMMIT, "push")


def test_moved_tag_is_rejected(monkeypatch):
    monkeypatch.setattr(
        release,
        "remote_commit",
        lambda repo, ref: COMMIT if ref == "refs/heads/main" else "b" * 40,
    )
    with pytest.raises(ValueError, match="Tag"):
        release.check_release("owner/repo", "refs/tags/v1", COMMIT, "release")


def test_commit_endpoint_resolves_tag_and_encodes_ref(monkeypatch):
    def run(argv, **kwargs):
        assert argv == [
            "gh",
            "api",
            "repos/owner/repo/commits/refs%2Ftags%2Freleases%2Fv1",
            "--jq",
            ".sha",
        ]
        assert kwargs["check"] is True
        return SimpleNamespace(stdout=COMMIT + "\n")

    monkeypatch.setattr(release.subprocess, "run", run)
    assert release.remote_commit("owner/repo", "refs/tags/releases/v1") == COMMIT
