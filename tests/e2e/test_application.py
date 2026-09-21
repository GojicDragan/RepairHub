"""Browser → HTTPS/Nginx → Gunicorn/Flask → PostgreSQL, ohne Anwendungs-Mocks."""

from scripts.ci.images import docker
from scripts.ci.isolated_runtime import ready


def test_home_renders_with_styles_and_security_headers(page):
    errors = []
    page.on("pageerror", lambda error: errors.append(error))
    response = page.goto("/")
    assert response.status == 200
    page.get_by_role("heading", name="RepairHub", exact=True).wait_for(state="visible")
    assert page.locator("html").get_attribute("lang") == "de-CH"
    assert page.get_by_text("Die Anwendung wird vorbereitet.", exact=True).is_visible()
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
