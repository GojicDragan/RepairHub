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
        ({"REPAIRHUB_ENV": "production", "TESTING": False, "DEBUG": True}, "Production"),
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


@pytest.mark.parametrize("environment,reloads", [("development", True), ("production", False)])
def test_template_changes_reload_only_in_development(app_config, tmp_path, environment, reloads):
    import os

    from flask import render_template
    from jinja2 import FileSystemLoader

    application = create_app({**app_config, "REPAIRHUB_ENV": environment, "TESTING": False})
    application.jinja_loader = FileSystemLoader(tmp_path)
    template = tmp_path / "live.html"
    template.write_text("old form")
    application.add_url_rule("/template-check", view_func=lambda: render_template("live.html"))
    client = application.test_client()
    assert client.get("/template-check").text == "old form"
    previous = template.stat().st_mtime
    template.write_text("new form with debounce hook")
    os.utime(template, (previous + 2, previous + 2))
    expected = "new form with debounce hook" if reloads else "old form"
    assert client.get("/template-check").text == expected
    assert application.debug is False
