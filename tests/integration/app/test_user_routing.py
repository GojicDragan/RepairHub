"""Echte HTTP-Endpunkte müssen injizierte Anwendungsfälle statt Bibliotheks-Views aufrufen."""

import importlib
import re

import pytest

from app.domains.users.dto import UserResult


@pytest.mark.parametrize(
    "path,slice_name,class_name,fields",
    [
        (
            "/register",
            "register_user",
            "RegisterUser",
            {
                "username": "Lea",
                "email": "lea@example.org",
                "password": "secret",
                "password_confirm": "secret",
            },
        ),
        ("/login", "login_user", "LoginUser", {"identity": "Lea", "password": "secret"}),
        ("/logout", "logout_user", "LogoutUser", {}),
        ("/confirm", "resend_confirmation", "ResendConfirmation", {"email": "lea@example.org"}),
        ("/reset", "request_password_reset", "RequestPasswordReset", {"email": "lea@example.org"}),
        (
            "/reset/token",
            "reset_password",
            "ResetPassword",
            {"password": "secret", "password_confirm": "secret"},
        ),
    ],
)
def test_post_enters_handler_without_touching_database(
    client, monkeypatch, path, slice_name, class_name, fields
):
    calls = []
    cls = getattr(importlib.import_module(f"app.domains.users.{slice_name}.handler"), class_name)
    monkeypatch.setattr(cls, "execute", lambda self, command: calls.append(command) or UserResult())
    page = client.get("/login")
    token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page.text).group(1)
    response = client.post(
        path, data={**fields, "csrf_token": token}, headers={"Referer": "https://localhost" + path}
    )
    assert response.status_code in {200, 302}
    assert len(calls) == 1
    for key, value in fields.items():
        assert getattr(calls[0], key) == value


@pytest.mark.parametrize(
    "path,slice_name,class_name",
    [
        ("/confirm/token", "confirm_email", "ConfirmEmail"),
        ("/reset/token", "check_reset_link", "CheckResetLink"),
    ],
)
def test_token_get_enters_handler(client, monkeypatch, path, slice_name, class_name):
    calls = []
    cls = getattr(importlib.import_module(f"app.domains.users.{slice_name}.handler"), class_name)
    monkeypatch.setattr(cls, "execute", lambda self, command: calls.append(command) or UserResult())
    assert client.get(path).status_code in {200, 302}
    assert len(calls) == 1 and calls[0].token == "token"


def test_library_blueprint_is_disabled_and_routes_have_single_owner(app):
    assert app.extensions["security"].register_blueprint is False
    for endpoint in [
        "register",
        "login",
        "logout",
        "send_confirmation",
        "confirm_email",
        "forgot_password",
        "reset_password",
    ]:
        name = "security." + endpoint
        assert app.view_functions[name].__module__ == "app.web.routes.users"
        assert len(list(app.url_map.iter_rules(name))) == 1
