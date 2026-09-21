"""Security-report redaction, error classification and mandatory source gates."""

import json
import os
import subprocess

import pytest

from scripts.ci import security


def test_source_snippets_and_match_values_are_not_retained():
    # Synthetic placeholders, never a functioning credential.
    report = [{"RuleID": "synthetic", "Secret": "placeholder", "Match": "placeholder"}]
    redacted = security.redact_report("gitleaks", report)
    assert "Secret" not in redacted[0]
    assert "Match" not in redacted[0]
    bandit = {"results": [{"code": "source snippet", "test_id": "B001"}]}
    assert "code" not in security.redact_report("bandit", bandit)["results"][0]


def test_scanner_error_diagnostics_do_not_echo_output():
    assert security.error_category("download failed: synthetic-secret-placeholder", 1) == (
        "database_download_failed"
    )


def test_failed_locked_dependency_export_cannot_become_a_clean_source_scan(tmp_path, monkeypatch):
    def fail_export(command, **kwargs):
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(security.subprocess, "run", fail_export)
    with pytest.raises(subprocess.CalledProcessError):
        security.source_scans(tmp_path / "reports", tmp_path / "binaries")


@pytest.mark.parametrize(
    ("image_name", "source", "expected_exception"),
    [
        ("db", security.POSTGRES_GOSU_IMAGE, True),
        ("app", security.POSTGRES_GOSU_IMAGE, False),
        ("nginx", security.POSTGRES_GOSU_IMAGE, False),
        ("db", security.POSTGRES_GOSU_IMAGE[:-1] + "0", False),
        ("db", "postgres:17.11-alpine3.24", False),
        ("db", None, False),
    ],
)
def test_gosu_exception_is_only_enabled_for_exact_database_digest(
    tmp_path, monkeypatch, image_name, source, expected_exception
):
    artifacts = tmp_path / "images"
    artifacts.mkdir()
    reports = tmp_path / "reports"
    reports.mkdir()
    (artifacts / "manifest.json").write_text(
        json.dumps(
            {
                "commit": "a" * 40,
                "images": {image_name: {"archive": "image.tar", "source_reference": source}},
            }
        )
    )
    monkeypatch.setattr(security, "source_scans", lambda *args: [])
    calls = []

    def capture(kind, command, path, **kwargs):
        calls.append((command, kwargs))
        return {"passed": True}

    monkeypatch.setattr(security, "run_scan", capture)
    assert security.main(artifacts, reports, tmp_path) == 0
    command, options = calls[0]
    ignorefile = security.POSTGRES_GOSU_EXCEPTIONS if expected_exception else None
    assert options["trivy_ignorefile"] == ignorefile
    assert command[command.index("--ignorefile") + 1] == (
        str(ignorefile) if ignorefile else os.devnull
    )
    assert "--show-suppressed" in command
    assert command[command.index("--severity") + 1] == "HIGH,CRITICAL"
    assert command[command.index("--exit-code") + 1] == "1"
    assert "--ignore-unfixed" not in command
