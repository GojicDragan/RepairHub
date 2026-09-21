"""Weboberfläche; fachliche Aktionen laufen über die Anwendungsfälle der Domänen."""

from flask import Blueprint

blueprint = Blueprint("web", __name__, template_folder="templates", static_folder="static")

# Die Routen dekorieren den oben erzeugten Blueprint beim Import; deshalb erst
# nach seiner Erstellung laden, um einen zirkulären Initialisierungszugriff zu vermeiden.
from app.web.routes import health, home  # noqa: E402, F401
