"""Renewal coordinates with deployment and only reloads complete certificates."""

import importlib.util
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "acme", ROOT / "deploy/ansible/roles/docker_host/files/repairhub-acme.py"
)
acme = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(acme)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    root = tmp_path / "install"
    root.mkdir()
    live = tmp_path / "live"
    live.mkdir()
    (live / "fullchain.pem").write_bytes(b"certificate-one")
    (live / "privkey.pem").write_bytes(b"private-key-one")
    monkeypatch.setattr(acme, "LIVE", live)
    monkeypatch.setattr(acme.os, "chown", lambda *args: None)
    config = dict(
        install_dir=str(root),
        domain="example.invalid",
        email="test@example.invalid",
        project_name="repairhub-test",
    )
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        output = b""
        if "-checkhost" in args:
            output = b"Hostname example.invalid does match certificate\nCertificate will not expire"
        elif "-pubkey" in args or "-pubout" in args:
            output = b"public-key"
        elif "ps" in args:
            output = b"nginx-container"
        return SimpleNamespace(stdout=output)

    monkeypatch.setattr(acme, "run", run)
    return root, live, config, calls


def test_initial_issue_repeat_and_rotation(setup):
    root, live, config, calls = setup
    assert acme.publish(config)
    tls = root / "infrastructure/tls"
    assert (tls / "server.crt").read_bytes() == b"certificate-one"
    assert (tls / "server.key").stat().st_mode & 0o777 == 0o600
    assert not acme.publish(config)
    (root / "infrastructure/.env").touch()  # Nginx now runs after first deployment.
    assert acme.publish(config)

    def reloads():
        return sum("reload" in call for call in calls)

    assert reloads() == 1
    assert not acme.publish(config)
    assert reloads() == 1
    (live / "fullchain.pem").write_bytes(b"certificate-two")
    (live / "privkey.pem").write_bytes(b"private-key-two")
    assert acme.publish(config)
    assert reloads() == 2
    assert (tls / "server.crt").read_bytes() == b"certificate-two"
    assert (tls / "server.key").read_bytes() == b"private-key-two"
    assert "--keep-until-expiring" in calls[0]
    assert "--force-renewal" not in calls[0]


@pytest.mark.parametrize("failure", ["certbot", "hostname", "key", "reload"])
def test_failure_never_marks_certificate_loaded(setup, monkeypatch, failure):
    root, live, config, calls = setup
    acme.publish(config)
    tls = root / "infrastructure/tls"
    (root / "infrastructure/.env").touch()
    acme.publish(config)
    loaded = (tls / ".loaded-fingerprint").read_text()
    (live / "fullchain.pem").write_bytes(b"certificate-new")
    original = acme.run

    def fail(args, **kwargs):
        if (failure == "certbot" and args[0].endswith("certbot")) or (
            failure == "reload" and "reload" in args
        ):
            raise subprocess.CalledProcessError(1, args)
        if failure == "hostname" and "-checkhost" in args:
            return SimpleNamespace(stdout=b"does NOT match certificate")
        if failure == "key" and "-pubout" in args:
            return SimpleNamespace(stdout=b"other-key")
        return original(args, **kwargs)

    monkeypatch.setattr(acme, "run", fail)
    with pytest.raises((subprocess.CalledProcessError, ValueError)):
        acme.publish(config)
    assert (tls / ".loaded-fingerprint").read_text() == loaded
    monkeypatch.setattr(acme, "run", original)
    assert acme.publish(config)  # A failed reload must be retried, even with the same PEM.


def test_timer_skips_deployment_and_releases_own_lock_on_failure(setup, monkeypatch):
    root, live, config, calls = setup
    configuration = root / "config.json"
    configuration.write_text(json.dumps(config))
    monkeypatch.setattr(acme, "CONFIG", configuration)
    monkeypatch.setattr(acme.sys, "argv", ["repairhub-acme"])
    lock = root / ".deployment-lock"
    lock.mkdir()
    acme.main()
    assert lock.exists() and not calls
    lock.rmdir()
    monkeypatch.setattr(acme, "publish", lambda config: (_ for _ in ()).throw(ValueError("fail")))
    with pytest.raises(ValueError):
        acme.main()
    assert not lock.exists()


def test_deployment_never_releases_ansible_lock(setup, monkeypatch):
    root, live, config, calls = setup
    configuration = root / "config.json"
    configuration.write_text(json.dumps(config))
    monkeypatch.setattr(acme, "CONFIG", configuration)
    monkeypatch.setattr(acme.sys, "argv", ["repairhub-acme", "--deployment-lock-held"])
    with pytest.raises(ValueError, match="Sperre"):
        acme.main()
    (root / ".deployment-lock").mkdir()
    acme.main()
    assert (root / ".deployment-lock").exists()
