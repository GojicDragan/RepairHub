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
