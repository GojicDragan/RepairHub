"""Geschützte Deployment-Dateien erhalten Sonderzeichen ohne Shell-Interpolation."""

import importlib.util
import json
import stat
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file()
)
SCRIPT = ROOT / "scripts" / "ci" / "deployment_input.py"
spec = importlib.util.spec_from_file_location("deployment_input", SCRIPT)
deployment_input = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deployment_input)


@pytest.fixture
def deployment_environment(tmp_path, monkeypatch):
    values = {
        "DEPLOY_INPUT_DIR": str(tmp_path / "inputs"),
        "POSTGRES_PASSWORD": "synthetic-@:#'\"$-value",
        "SECRET_KEY": "synthetic-disposable-test-value-of-sufficient-length",
        "APP_IMAGE": "example/app@sha256:" + "a" * 64,
        "GITHUB_SHA": "d" * 40,
        "GITHUB_RUN_NUMBER": "1",
        "BACKUP_PASSPHRASE": "synthetic-backup-value-at-least-32-characters",
        "MAIL_SERVER": "smtp.example.org",
        "MAIL_PORT": "587",
        "MAIL_DEFAULT_SENDER": "noreply@example.org",
        "MAIL_USERNAME": "smtp-user",
        "MAIL_PASSWORD": "synthetic-mail-value",
        "PUBLIC_URL": "https://example.invalid",
        "ACME_EMAIL": "test@example.invalid",
        "DEPLOY_SSH_PASSWORD": "synthetic-SSH-" + " @:#'\"$`\\ä space ",
        "DEPLOY_SSH_KNOWN_HOSTS": "synthetic hostkey placeholder",
        "REPAIRHUB_DEPLOY_HOST": "deployment.invalid",
        "REPAIRHUB_DEPLOY_USER": "synthetic-existing-user",
        "POSTGRES_USER": "repairhub",
        "POSTGRES_DB": "repairhub",
    }
    monkeypatch.setenv("GITHUB_ACTIONS", "false")
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    return values


def test_secrets_are_protected_and_url_encoded(deployment_environment, capsys):
    values = deployment_environment
    deployment_input.main()
    directory = Path(values["DEPLOY_INPUT_DIR"])
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    payload = json.loads((directory / "vars.json").read_text())
    assert payload["repairhub_migration_mode"] == "compatible"
    assert payload["repairhub_backup_fetch_dir"] == str(directory / "backups")
    assert values["BACKUP_PASSPHRASE"] not in json.dumps(payload)
    assert payload["repairhub_tls_mode"] == "acme"
    assert payload["repairhub_acme_email"] == values["ACME_EMAIL"]
    assert "repairhub_tls_private_key" not in payload
    assert payload["ansible_password"] == values["DEPLOY_SSH_PASSWORD"]
    assert {file.name for file in directory.iterdir()} == {"vars.json", "known_hosts"}
    lines = dict(line.split("=", 1) for line in payload["repairhub_runtime_env"].splitlines())
    assert set(lines) == {
        "SECRET_KEY",
        "DATABASE_URL",
        "MAIL_SERVER",
        "MAIL_PORT",
        "MAIL_DEFAULT_SENDER",
        "MAIL_USERNAME",
        "MAIL_PASSWORD",
        "MAIL_USE_TLS",
        "MAIL_USE_SSL",
        "PUBLIC_URL",
    }
    assert lines["MAIL_PASSWORD"] == values["MAIL_PASSWORD"]
    assert payload["repairhub_database_env"] == f"POSTGRES_PASSWORD={values['POSTGRES_PASSWORD']}\n"
    assert (
        not {"repairhub_nginx_image", "repairhub_postgres_image", "repairhub_database_contract"}
        & payload.keys()
    )
    assert unquote(urlsplit(lines["DATABASE_URL"]).password) == values["POSTGRES_PASSWORD"]
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""
    for file in directory.iterdir():
        assert stat.S_IMODE(file.stat().st_mode) == 0o600


def test_env_line_injection_is_rejected(deployment_environment, monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "synthetic\nREPAIRHUB_ENV=development")
    with pytest.raises(ValueError, match="Zeilenumbrüche"):
        deployment_input.main()
    assert not (Path(deployment_environment["DEPLOY_INPUT_DIR"]) / "vars.json").exists()


def test_app_release_does_not_accept_pipeline_infrastructure_overrides(
    deployment_environment, monkeypatch
):
    for name in ("NGINX_IMAGE", "POSTGRES_IMAGE", "DATABASE_CONTRACT"):
        monkeypatch.setenv(name, "untrusted-pipeline-override")
    deployment_input.main()
    payload = json.loads(
        (Path(deployment_environment["DEPLOY_INPUT_DIR"]) / "vars.json").read_text()
    )
    assert "untrusted-pipeline-override" not in json.dumps(payload)
    assert payload["repairhub_app_image"] == deployment_environment["APP_IMAGE"]


def test_github_log_masking_never_prints_ssh_password(deployment_environment, monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    deployment_input.main()
    captured = capsys.readouterr()
    password = deployment_environment["DEPLOY_SSH_PASSWORD"]
    assert password not in captured.out + captured.err
    assert json.dumps(password) not in captured.out + captured.err
    assert captured.err == ""


@pytest.mark.parametrize(
    "missing", ["DEPLOY_SSH_PASSWORD", "REPAIRHUB_DEPLOY_USER", "REPAIRHUB_DEPLOY_HOST"]
)
@pytest.mark.parametrize("value", [None, ""])
def test_missing_ssh_credentials_or_target_block_before_writing_inputs(
    deployment_environment, monkeypatch, capsys, missing, value
):
    if value is None:
        monkeypatch.delenv(missing)
    else:
        monkeypatch.setenv(missing, value)
    with pytest.raises(ValueError, match=missing) as error:
        deployment_input.main()
    assert deployment_environment["DEPLOY_SSH_PASSWORD"] not in str(error.value)
    assert not Path(deployment_environment["DEPLOY_INPUT_DIR"]).exists()
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""


@pytest.mark.parametrize("character", ["\r", "\n", "\0"])
def test_askpass_control_characters_are_rejected_without_logging_password(
    deployment_environment, monkeypatch, capsys, character
):
    # Ein einfaches Mapping erlaubt die NUL-Prüfung, bevor ein SSH-Aufruf erfolgt.
    environment = dict(deployment_input.os.environ)
    password = "synthetic" + character + "SSH-password"
    environment["DEPLOY_SSH_PASSWORD"] = password
    monkeypatch.setattr(deployment_input.os, "environ", environment)
    with pytest.raises(ValueError, match="SSH-Passwort") as error:
        deployment_input.main()
    assert password not in str(error.value)
    assert not Path(deployment_environment["DEPLOY_INPUT_DIR"]).exists()
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""


@pytest.mark.parametrize("name", ["MAIL_SERVER", "MAIL_USERNAME", "MAIL_PASSWORD", "PUBLIC_URL"])
def test_mail_env_line_injection_is_rejected(deployment_environment, monkeypatch, name):
    monkeypatch.setenv(name, "synthetic\nMAIL_USE_TLS=false")
    with pytest.raises(ValueError, match="Zeilenumbrüche"):
        deployment_input.main()
