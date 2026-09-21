"""HTTP-Routen mit Flask-Erweiterungen, Diagnose und PostgreSQL integrieren."""

import logging

import pytest

from app.extensions import db


def test_readiness_reaches_postgres(postgres_app):
    with postgres_app.app_context():
        assert db.engine.dialect.name == "postgresql"
    response = postgres_app.test_client().get("/health/ready")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ready"}


def test_readiness_fails_without_database_and_hides_details(client, caplog):
    with caplog.at_level(logging.WARNING):
        response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.get_json() == {"status": "unavailable"}
    combined_output = response.get_data(as_text=True) + caplog.text
    assert "Readiness check: database unavailable." in caplog.text
    for sensitive_fragment in ("psycopg", "test:test", "127.0.0.1", "OperationalError"):
        assert sensitive_fragment not in combined_output


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_readiness_rejects_state_changing_methods(client, method):
    # CSRF kann schreibende Anfragen vor Flask-Methodenprüfung abweisen.
    response = getattr(client, method)("/health/ready")
    assert response.status_code in {400, 405}


def test_home_and_static_are_available(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Manage your personal repairs." in response.get_data(as_text=True)
    assert client.get("/static/app.css").status_code == 200


def test_csrf_is_initialized(app):
    @app.post("/test-form")
    def form_submission():
        return "unexpected"

    assert app.test_client().post("/test-form").status_code == 400


@pytest.mark.parametrize(
    "language,label", [("en", "Email or username"), ("de", "E-Mail oder Benutzername")]
)
def test_login_has_one_identity_input_before_password(client, language, label):
    html = client.get("/login", headers={"Accept-Language": language}).text
    assert label in html
    assert html.index('name="identity"') < html.index('name="password"')
    assert 'name="email"' not in html
    assert 'name="username"' not in html
    assert 'autocomplete="username"' in html
