"""Bereitet einen wegwerfbaren SSH-/Docker-Testhost für die echten Playbooks vor.

Nur lokal ausführen: startet Docker-in-Docker mit --privileged, ohne den
Docker-Socket des Arbeitsplatzes einzubinden. Veröffentlichung nur auf Loopback.
"""

import argparse
import json
import os
import secrets
import shlex
import subprocess
import time
from pathlib import Path

from scripts.ci.images import verify

REGISTRY = "registry:3.0.0@sha256:6c5666b861f3505b116bb9aa9b25175e71210414bd010d92035ff64018f9457e"


def run(*args: str, **kwargs) -> str:
    result = subprocess.run(args, check=True, capture_output=True, **kwargs)
    return result.stdout.decode().strip()


def write_private(path: Path, content: str) -> None:
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(content)


def prepare(directory: Path, artifacts: Path, commit: str) -> None:
    manifest = verify(artifacts, commit)
    directory.mkdir(parents=True, mode=0o700, exist_ok=False)
    access = directory / "access"
    access.mkdir()
    key = directory / "deploy-key"
    run("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key))
    (access / "authorized_keys").write_bytes(key.with_suffix(".pub").read_bytes())
    run("docker", "build", "-t", "repairhub-testhost:29.6.1", "tests/deployment")
    host = "repairhub-check-" + secrets.token_hex(5)
    # Keine Anwendungsschlüssel in Docker-Argumenten oder Testhost-Images.
    run(
        "docker",
        "run",
        "-d",
        "--privileged",
        "--name",
        host,
        "--label",
        "repairhub.fixture=deployment",
        "-p",
        "127.0.0.1::22",
        "-p",
        "127.0.0.1::443",
        "--mount",
        f"type=bind,source={access},target=/test-access,readonly",
        "repairhub-testhost:29.6.1",
    )
    write_private(directory / "container-name", host + "\n")
    deadline = time.monotonic() + 90
    while True:
        try:
            run("docker", "exec", host, "docker", "info")
            break
        except subprocess.CalledProcessError:
            if time.monotonic() > deadline:
                raise RuntimeError("Isolierter Testdaemon wurde nicht bereit.") from None
            time.sleep(1)
    ports = {
        name: run("docker", "port", host, port).rsplit(":", 1)[1]
        for name, port in (("ssh", "22/tcp"), ("https", "443/tcp"))
    }
    # Docker ist hier der bereits vertrauenswürdige lokale Kontrollkanal.
    host_key = run("docker", "exec", host, "cat", "/etc/ssh/ssh_host_ed25519_key.pub").split()
    write_private(
        directory / "known_hosts", f"[127.0.0.1]:{ports['ssh']} {' '.join(host_key[:2])}\n"
    )
    run("docker", "exec", host, "mkdir", "-p", "/opt/repairhub")
    run("docker", "exec", host, "chown", "repairhub-deploy:repairhub-deploy", "/opt/repairhub")
    run("docker", "exec", host, "chmod", "0700", "/opt/repairhub")
    run(
        "docker",
        "exec",
        host,
        "docker",
        "run",
        "-d",
        "--name",
        "fixture-registry",
        "-p",
        "127.0.0.1:5000:5000",
        REGISTRY,
    )
    refs = {}
    for name, entry in manifest["images"].items():
        with (artifacts / entry["archive"]).open("rb") as stream:
            run("docker", "exec", "-i", host, "docker", "load", stdin=stream)
        tag = f"127.0.0.1:5000/repairhub/{name}:fixture"
        run("docker", "exec", host, "docker", "tag", entry["reference"], tag)
        run("docker", "exec", host, "docker", "push", tag)
        info = json.loads(run("docker", "exec", host, "docker", "image", "inspect", tag))[0]
        refs[name] = next(ref for ref in info["RepoDigests"] if ref.startswith("127.0.0.1:5000/"))
    run(
        "openssl",
        "req",
        "-x509",
        "-newkey",
        "rsa:2048",
        "-nodes",
        "-keyout",
        str(directory / "server.key"),
        "-out",
        str(directory / "server.crt"),
        "-days",
        "2",
        "-subj",
        "/CN=localhost",
        "-addext",
        "subjectAltName=DNS:localhost,IP:127.0.0.1",
    )
    (directory / "server.key").chmod(0o600)
    password = secrets.token_urlsafe(32)
    # Die lokale Registry ersetzt nur für diese Fixture die echten Quellen.
    # Infrastruktur bleibt ein eigener, vom App-Release unabhängiger Eingabesatz.
    infrastructure = {
        **manifest["infrastructure"],
        "nginx_image": refs["nginx"],
        "postgres_image": refs["db"],
    }
    infrastructure_path = directory / "infrastructure.json"
    write_private(infrastructure_path, json.dumps(infrastructure, indent=2) + "\n")
    values = {
        "repairhub_repo_root": str(Path.cwd()),
        "repairhub_app_image": refs["app"],
        "repairhub_infrastructure_file": str(infrastructure_path),
        "repairhub_release_commit": commit,
        "repairhub_release_sequence": 1,
        "repairhub_public_url": f"https://127.0.0.1:{ports['https']}",
        "repairhub_smoke_ca_path": str(directory / "server.crt"),
        "repairhub_runtime_env": (
            f"SECRET_KEY={secrets.token_hex(32)}\n"
            f"DATABASE_URL=postgresql+psycopg://repairhub:{password}@db:5432/repairhub\n"
        ),
        "repairhub_database_env": f"POSTGRES_PASSWORD={password}\n",
        "repairhub_tls_mode": "provided",
        "repairhub_tls_certificate": (directory / "server.crt").read_text(),
        "repairhub_tls_private_key": (directory / "server.key").read_text(),
    }
    write_private(directory / "release.json", json.dumps(values))
    environment = {
        "ANSIBLE_CONFIG": str(Path.cwd() / "deploy/ansible/ansible.cfg"),
        "ANSIBLE_INVENTORY": str(Path.cwd() / "tests/deployment/inventory.yml"),
        "REPAIRHUB_FIXTURE_SSH_PORT": ports["ssh"],
        "ANSIBLE_PRIVATE_KEY_FILE": str(key),
        "ANSIBLE_SSH_COMMON_ARGS": (
            f"-o StrictHostKeyChecking=yes -o IdentitiesOnly=yes "
            f"-o UserKnownHostsFile={directory}/known_hosts"
        ),
    }
    write_private(
        directory / "controller.env",
        "".join(f"export {name}={shlex.quote(value)}\n" for name, value in environment.items()),
    )
    print(f"Testhost {host} bereit. Geschützte Eingaben: {directory}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts/images"))
    parser.add_argument("--commit", required=True)
    options = parser.parse_args()
    try:
        prepare(options.directory.resolve(), options.artifacts.resolve(), options.commit)
    except subprocess.CalledProcessError:
        # Keine ausgeführten Befehle mit möglichen vertraulichen Parametern protokollieren.
        raise SystemExit("Testhost-Vorbereitung fehlgeschlagen; lokale Fixture prüfen.") from None
