"""Konservatives Laufzeitinventar für das offizielle Garage-Scratch-Image.

Das Binary enthält keine cargo-auditable-Metadaten. Daher an Image-Digest und
Upstream-Commit gebundene Manifeste prüfen und alle normalen/Build-Abhängigkeiten
inklusive optionaler Features verfolgen. Nur reine Workspace-Testwurzeln entfallen.
"""

import hashlib
import json
import re
import tomllib
import urllib.request
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "deploy/security/garage-source.json"


def runtime_packages(documents):
    workspace = tomllib.loads(documents["Cargo.toml"])["workspace"]
    inherited = workspace["dependencies"]
    internal = {}
    for member in workspace["members"]:
        document = tomllib.loads(documents[member + "/Cargo.toml"])
        names = set()
        groups = [document, *document.get("target", {}).values()]
        for group in groups:
            for kind in ("dependencies", "build-dependencies"):
                for alias, specification in group.get(kind, {}).items():
                    if isinstance(specification, dict) and specification.get("workspace"):
                        specification = inherited[alias]
                    names.add(
                        specification.get("package", alias)
                        if isinstance(specification, dict)
                        else alias
                    )
        internal[document["package"]["name"]] = names
    packages = tomllib.loads(documents["Cargo.lock"])["package"]
    by_name = {}
    for package in packages:
        by_name.setdefault(package["name"], []).append(package)
    roots = by_name.get("garage", [])
    if len(roots) != 1:
        raise ValueError("Garage-Wurzel fehlt oder ist mehrdeutig.")
    visited = {}

    def visit(package):
        key = (package["name"], package["version"])
        if key in visited:
            return
        visited[key] = package
        for dependency in package.get("dependencies", []):
            parts = dependency.split()
            name = parts[0]
            # Ein lokales Manifest unterscheidet normale von reinen Testabhängigkeiten.
            # Bei Registry-Paketen nichts wegfiltern: Feature-Vereinigung konservativ prüfen.
            if package["name"] in internal and name not in internal[package["name"]]:
                continue
            candidates = by_name.get(name, [])
            if len(parts) > 1:
                candidates = [p for p in candidates if p["version"] == parts[1]]
            if len(candidates) != 1:
                raise ValueError("Unvollständiger oder mehrdeutiger Cargo-Abhängigkeitsgraph.")
            visit(candidates[0])

    visit(roots[0])
    return sorted(visited.values(), key=lambda p: (p["name"], p["version"]))


def prepare(destination: Path, image_reference: str):
    specification = json.loads(SOURCE.read_text())
    if image_reference != specification["image"]:
        raise ValueError("Garage-Quelle ist nicht für diesen Image-Digest geprüft.")
    commit = specification["commit"]
    if not re.fullmatch("[a-f0-9]{40}", commit):
        raise ValueError("Ungültiger Garage-Quellcommit.")
    documents = {}
    for name, expected in specification["files"].items():
        if not re.fullmatch(r"(?:[a-zA-Z0-9_-]+/)*Cargo\.(?:toml|lock)", name):
            raise ValueError("Ungültiger Manifestpfad.")
        url = f"https://git.deuxfleurs.fr/Deuxfleurs/garage/raw/commit/{commit}/{name}"
        with urllib.request.urlopen(url, timeout=30) as response:  # nosec B310: feste HTTPS-Origin
            data = response.read(2_000_001)
        if len(data) > 2_000_000 or hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("Garage-Quellmanifest stimmt nicht mit der Freigabe überein.")
        documents[name] = data.decode()
    packages = runtime_packages(documents)
    if len(packages) < 100:
        raise ValueError("Unvollständiges Garage-Laufzeitinventar.")
    destination.mkdir(parents=True, exist_ok=True)
    lines = ["version = 4"]
    for package in packages:
        lines.extend(
            [
                "",
                "[[package]]",
                "name = " + json.dumps(package["name"]),
                "version = " + json.dumps(package["version"]),
            ]
        )
        for key in ("source", "checksum"):
            if key in package:
                lines.append(key + " = " + json.dumps(package[key]))
    (destination / "Cargo.lock").write_text("\n".join(lines) + "\n")
    evidence = {
        "image": image_reference,
        "source_commit": commit,
        "source_manifests": specification["files"],
        "runtime_package_count": len(packages),
        "coverage": "source-lockfile, conservative normal/build dependency closure",
        "limitation": (
            "Upstream binary has no embedded Rust package inventory; "
            "source linkage relies on the pinned official release."
        ),
    }
    (destination / "provenance.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return evidence
