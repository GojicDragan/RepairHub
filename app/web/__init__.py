"""Weboberfläche; Fachzugriff ausschliesslich über die vier Verwaltungsservices."""

from flask import Blueprint

blueprint = Blueprint("web", __name__, template_folder="templates", static_folder="static")

from app.web.routes import health, home  # noqa: E402, F401
