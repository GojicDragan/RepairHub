"""REST-API; Fachzugriff ausschliesslich über Benutzer- und Reparaturverwaltung."""

from flask import Blueprint

blueprint = Blueprint("api", __name__)
