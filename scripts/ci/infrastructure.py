"""Unveränderliche Referenzen für die offiziellen Nginx- und PostgreSQL-Images laden."""

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PINNED_IMAGE = re.compile(r"[a-z0-9][a-z0-9.:/_-]+@sha256:[a-f0-9]{64}\Z")
VERSION = re.compile(r"[a-z0-9][a-z0-9._-]{0,127}\Z")


def load(path: Path | None = None) -> dict:
    if path is None:
        path = Path(
            os.environ.get("REPAIRHUB_INFRASTRUCTURE_FILE", ROOT / "deploy/infrastructure.json")
        )
    configuration = json.loads(path.read_text())
    if (
        not isinstance(configuration, dict)
        or type(configuration.get("schema_version")) is not int
        or configuration["schema_version"] != 1
    ):
        raise ValueError("Ungültige Infrastruktur-Konfiguration.")
    for field in ("database_contract", "postgres_version"):
        if not isinstance(configuration.get(field), str) or not VERSION.fullmatch(
            configuration[field]
        ):
            raise ValueError(f"Ungültige Infrastruktur-Version: {field}.")
    for field in ("nginx_image", "postgres_image"):
        value = configuration.get(field)
        if not isinstance(value, str) or not PINNED_IMAGE.fullmatch(value):
            raise ValueError(f"Infrastruktur-Image benötigt einen festen Digest: {field}.")
    return configuration
