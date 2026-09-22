"""Gemeinsame kurzlebige Testumgebung für Image-Smoke-Tests, Browser-E2E und DAST."""

import json
import os
import secrets
import subprocess
import tempfile
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path

if __package__:
    from .images import docker
else:
    from images import docker


@dataclass(frozen=True, slots=True)
class IsolatedRuntime:
    network: str
    app: str
    db: str
    nginx: str
    tls_directory: Path
    ca_path: Path
    url: str = "https://nginx:8443"
    public_url: str | None = None
    mail_directory: Path | None = None


def ready(container: str, command: list[str], timeout: int = 90) -> None:
    """Wartezeit begrenzen und Anwendungsausgaben auch im Fehlerfall unterdrücken."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            probe = subprocess.run(
                ["docker", "exec", container, *command],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=min(10, max(1, deadline - time.monotonic())),
            )
        except subprocess.TimeoutExpired:
            probe = None
        if probe is not None and probe.returncode == 0:
            return
        time.sleep(1)
    raise RuntimeError("Bereitschaftsprüfung fehlgeschlagen; keine internen Logs veröffentlicht.")


def _write_private(path: Path, content: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(content)


def _cleanup(containers: list[str], network: str | None) -> None:
    # Nach einem Fehler trotzdem alle Ressourcen aufräumen; erst danach scheitern.
    failed = False
    commands = [["docker", "rm", "--force", container] for container in reversed(containers)]
    if network is not None:
        commands.append(["docker", "network", "rm", network])
    for command in commands:
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=15,
            )
            failed = failed or result.returncode != 0
        except (OSError, subprocess.TimeoutExpired):
            failed = True
    if failed:
        raise RuntimeError("Isolierte Testressourcen konnten nicht vollständig entfernt werden.")


@contextmanager
def isolated_runtime(
    manifest: dict, *, publish_https: bool = False, receive_mail: bool = False
) -> Iterator[IsolatedRuntime]:
    """Bereits geprüfte Images starten; kein externes Testziel kontaktieren.

    Der Aufrufer muss die Archive anhand des Manifests geprüft und geladen haben.
    Die Referenzen unterstützen Dockers klassischen und den containerd-Imagespeicher.
    Infrastruktur-Images bleiben unabhängig vom Anwendungscommit festgelegt.
    """
    prefix = f"repairhub-t02-check-{uuid.uuid4().hex[:12]}"
    images = manifest["images"]
    containers: list[str] = []
    network: str | None = None
    volume: str | None = None
    with tempfile.TemporaryDirectory(prefix="repairhub-t02-runtime-") as temporary:
        temporary_path = Path(temporary)
        tls_directory = temporary_path / "tls"
        tls_directory.mkdir(mode=0o700)
        static_directory = temporary_path / "www"
        static_release = static_directory / "releases" / "runtime"
        (static_release / "static").mkdir(parents=True, mode=0o755)
        (static_directory / "current").symlink_to("releases/runtime", target_is_directory=True)
        nginx_directory = Path(__file__).resolve().parents[2] / "deploy" / "nginx"
        runtime = IsolatedRuntime(
            network=prefix,
            app=f"{prefix}-app",
            db=f"{prefix}-db",
            nginx=f"{prefix}-nginx",
            tls_directory=tls_directory,
            ca_path=tls_directory / "server.crt",
        )
        if receive_mail:
            outbox = temporary_path / "outbox"
            outbox.mkdir(mode=0o700)
            runtime = replace(runtime, mail_directory=outbox)
        database_password = secrets.token_hex(24)
        _write_private(
            temporary_path / "db.env",
            "POSTGRES_USER=repairhub_test\nPOSTGRES_DB=repairhub_test\n"
            f"POSTGRES_PASSWORD={database_password}\n",
        )
        _write_private(
            temporary_path / "app.env",
            f"SECRET_KEY={secrets.token_hex(32)}\n"
            f"DATABASE_URL=postgresql+psycopg://repairhub_test:{database_password}"
            "@db:5432/repairhub_test\n"
            + (
                "MAIL_SERVER=mail\nMAIL_PORT=1025\nMAIL_USE_TLS=true\n"
                "MAIL_DEFAULT_SENDER=noreply@example.org\nSSL_CERT_FILE=/tmp/smoke-ca.crt\n"
                if receive_mail
                else ""
            ),
        )
        try:
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
                    "/CN=nginx",
                    "-addext",
                    "subjectAltName=DNS:nginx,DNS:mail,IP:127.0.0.1",
                    "-keyout",
                    str(tls_directory / "server.key"),
                    "-out",
                    str(runtime.ca_path),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30,
            )
            (tls_directory / "server.key").chmod(0o600)
            runtime.ca_path.chmod(0o644)
            # Docker veröffentlicht keine Ports auf einer internen Bridge. Browsertests
            # erhalten eine eigene Bridge mit ausschliesslich lokalem HTTPS-Port.
            docker(
                "network",
                "create",
                *([] if publish_https else ["--internal"]),
                prefix,
                capture=True,
            )
            network = prefix
            # Ein eigenes Volume bildet den Produktionsbetrieb ab und überlebt
            # auch stop/start und Container-Neuerstellung innerhalb eines Tests.
            docker("volume", "create", f"{prefix}-db", capture=True)
            volume = f"{prefix}-db"

            def start(name: str, arguments: list[str]) -> None:
                # Vor dem Start vormerken, damit auch fehlgeschlagene Starts bereinigt werden.
                docker("create", "--name", name, *arguments, capture=True)
                containers.append(name)
                docker("start", name, capture=True)

            if receive_mail:
                # Derselbe App-Interpreter, aber Testwerkzeuge nur als read-only Mount.
                # Kein SMTP-Paket oder Postfach gelangt dadurch ins Produktionsimage.
                import aiosmtpd

                tools_directory = Path(aiosmtpd.__file__).resolve().parent.parent
                receiver_script = Path("tests/support/smtp_receiver.py").resolve()
                mail_container = f"{prefix}-mail"
                start(
                    mail_container,
                    [
                        "--network",
                        prefix,
                        "--network-alias",
                        "mail",
                        "--no-healthcheck",
                        "--user",
                        f"{os.getuid()}:{os.getgid()}",
                        "--read-only",
                        "--cap-drop",
                        "ALL",
                        "--security-opt",
                        "no-new-privileges:true",
                        "--env",
                        "PYTHONPATH=/test-tools",
                        "--mount",
                        f"type=bind,src={tools_directory},dst=/test-tools,readonly",
                        "--mount",
                        f"type=bind,src={receiver_script},dst=/receiver.py,readonly",
                        "--mount",
                        f"type=bind,src={tls_directory},dst=/tls,readonly",
                        "--mount",
                        f"type=bind,src={runtime.mail_directory},dst=/outbox",
                        "--entrypoint",
                        "python",
                        images["app"]["reference"],
                        "/receiver.py",
                    ],
                )
                ready(
                    mail_container,
                    [
                        "python",
                        "-c",
                        "import socket; "
                        "socket.create_connection(('127.0.0.1',1025),timeout=2).close()",
                    ],
                )
            start(
                runtime.db,
                [
                    "--network",
                    prefix,
                    "--network-alias",
                    "db",
                    "--mount",
                    f"type=volume,src={volume},dst=/var/lib/postgresql/data",
                    "--env-file",
                    str(temporary_path / "db.env"),
                    images["db"]["reference"],
                ],
            )
            ready(runtime.db, ["pg_isready", "-U", "repairhub_test", "-d", "repairhub_test"])
            start(
                runtime.app,
                [
                    "--network",
                    prefix,
                    "--network-alias",
                    "app",
                    "--read-only",
                    "--mount",
                    "type=tmpfs,dst=/tmp,tmpfs-mode=1777,tmpfs-size=67108864",
                    "--cap-drop",
                    "ALL",
                    "--security-opt",
                    "no-new-privileges:true",
                    "--mount",
                    f"type=bind,src={runtime.ca_path},dst=/tmp/smoke-ca.crt,readonly",
                    "--env-file",
                    str(temporary_path / "app.env"),
                    images["app"]["reference"],
                ],
            )
            ready(
                runtime.app,
                [
                    "python",
                    "-c",
                    "import json,urllib.request; "
                    "r=urllib.request.urlopen('http://127.0.0.1:8000/health/ready',timeout=5); "
                    "assert json.load(r)=={'status':'ready'}",
                ],
            )
            # Derselbe explizite Migrationsschritt wie im Deployment, einmalig vor
            # Browser-/DAST-Zugriffen; keine Migration in Gunicorn-Workern.
            capabilities = json.loads(Path("deploy/capabilities.json").read_text())
            if capabilities["schema_migrations"]:
                docker("exec", runtime.app, "flask", "--app", "app", "db", "upgrade", capture=True)
            # Nginx liefert statische Dateien aus genau dem geprüften Anwendungsimage.
            # Stabiles Verzeichnis und relativer Symlink entsprechen der Produktion.
            docker(
                "cp",
                f"{runtime.app}:/srv/repairhub/app/web/static/.",
                str(static_release / "static"),
                capture=True,
            )
            start(
                runtime.nginx,
                [
                    "--network",
                    prefix,
                    "--network-alias",
                    "nginx",
                    "--read-only",
                    "--tmpfs",
                    "/var/cache/nginx:mode=0755,size=32m",
                    "--tmpfs",
                    "/var/run:mode=0755,size=1m",
                    "--security-opt",
                    "no-new-privileges:true",
                    "--mount",
                    f"type=bind,src={tls_directory},dst=/etc/nginx/tls,readonly",
                    "--mount",
                    f"type=bind,src={nginx_directory},dst=/etc/nginx/repairhub,readonly",
                    "--mount",
                    f"type=bind,src={static_directory},dst=/usr/share/nginx/html,readonly",
                    "--entrypoint",
                    "nginx",
                    *(["--publish", "127.0.0.1::8443"] if publish_https else []),
                    images["nginx"]["reference"],
                    "-c",
                    "/etc/nginx/repairhub/nginx.conf",
                    "-g",
                    "daemon off;",
                ],
            )
            ready(
                runtime.app,
                [
                    "python",
                    "-c",
                    "import json,ssl,urllib.request; "
                    "ctx=ssl.create_default_context(cafile='/tmp/smoke-ca.crt'); "
                    "r=urllib.request.urlopen('https://nginx:8443/health/ready',"
                    "context=ctx,timeout=5); "
                    "assert json.load(r)=={'status':'ready'}",
                ],
            )
            if publish_https:
                binding = docker("port", runtime.nginx, "8443/tcp", capture=True)
                address, separator, port = binding.rpartition(":")
                if (
                    address != "127.0.0.1"
                    or separator != ":"
                    or not port.isdecimal()
                    or not 1 <= int(port) <= 65535
                ):
                    raise RuntimeError("Die Browser-Testadresse ist keine lokale HTTPS-Bindung.")
                runtime = replace(runtime, public_url=f"https://127.0.0.1:{port}")
            yield runtime
        finally:
            _cleanup(containers, network)
            if volume is not None:
                docker("volume", "rm", volume, capture=True)
