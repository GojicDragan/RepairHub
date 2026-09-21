"""Geprüfte Scannerprogramme installieren, ohne entfernte Installationsskripte auszuführen."""

import argparse
import hashlib
import io
import platform
import subprocess
import tarfile
from pathlib import Path

SCANNERS = {
    "actionlint": (
        "https://github.com/rhysd/actionlint/releases/download/v1.7.12/"
        "actionlint_1.7.12_linux_amd64.tar.gz",
        "8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8",
    ),
    "gitleaks": (
        "https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/"
        "gitleaks_8.30.1_linux_x64.tar.gz",
        "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb",
    ),
    "trivy": (
        "https://github.com/aquasecurity/trivy/releases/download/v0.74.0/"
        "trivy_0.74.0_Linux-64bit.tar.gz",
        "2ae6fe3ee734b7fdf11335663e18c75ea12dccc76062f09f164a3b0f8be4371a",
    ),
}


def install(destination: Path, names: list[str]) -> None:
    if platform.system() != "Linux" or platform.machine() not in {"x86_64", "AMD64"}:
        raise SystemExit("Scanner-Binaries benötigen Linux amd64.")
    destination.mkdir(parents=True, exist_ok=True)
    for name in names:
        url, expected = SCANNERS[name]
        payload = subprocess.run(
            [
                "curl",
                "--fail",
                "--location",
                "--silent",
                "--show-error",
                "--proto",
                "=https",
                "--tlsv1.2",
                "--max-time",
                "120",
                url,
            ],
            check=True,
            capture_output=True,
        ).stdout
        if hashlib.sha256(payload).hexdigest() != expected:
            raise SystemExit(f"Ungültige Prüfsumme für {name}.")
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
            # Genau eine reguläre Datei kopieren; keine vom Archiv vorgegebenen Pfade entpacken.
            member = archive.getmember(name)
            if not member.isfile():
                raise SystemExit(f"Ungültiges Binary für {name}.")
            source = archive.extractfile(member)
            if source is None:
                raise SystemExit(f"Fehlendes Binary für {name}.")
            binary = destination / name
            binary.write_bytes(source.read())
            binary.chmod(0o755)
        print(f"{name}: Binary-Prüfsumme bestätigt.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    parser.add_argument("--only", nargs="+", choices=SCANNERS, default=list(SCANNERS))
    args = parser.parse_args()
    install(args.destination, args.only)
