"""Browser → Nginx → Flask-Security → PostgreSQL und isolierter STARTTLS-Empfänger."""

import re
import time
import uuid
from email import policy
from email.parser import BytesParser

import pytest
from playwright.sync_api import expect

from scripts.ci.images import docker


@pytest.mark.parametrize(
    "page",
    [
        True,
        False,
        {"javascript": True, "locale": "de-CH"},
        {"javascript": False, "locale": "de-CH"},
    ],
    indirect=True,
    ids=["en-javascript", "en-no-javascript", "de-javascript", "de-no-javascript"],
)
def test_register_confirm_login_and_logout(page, live_application):
    german = page.evaluate("navigator.language").startswith("de")
    login_label = "Anmelden" if german else "Log in"
    logout_label = "Abmelden" if german else "Log out"
    username = "user" + uuid.uuid4().hex[:10]
    email = username + "@example.org"
    password = "example test phrase"
    errors = []
    page.on("pageerror", lambda error: errors.append(error))
    page.goto("/register")
    page.locator('[name="username"]').fill(username)
    page.locator('[name="email"]').fill(email)
    page.locator('[name="password"]').fill(password)
    page.locator('[name="password_confirm"]').fill(password)
    page.locator('[type="submit"]').click()
    page.wait_for_url("**/")
    assert (
        page.get_by_role("navigation")
        .get_by_role("link", name=login_label, exact=True)
        .is_visible()
    )
    deadline = time.monotonic() + 10
    link = None
    while time.monotonic() < deadline and link is None:
        for path in live_application.mail_directory.glob("*.eml"):
            message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
            if message["To"] == email:
                body = message.get_body(preferencelist=("plain",)).get_content()
                assert password not in body
                assert ("Willkommen bei RepairHub." if german else "Welcome to RepairHub.") in body
                link = re.search(r"https?://[^\s]+/confirm/[^\s]+", body).group(0)
                break
        if link is None:
            page.wait_for_timeout(100)
    assert link is not None, "Bestätigungsmail fehlt im isolierten Postfach."
    page.goto("/login")
    page.locator('[name="identity"]').fill(email)
    page.locator('[name="password"]').fill(password)
    page.locator('[type="submit"]').click()
    assert page.get_by_role("heading", name=login_label, exact=True).is_visible()
    assert page.get_by_role("button", name=logout_label).count() == 0
    page.goto(link)
    access_log = docker("logs", live_application.nginx, capture=True)
    assert link.rsplit("/", 1)[-1] not in access_log
    assert "/confirm/[redacted]" in access_log
    page.locator('[name="identity"]').fill(email)
    page.locator('[name="password"]').fill(password)
    page.locator('[type="submit"]').click()
    page.wait_for_url("**/")
    page.get_by_role("button", name=logout_label).click()
    page.wait_for_url("**/")
    assert (
        page.get_by_role("navigation")
        .get_by_role("link", name=login_label, exact=True)
        .is_visible()
    )
    page.goto("/login")
    page.get_by_role("link", name="Passwort vergessen?" if german else "Forgot password?").click()
    page.locator('[name="email"]').fill(email)
    page.locator('[type="submit"]').click()
    reset_url = None
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and reset_url is None:
        for path in live_application.mail_directory.glob("*.eml"):
            message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
            if message["To"] != email:
                continue
            body = message.get_body(preferencelist=("plain",)).get_content()
            match = re.search(r"https?://[^\s]+/reset/[^\s]+", body)
            if match:
                reset_url = match.group(0)
                assert ("eine Stunde" if german else "one hour") in body
                assert "#243b35" in message.get_body(preferencelist=("html",)).get_content()
                break
        if reset_url is None:
            page.wait_for_timeout(100)
    assert reset_url is not None
    page.goto(reset_url)
    page.locator('[name="password"]').fill("1234567")
    page.locator('[name="password_confirm"]').fill("1234567")
    expect(page.locator('[type="submit"]')).to_be_disabled()
    expect(page.locator('[data-field-error="password-length"]')).to_be_visible()
    page.locator('[name="password"]').fill("new example test phrase")
    page.locator('[name="password_confirm"]').fill("different reset phrase")
    page.locator('[name="password_confirm"]').blur()
    expect(page.locator('[type="submit"]')).to_be_disabled()
    expect(page.locator('[data-field-error="password-match"]')).to_be_visible()
    page.locator('[name="password_confirm"]').fill("new example test phrase")
    page.locator('[type="submit"]').click()
    page.wait_for_url("**/login")
    page.locator('[name="identity"]').fill(username)
    page.locator('[name="password"]').fill("new example test phrase")
    page.locator('[type="submit"]').click()
    page.wait_for_url("**/")
    page.get_by_role("button", name=logout_label).click()
    access_log = docker("logs", live_application.nginx, capture=True)
    assert reset_url.rsplit("/", 1)[-1] not in access_log
    assert "/reset/[redacted]" in access_log
    assert not errors


def test_registered_users_survive_database_container_recreation(live_application):
    import json
    import tempfile
    from pathlib import Path

    from scripts.ci.isolated_runtime import ready

    runtime = live_application
    query = (
        "from app import create_app; from app.extensions import db; "
        "from sqlalchemy import text; app=create_app(); "
        "ctx=app.app_context(); ctx.push(); "
        "print(db.session.execute(text('select count(*) from users')).scalar())"
    )
    before = docker("exec", runtime.app, "python", "-c", query, capture=True)
    assert int(before) >= 2
    old = json.loads(docker("inspect", runtime.db, capture=True))[0]
    volume = next(mount["Name"] for mount in old["Mounts"] if mount["Type"] == "volume")
    # Nur die eigene DB-Fixture ersetzen, ihr Volume ausdrücklich weiterverwenden.
    with tempfile.TemporaryDirectory(prefix="repairhub-db-recreate-") as directory:
        env = Path(directory) / "database.env"
        env.touch(mode=0o600)
        env.write_text("\n".join(old["Config"]["Env"]) + "\n")
        docker("rm", "--force", runtime.db, capture=True)
        docker(
            "run",
            "--detach",
            "--name",
            runtime.db,
            "--network",
            runtime.network,
            "--network-alias",
            "db",
            "--mount",
            f"type=volume,src={volume},dst=/var/lib/postgresql/data",
            "--env-file",
            str(env),
            old["Config"]["Image"],
            capture=True,
        )
    ready(runtime.db, ["pg_isready", "-U", "repairhub_test", "-d", "repairhub_test"])
    assert docker("exec", runtime.app, "python", "-c", query, capture=True) == before
