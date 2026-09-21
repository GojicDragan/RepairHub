"""Absenden echter Benutzerformulare prüfen, einschliesslich Autofill ohne Ereignisse."""

import pytest
from playwright.sync_api import expect

PAGES = ["/register", "/login", "/reset", "/confirm"]


@pytest.mark.parametrize("path", PAGES)
def test_identity_button_tracks_required_fields(page, path):
    page.goto(path)
    form = page.locator("[data-form-completion]")
    button = form.locator('[type="submit"]')
    fields = form.locator("[data-required-input]")
    expect(button).to_be_disabled()
    for index in range(fields.count()):
        expect(button).to_be_disabled()
        field = fields.nth(index)
        field.fill("lea@example.org" if field.get_attribute("type") == "email" else "valid-input")
    expect(button).to_be_enabled()
    fields.first.fill("")
    expect(button).to_be_disabled()
    fields.first.fill("   ")
    expect(button).to_be_disabled()
    # Passwortmanager lösen beim Befüllen nicht immer input/change-Ereignisse aus.
    fields.first.evaluate("field => { field.value = 'lea@example.org'; }")
    expect(button).to_be_enabled()
    form.evaluate("form => form.reset()")
    expect(button).to_be_disabled()


@pytest.mark.parametrize("page", [False], indirect=True)
@pytest.mark.parametrize("path", PAGES)
def test_identity_forms_remain_usable_without_javascript(page, path):
    page.goto(path)
    form = page.locator("[data-form-completion]")
    expect(form.locator('[type="submit"]')).to_be_enabled()
    assert form.evaluate("form => form.checkValidity()") is False
    assert form.locator("[data-required-input]:not([required])").count() == 0


@pytest.mark.parametrize("path", ["/confirm", "/reset", "/register"])
def test_email_actions_require_email_format(page, path):
    page.goto(path)
    for field in page.locator('[data-required-input]:not([name="email"])').all():
        field.fill("valid-input")
    email = page.locator('[name="email"]')
    button = page.locator('[data-form-completion] [type="submit"]')
    for invalid in ["", "not-an-email", "lea@", "@example.org", "lea@@example.org"]:
        email.fill(invalid)
        expect(button).to_be_disabled()
    email.fill("lea+repair@example.org")
    expect(button).to_be_enabled()
    email.fill("invalid-again")
    expect(button).to_be_disabled()


@pytest.mark.parametrize("path", ["/confirm", "/reset", "/register"])
def test_email_feedback_uses_branded_inline_messages(page, path):
    page.goto(path)
    for field in page.locator('[data-required-input]:not([name="email"])').all():
        field.fill("valid-input")
    form = page.locator("[data-form-completion]")
    email = form.locator('[name="email"]')
    error = form.locator('[data-field-error="email"]')
    required = form.locator('[data-field-error="required"]')
    expect(error).to_be_hidden()
    expect(required).to_be_hidden()
    email.fill("invalid")
    expect(error).to_be_hidden()
    email.blur()
    expect(error).to_be_visible()
    expect(email).to_have_attribute("aria-invalid", "true")
    assert form.evaluate("form => form.noValidate")
    assert error.evaluate("element => getComputedStyle(element).color") == "rgb(184, 64, 32)"
    german = page.locator("html").get_attribute("lang").startswith("de")
    expect(error).to_have_text(
        "Gib eine gültige E-Mail-Adresse ein, zum Beispiel name@example.org."
        if german
        else "Enter a valid email address, for example name@example.org."
    )
    email.fill("lea@example.org")
    expect(error).to_be_hidden()
    expect(email).to_have_attribute("aria-invalid", "false")
    expect(form.locator('[type="submit"]')).to_be_enabled()
    email.fill("")
    expect(required).to_be_visible()
    expect(form.locator('[type="submit"]')).to_be_disabled()
    form.evaluate("form => form.reset()")
    expect(required).to_be_hidden()


def test_registration_requires_matching_passwords(page):
    page.goto("/register")
    page.locator('[name="username"]').fill("Lea")
    page.locator('[name="email"]').fill("lea@example.org")
    password = page.locator('[name="password"]')
    confirmation = page.locator('[name="password_confirm"]')
    button = page.locator('[data-form-completion] [type="submit"]')
    error = page.locator('[data-field-error="password-match"]')
    password.fill("secure phrase ")
    confirmation.fill("secure phrase")
    confirmation.blur()
    expect(button).to_be_disabled()
    expect(error).to_be_visible()
    expect(confirmation).to_have_attribute("aria-invalid", "true")
    german = page.locator("html").get_attribute("lang").startswith("de")
    expect(error).to_have_text(
        "Die Passwörter müssen übereinstimmen." if german else "Passwords must match."
    )
    confirmation.fill("secure phrase ")
    expect(button).to_be_enabled()
    expect(error).to_be_hidden()
    password.fill("a different phrase")
    expect(button).to_be_disabled()
    expect(error).to_be_visible()
    confirmation.fill("a different phrase")
    expect(button).to_be_enabled()
    confirmation.fill("")
    expect(button).to_be_disabled()


def test_registration_requires_minimum_password_length(page):
    page.goto("/register")
    page.locator('[name="username"]').fill("Lea")
    page.locator('[name="email"]').fill("lea@example.org")
    password = page.locator('[name="password"]')
    confirmation = page.locator('[name="password_confirm"]')
    button = page.locator('[data-form-completion] [type="submit"]')
    error = page.locator('[data-field-error="password-length"]')
    for value in ["1234567", "🔧" * 4]:
        password.fill(value)
        confirmation.fill(value)
        password.blur()
        expect(button).to_be_disabled()
        expect(error).to_be_visible()
    german = page.locator("html").get_attribute("lang").startswith("de")
    expect(error).to_have_text(
        "Verwende mindestens 8 Zeichen." if german else "Use at least 8 characters."
    )
    password.fill("12345678")
    confirmation.fill("12345678")
    expect(button).to_be_enabled()
    expect(error).to_be_hidden()
    password.fill("1234567")
    confirmation.fill("1234567")
    expect(button).to_be_disabled()
