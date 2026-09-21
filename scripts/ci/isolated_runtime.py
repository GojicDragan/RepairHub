"""Disposable runtime shared by image smoke tests, browser E2E and DAST scans."""

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


def ready(container: str, command: list[str], timeout: int = 90) -> None:
    """Bound retries and suppress application output, including on failure."""
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
def isolated_runtime(manifest: dict, *, publish_https: bool = False) -> Iterator[IsolatedRuntime]:
    """Start already verified references; never connect to an external test target.

    The caller must have verified and loaded the archive manifest. Its references
    work with both Docker's classic image store and the containerd image store.
    Infrastructure images stay pinned independently of the application commit.
    """
    prefix = f"repairhub-t02-check-{uuid.uuid4().hex[:12]}"
    images = manifest["images"]
    containers: list[str] = []
    network: str | None = None
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
            "@db:5432/repairhub_test\n",
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
                    "subjectAltName=DNS:nginx,IP:127.0.0.1",
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
            # Docker does not publish ports on an internal bridge. Browser tests
            # need their own bridge with only the explicit loopback HTTPS binding.
            docker(
                "network",
                "create",
                *([] if publish_https else ["--internal"]),
                prefix,
                capture=True,
            )
            network = prefix

            def start(name: str, arguments: list[str]) -> None:
                # Record creation before startup: a failed start must still be removed.
                docker("create", "--name", name, *arguments, capture=True)
                containers.append(name)
                docker("start", name, capture=True)

            start(
                runtime.db,
                [
                    "--network",
                    prefix,
                    "--network-alias",
                    "db",
                    "--tmpfs",
                    "/var/lib/postgresql/data:mode=0700",
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
            # Nginx serves the static files from exactly the tested application
            # image. The stable directory and relative symlink match production.
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
