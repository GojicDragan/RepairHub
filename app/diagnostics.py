"""Technische Diagnoseschnittstelle zwischen HTTP-Bereitschaft und Datenzugriff."""

# Technische Betriebsdiagnose ausserhalb von app.domains: Die Flask-/DB-Anbindung
# hier ist kein Vorbild für fachliche Anwendungsfälle, die ihre Ports injiziert erhalten.
from flask import current_app

from app.data.health import database_ready


def check_readiness() -> bool:
    ready = database_ready()
    if not ready:
        current_app.logger.warning("Readiness check: database unavailable.")
    return ready
