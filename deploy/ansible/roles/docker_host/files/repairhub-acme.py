#!/usr/bin/python3
"""Issue/renew TLS under the same host lock as Ansible; publish a complete pair."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

CONFIG = Path("/etc/repairhub-acme.json")
LIVE = Path("/etc/letsencrypt/live/repairhub")


def run(arguments, **kwargs):
    return subprocess.run(arguments, check=True, capture_output=True, **kwargs)  # nosec B603


def publish(config):
    root = Path(config["install_dir"])
    domain = config["domain"]
    # Certbot retains a valid certificate until renewal is due. No forced renewal.
    run(
        [
            "/usr/bin/certbot",
            "certonly",
            "--standalone",
            "--non-interactive",
            "--agree-tos",
            "--keep-until-expiring",
            "--preferred-challenges",
            "http",
            "--cert-name",
            "repairhub",
            "--domain",
            domain,
            "--email",
            config["email"],
        ]
    )
    live = LIVE
    cert = live / "fullchain.pem"
    key = live / "privkey.pem"
    validity = run(
        [
            "/usr/bin/openssl",
            "x509",
            "-in",
            str(cert),
            "-noout",
            "-checkhost",
            domain,
        ]
    )
    if b"does match certificate" not in validity.stdout:
        raise ValueError("Zertifikat gilt nicht für die konfigurierte Domain.")
    run(["/usr/bin/openssl", "x509", "-in", str(cert), "-noout", "-checkend", "0"])
    public_cert = run(["/usr/bin/openssl", "x509", "-in", str(cert), "-pubkey", "-noout"]).stdout
    public_key = run(["/usr/bin/openssl", "pkey", "-in", str(key), "-pubout"]).stdout
    if public_cert != public_key:
        raise ValueError("Zertifikat und Schlüssel passen nicht zusammen.")
    fingerprint = hashlib.sha256(cert.read_bytes() + key.read_bytes()).hexdigest()
    tls = root / "infrastructure/tls"
    tls.mkdir(parents=True, exist_ok=True, mode=0o700)
    owner = root.stat()
    generation = tls / fingerprint
    generation.mkdir(exist_ok=True, mode=0o700)
    for source, name in ((cert, "server.crt"), (key, "server.key")):
        target = generation / name
        if not target.exists():
            shutil.copyfile(source, target)
        target.chmod(0o600)
        os.chown(target, owner.st_uid, owner.st_gid)
    for directory in (tls.parent, tls, generation):
        os.chown(directory, owner.st_uid, owner.st_gid)
    changed = not (tls / "current").is_symlink() or os.readlink(tls / "current") != fingerprint
    # A directory symlink swaps the key/certificate pair together. Nginx has the
    # containing directory mounted, so it sees the new target without recreation.
    if changed:
        temporary = tls / ".current-next"
        temporary.unlink(missing_ok=True)
        temporary.symlink_to(fingerprint)
        temporary.replace(tls / "current")
    for name in ("server.crt", "server.key"):
        link = tls / name
        expected = "current/" + name
        if not link.is_symlink() or os.readlink(link) != expected:
            temporary = tls / ("." + name + "-next")
            temporary.unlink(missing_ok=True)
            temporary.symlink_to(expected)
            temporary.replace(link)
            changed = True
    infrastructure = root / "infrastructure"
    loaded = tls / ".loaded-fingerprint"
    if (infrastructure / ".env").exists():
        compose = [
            "/usr/bin/docker",
            "compose",
            "--project-name",
            config["project_name"],
            "-f",
            "compose.yaml",
            "-f",
            "compose.production.yaml",
        ]
        running = run(
            [*compose, "ps", "--status", "running", "--quiet", "nginx"], cwd=infrastructure
        ).stdout.strip()
        if running and (not loaded.exists() or loaded.read_text() != fingerprint):
            run(
                [
                    *compose,
                    "exec",
                    "-T",
                    "nginx",
                    "nginx",
                    "-t",
                    "-c",
                    "/etc/nginx/repairhub/nginx.conf",
                ],
                cwd=infrastructure,
            )
            run(
                [
                    *compose,
                    "exec",
                    "-T",
                    "nginx",
                    "nginx",
                    "-s",
                    "reload",
                    "-c",
                    "/etc/nginx/repairhub/nginx.conf",
                ],
                cwd=infrastructure,
            )
            loaded.write_text(fingerprint)
            loaded.chmod(0o600)
            os.chown(loaded, owner.st_uid, owner.st_gid)
            changed = True
    return changed


def main():
    config = json.loads(CONFIG.read_text())
    lock = Path(config["install_dir"]) / ".deployment-lock"
    owns_lock = "--deployment-lock-held" not in sys.argv[1:]
    if owns_lock:
        try:
            lock.mkdir(mode=0o700)
        except FileExistsError:
            print("Deployment aktiv; Erneuerung wird beim nächsten Lauf geprüft.")
            return
    elif not lock.is_dir():
        raise ValueError("Deployment-Sperre fehlt.")
    try:
        print("TLS_CHANGED" if publish(config) else "TLS_UNCHANGED")
    finally:
        if owns_lock:
            lock.rmdir()


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError):
        # Captured child output may contain account details; failures stay red.
        print("TLS-Ausstellung, Prüfung oder Nginx-Reload fehlgeschlagen.", file=sys.stderr)
        sys.exit(1)
