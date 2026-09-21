"""HTML-Fehlerdarstellung ohne Zugriff auf fachliche Komponenten."""

from flask import render_template
from werkzeug.wrappers import Response


def render_error(response: Response, title: str, message: str) -> Response:
    response.set_data(
        render_template("error.html", status=response.status_code, title=title, message=message)
    )
    response.content_type = "text/html; charset=utf-8"
    return response
