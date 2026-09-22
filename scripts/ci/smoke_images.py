"""Archivierte Image-Kombination in einem privaten, kurzlebigen Docker-Netz starten."""

import argparse
import json
import os
from pathlib import Path

if __package__:
    from .images import docker, verify
    from .isolated_runtime import isolated_runtime
else:
    from images import docker, verify
    from isolated_runtime import isolated_runtime


def main(directory: Path, commit: str) -> None:
    manifest = verify(directory, commit)
    reports = Path("reports/build")
    reports.mkdir(parents=True, exist_ok=True)
    evidence = {"commit": commit, "images": manifest["images"], "passed": False}
    try:
        with isolated_runtime(manifest, public_url="https://nginx:8443") as runtime:
            # Produktions-Hostprüfung einschalten und den echten Image-Healthcheck ausführen.
            docker("exec", runtime.app, "python", "healthcheck.py", capture=True)
            docker(
                "exec",
                runtime.nginx,
                "wget",
                "--no-check-certificate",
                "--spider",
                "-q",
                "--header=Host: nginx:8443",
                "https://127.0.0.1:8443/health/ready",
                capture=True,
            )
            if json.loads(Path("deploy/capabilities.json").read_text())["authenticated_api"]:
                docker(
                    "exec",
                    runtime.app,
                    "python",
                    "-c",
                    Path("tests/support/api_fixture.py").read_text(),
                    capture=True,
                )
            evidence["checks"] = [
                "Authentifizierte Lese-API mit separatem Fixture-Konto und negativen Zugriffen",
                "Interne App-/Nginx-Checks mit produktiver Hostbeschränkung",
                "PostgreSQL bereit",
                "Gunicorn bereit",
                "Nginx HTTPS mit CA-Prüfung",
                "Internes Netzwerk ohne veröffentlichte Ports",
            ]
        # Eine fehlgeschlagene Bereinigung darf keinen erfolgreichen Prüfbericht hinterlassen.
        evidence["passed"] = True
    finally:
        (reports / "smoke.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print("Archivierte Image-Kombination mit PostgreSQL und HTTPS geprüft.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=Path("artifacts/images"))
    parser.add_argument("--commit", default=os.environ.get("GITHUB_SHA", ""))
    args = parser.parse_args()
    main(args.directory, args.commit)
