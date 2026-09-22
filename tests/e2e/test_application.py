"""Browser → HTTPS/Nginx → Gunicorn/Flask → PostgreSQL, ohne Anwendungs-Mocks."""

import pytest

from scripts.ci.images import docker
from scripts.ci.isolated_runtime import ready


def test_home_renders_with_styles_and_security_headers(page):
    errors = []
    page.on("pageerror", lambda error: errors.append(error))
    response = page.goto("/")
    assert response.status == 200
    page.get_by_role("heading", name="Good things deserve a second life.", exact=True).wait_for(
        state="visible"
    )
    assert page.locator("html").get_attribute("lang") == "en"
    assert page.get_by_text("Manage your personal repairs.", exact=True).is_visible()
    assert page.evaluate(
        "Array.from(document.styleSheets).some(sheet => "
        "sheet.href && new URL(sheet.href).pathname === '/static/app.css' "
        "&& sheet.cssRules.length > 0)"
    )
    assert response.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert not errors


def test_readiness_through_the_complete_runtime(page):
    response = page.goto("/health/ready")
    assert response.status == 200
    assert response.json() == {"status": "ready"}


def test_database_outage_is_reported_without_internal_details(page, live_application):
    # Stoppt ausschliesslich die eigene kurzlebige Testdatenbank.
    docker("stop", live_application.db, capture=True)
    try:
        response = page.goto("/health/ready")
        assert response.status == 503
        assert response.json() == {"status": "unavailable"}
        assert "postgresql" not in response.text()
        assert "Traceback" not in response.text()
    finally:
        docker("start", live_application.db, capture=True)
        ready(live_application.db, ["pg_isready", "-U", "repairhub_test", "-d", "repairhub_test"])
        ready(
            live_application.app,
            [
                "python",
                "-c",
                "import urllib.request; "
                "urllib.request.urlopen('http://127.0.0.1:8000/health/ready',timeout=5)",
            ],
        )
    assert page.goto("/health/ready").status == 200


@pytest.mark.parametrize("page", [True, {"javascript": False, "locale": "de-CH"}], indirect=True)
def test_error_page_shares_navigation_and_returns_home(page):
    response = page.goto("/not-found")
    assert response.status == 404
    german = page.locator("html").get_attribute("lang").startswith("de")
    assert page.get_by_role(
        "heading", name="Seite nicht gefunden" if german else "Page not found"
    ).is_visible()
    page.get_by_role(
        "link", name="Zur Startseite" if german else "Back to home", exact=True
    ).click()
    assert page.url.endswith("/")
    assert page.locator("#home-heading").is_visible()


def test_unknown_api_route_returns_json_through_nginx(page):
    response = page.goto("/api/not-found")
    assert response.status == 404
    assert response.json()["error"]["status"] == 404


def test_bootstrap_and_humble_notification_adapter(page):
    errors = []
    page.on("pageerror", lambda error: errors.append(error))
    page.goto("/")
    assert (
        page.evaluate(
            "getComputedStyle(document.documentElement).getPropertyValue('--bs-primary').trim()"
        )
        == "#b84020"
    )
    # Die Meldungs-Fixture prüft das UI-Verhalten unabhängig von einer Kontoerstellung.
    page.evaluate("""async () => {
        const message = document.createElement('div');
        message.dataset.notification = '';
        message.innerHTML = '<span>Gespeichert</span><button type="button" '
            + 'data-dismiss-notification hidden>Dismiss message</button>';
        document.querySelector('#content').prepend(message);
        const { mountNotifications } = await import('/static/js/notification-view.mjs');
        mountNotifications(document);
    }""")
    page.get_by_role("button", name="Dismiss message").click()
    assert page.locator("[data-notification]").count() == 0
    assert page.locator("#content").evaluate("element => element === document.activeElement")
    assert not errors


def test_home_works_without_javascript_on_small_screen(browser, live_application):
    context = browser.new_context(
        base_url=live_application.public_url,
        ignore_https_errors=True,
        java_script_enabled=False,
        viewport={"width": 360, "height": 740},
    )
    try:
        page = context.new_page()
        page.goto("/")
        assert page.get_by_role(
            "heading", name="Good things deserve a second life.", exact=True
        ).is_visible()
        assert page.get_by_role("link", name="RepairHub – Home").is_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    finally:
        context.close()
