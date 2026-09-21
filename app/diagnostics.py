"""Technische Diagnoseschnittstelle zwischen HTTP-Bereitschaft und Datenzugriff."""

from flask import current_app

from app.data.health import database_ready


def check_readiness() -> bool:
    ready = database_ready()
    if not ready:
        current_app.logger.warning("Bereitschaftsprüfung: Datenbank nicht verfügbar.")
    return ready
