"""Deployment-Prüfungen mit der Einführung von Schema und authentifizierter API erzwingen."""

import json
import subprocess
import sys
from pathlib import Path


def validate(capabilities: dict, migration_files: list[Path], routes: set[str]) -> None:
    expected = {
        "schema_migrations": bool(migration_files),
        "authenticated_api": "/api/auth/token" in routes,
    }
    if capabilities != expected:
        raise ValueError("deploy/capabilities.json stimmt nicht mit Schema und API überein.")
    if expected["schema_migrations"] and not Path("migrations/alembic.ini").is_file():
        raise ValueError("Migrationen vorhanden, aber Alembic-Konfiguration fehlt.")


def main() -> None:
    from app import create_app

    capabilities = json.loads(Path("deploy/capabilities.json").read_text())
    app = create_app()
    migration_files = list(Path("migrations/versions").glob("*.py"))
    routes = {rule.rule for rule in app.url_map.iter_rules()}
    validate(capabilities, migration_files, routes)
    if capabilities["schema_migrations"]:
        for operation in ("upgrade", "check"):
            subprocess.run(
                [sys.executable, "-m", "flask", "--app", "app:create_app", "db", operation],
                check=True,
            )
    else:
        print("T02: Noch keine Schemamigrationen; ab erster Revision wird Migration geprüft.")
    if not capabilities["authenticated_api"]:
        print("T02: Authentifizierter API-Smoke-Test wird mit T09 verbindlich aktiviert.")


if __name__ == "__main__":
    main()
