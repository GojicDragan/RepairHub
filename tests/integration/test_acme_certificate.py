"""Exercise certificate validation with real OpenSSL and disposable local PEMs."""

import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "acme_integration", ROOT / "deploy/ansible/roles/docker_host/files/repairhub-acme.py"
)
acme = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(acme)
pytestmark = pytest.mark.integration


@pytest.mark.parametrize("domain", ["example.invalid", "other.invalid"])
def test_real_certificate_hostname_validation(tmp_path, monkeypatch, domain):
    live = tmp_path / "live"
    live.mkdir()
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-subj",
            "/CN=example.invalid",
            "-addext",
            "subjectAltName=DNS:example.invalid",
            "-keyout",
            str(live / "privkey.pem"),
            "-out",
            str(live / "fullchain.pem"),
        ],
        check=True,
        capture_output=True,
    )
    root = tmp_path / "install"
    root.mkdir()
    monkeypatch.setattr(acme, "LIVE", live)
    actual_run = acme.run

    def run(args, **kwargs):
        if args[0] == "/usr/bin/certbot":
            return subprocess.CompletedProcess(args, 0, stdout=b"")
        return actual_run(args, **kwargs)

    monkeypatch.setattr(acme, "run", run)
    config = dict(
        install_dir=str(root),
        domain=domain,
        email="test@example.invalid",
        project_name="repairhub-test",
    )
    if domain == "example.invalid":
        assert acme.publish(config)
        assert not acme.publish(config)
        assert (root / "infrastructure/tls/server.crt").read_bytes() == (
            live / "fullchain.pem"
        ).read_bytes()
    else:
        with pytest.raises((ValueError, subprocess.CalledProcessError)):
            acme.publish(config)
        assert not (root / "infrastructure/tls/server.crt").exists()
