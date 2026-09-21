"""Fehlerdarstellung bleibt deutsch, getrennt und frei von internen Details."""

import logging

import pytest
from flask import abort, request
from werkzeug.exceptions import TooManyRequests


@pytest.mark.parametrize("path", ["/missing", "/api", "/api/missing", "/api-other"])
def test_unknown_routes_use_correct_presentation(client, path):
    response = client.get(path)
    assert response.status_code == 404
    is_api = path == "/api" or path.startswith("/api/")
    assert response.is_json == is_api
    if is_api:
        assert response.json == {
            "error": {
                "status": 404,
                "title": "Seite nicht gefunden",
                "message": "Die angeforderte Ressource wurde nicht gefunden.",
            }
        }
    else:
        assert 'lang="de-CH"' in response.text
        assert "Zur Startseite" in response.text
        assert "Hauptnavigation" in response.text


@pytest.mark.parametrize("path", ["/broken", "/api/broken"])
def test_unexpected_failure_hides_exception_in_response_and_log(app, caplog, path):
    @app.get(path)
    def broken():
        raise RuntimeError("secret-token-and-database-credentials")

    with caplog.at_level(logging.ERROR):
        response = app.test_client().get(path)
    assert response.status_code == 500
    assert response.is_json == path.startswith("/api/")
    assert "secret-token" not in response.text + caplog.text
    assert "Traceback" not in response.text + caplog.text
    assert "Interner Anwendungsfehler." in caplog.text
    assert "Typ=RuntimeError" in caplog.text
    assert "Endpoint=broken" in caplog.text
    assert ".broken:" in caplog.text


def test_http_errors_preserve_headers_and_hide_descriptions(app):
    @app.post("/api/post-only")
    def post_only():
        return "unused"

    @app.get("/api/rate-limit")
    def rate_limit():
        raise TooManyRequests(description="private diagnostic", retry_after=30)

    @app.get("/private-description")
    def description():
        abort(403, description="secret-token")

    client = app.test_client()
    response = client.get("/api/post-only")
    assert response.status_code == 405
    assert "POST" in response.headers["Allow"]
    assert response.json["error"]["status"] == 405
    response = client.get("/api/rate-limit")
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "30"
    assert "private diagnostic" not in response.text
    assert "secret-token" not in client.get("/private-description").text


def test_csrf_and_request_size_errors_are_readable(app):
    @app.post("/form")
    def form():
        return request.get_data()

    client = app.test_client()
    assert "Ungültige Anfrage" in client.post("/form").text
    response = client.post("/form", data=b"x" * (app.config["MAX_CONTENT_LENGTH"] + 1))
    assert response.status_code == 413
    assert "Anfrage zu gross" in response.text


def test_head_and_options_remain_available(client):
    assert client.head("/").status_code == 200
    response = client.head("/api/missing")
    assert response.status_code == 404 and response.data == b""
    assert client.options("/").status_code == 200
