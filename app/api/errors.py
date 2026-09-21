"""Einheitliche JSON-Fehlerdarstellung, auch für unbekannte API-Routen."""

from flask import json
from werkzeug.wrappers import Response


def render_error(response: Response, title: str, message: str) -> Response:
    # Die vorhandene Response weiterverwenden: Status und Protokollheader wie
    # Allow (405) bleiben erhalten, nur Darstellung und Content-Type ändern sich.
    response.set_data(
        json.dumps(
            {
                "error": {
                    "status": response.status_code,
                    "title": title,
                    "message": message,
                }
            }
        )
    )
    response.content_type = "application/json"
    return response
