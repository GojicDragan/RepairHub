"""Quellcode und öffentliche T13-Unterlagen ohne lokale Laufzeitdaten bündeln."""

import hashlib
import json
import subprocess
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def main():
    root = Path(git("rev-parse", "--show-toplevel"))
    if root != Path.cwd():
        raise SystemExit("Bitte im Repository-Hauptverzeichnis ausführen.")
    paths = set(git("ls-files", "-z").split("\0"))
    # Nur bekannte neue Dokumentationspfade ergänzen, niemals pauschal das Verzeichnis zippen.
    for directory in (
        "docs/user-guide",
        "docs/diagrams",
        "docs/submission",
        "scripts/documentation",
    ):
        paths.update(str(path) for path in Path(directory).rglob("*") if path.is_file())
    paths.add("docs/t13-validation.md")
    files = []
    forbidden = {".git", ".venv", "__pycache__", ".qa", "secrets", "backups", "artifacts"}
    for name in sorted(paths):
        path = Path(name)
        if not name or not path.is_file():
            continue
        if path.is_symlink() or forbidden.intersection(path.parts):
            continue
        if path.name.endswith((".pyc", ".key", ".pem", ".dump")):
            continue
        if path.name.endswith(".env") or (
            path.name.startswith(".env") and path.name != ".env.example"
        ):
            continue
        files.append(path)
    output = Path("artifacts/submission")
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "base_commit": git("rev-parse", "HEAD"),
        "working_tree": bool(git("status", "--porcelain")),
        "files": [],
    }
    with ZipFile(output / "RepairHub-source.zip", "w", ZIP_DEFLATED) as archive:
        for path in files:
            content = path.read_bytes()
            archive.writestr("RepairHub/" + path.as_posix(), content)
            # Pfad und Hash getrennt benennen: Ein Dateiname mit „api_key“
            # macht seine Prüfsumme dadurch nicht scheinbar zu einem Zugangsschlüssel.
            manifest["files"].append(
                {"path": path.as_posix(), "sha256": hashlib.sha256(content).hexdigest()}
            )
        archive.writestr("RepairHub/SOURCE-MANIFEST.json", json.dumps(manifest, indent=2) + "\n")
    manifest["archive_sha256"] = hashlib.sha256(
        (output / "RepairHub-source.zip").read_bytes()
    ).hexdigest()
    (output / "source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"{len(files)} Dateien: {output / 'RepairHub-source.zip'}")


if __name__ == "__main__":
    main()
