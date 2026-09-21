"""Verschlüsselt ausschliesslich Backup-Artefakte; Passphrase nie in argv oder Logs."""

import argparse
import os
import subprocess
import tempfile
from pathlib import Path


def encrypt(source: Path, destination: Path, passphrase: str) -> None:
    backups = sorted(source.glob("*/*.dump"))
    if not backups:
        return
    if len(passphrase) < 32 or any(char in passphrase for char in "\r\n\0"):
        raise ValueError("Gültige Backup-Passphrase mit mindestens 32 Zeichen erforderlich.")
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Eigene GnuPG-Konfiguration und kein Passwort-Cache auf dem Runner.
    # https://www.gnupg.org/documentation/manuals/gnupg/GPG-Esoteric-Options.html
    with tempfile.TemporaryDirectory() as home:
        for backup in backups:
            output = destination / (backup.parent.name + "-" + backup.name + ".gpg")
            result = subprocess.run(
                [
                    "gpg",
                    "--homedir",
                    home,
                    "--batch",
                    "--yes",
                    "--pinentry-mode",
                    "loopback",
                    "--no-symkey-cache",
                    "--passphrase-fd",
                    "0",
                    "--symmetric",
                    "--cipher-algo",
                    "AES256",
                    "--output",
                    str(output),
                    str(backup),
                ],
                input=passphrase.encode() + b"\n",
                capture_output=True,
                check=False,
            )
            if result.returncode:
                output.unlink(missing_ok=True)
                raise RuntimeError("Backup-Verschlüsselung fehlgeschlagen.")
            output.chmod(0o600)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    encrypt(args.source, args.destination, os.environ.get("BACKUP_PASSPHRASE", ""))
