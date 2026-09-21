"""Factory verbindet Konfiguration und Flask-Komponenten korrekt."""

import pytest

from app import create_app


def test_factory_instances_have_separate_configuration(app_config):
    first = create_app(app_config)
    second = create_app({**app_config, "SERVER_NAME": "second.example"})
    assert first is not second
    assert first.config["SERVER_NAME"] is None
    assert second.config["SERVER_NAME"] == "second.example"


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"SECRET_KEY": ""}, "SECRET_KEY"),
        ({"SQLALCHEMY_DATABASE_URI": "sqlite:///not-supported.db"}, "DATABASE_URL"),
        ({"REPAIRHUB_ENV": "production", "TESTING": False, "DEBUG": True}, "Produktion"),
    ],
)
def test_factory_enforces_configuration_validation(app_config, override, message):
    app_config.update(override)
    with pytest.raises(ValueError, match=message):
        create_app(app_config)


def test_factory_override_selects_matching_environment_defaults(app_config, monkeypatch):
    monkeypatch.setenv("REPAIRHUB_ENV", "development")
    production = create_app({**app_config, "REPAIRHUB_ENV": "production", "TESTING": False})
    assert production.config["SESSION_COOKIE_SECURE"] is True
    development = create_app({**app_config, "REPAIRHUB_ENV": "development"})
    assert development.config["SESSION_COOKIE_SECURE"] is False


def test_factory_keeps_blueprints_and_extensions_separate(app_config):
    first = create_app(app_config)
    second = create_app(app_config)
    first.add_url_rule("/only-first", view_func=lambda: "ok")
    assert first.test_client().get("/only-first").status_code == 200
    assert second.test_client().get("/only-first").status_code == 404
    assert {"web", "api"} <= first.blueprints.keys()
    assert {"sqlalchemy", "migrate", "csrf"} <= first.extensions.keys()


def test_flash_messages_are_escaped_and_readable_without_javascript(app_config):
    client = create_app(app_config).test_client()
    with client.session_transaction() as session:
        session["_flashes"] = [("message", "<script>alert('unsafe')</script>")]
    response = client.get("/")
    assert b"&lt;script&gt;" in response.data
    assert b"<script>alert" not in response.data
    assert b"data-dismiss-notification hidden" in response.data
    assert b"data-notification" in response.data
