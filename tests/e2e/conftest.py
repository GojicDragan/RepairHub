"""Echte Browserabläufe gegen eine eigene kurzlebige Produktionsimage-Kombination."""

import json
import os
import ssl
import subprocess
import urllib.request
from pathlib import Path

import pytest

from scripts.ci.images import SHA, verify
from scripts.ci.isolated_runtime import isolated_runtime


def pytest_addoption(parser):
    parser.addoption("--image-artifacts", default="artifacts/images")
    parser.addoption("--image-commit", default=os.environ.get("GITHUB_SHA"))


@pytest.fixture(scope="session")
def live_application(pytestconfig):
    commit = pytestconfig.getoption("--image-commit")
    if not commit:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if not SHA.fullmatch(commit):
        pytest.fail("E2E benötigt den vollständigen Commit-SHA der gebauten Images.")
    directory = Path(pytestconfig.getoption("--image-artifacts"))
    if not (directory / "manifest.json").is_file():
        pytest.fail("E2E benötigt gebaute Image-Archive: scripts/ci/images.py build ausführen.")
    manifest = verify(directory, commit)
    with isolated_runtime(manifest, publish_https=True, receive_mail=True) as runtime:
        # Der Browser vertraut der kurzlebigen CA nicht systemweit. Vor seiner
        # Nutzung prüfen wir Zertifikatskette und Hostname ausdrücklich über TLS.
        tls_context = ssl.create_default_context(cafile=runtime.ca_path)
        with urllib.request.urlopen(
            runtime.public_url + "/health/ready", context=tls_context, timeout=10
        ) as response:
            assert response.status == 200
            assert json.load(response) == {"status": "ready"}
        yield runtime


@pytest.fixture(scope="session")
def browser(live_application):
    # Lazy import: Unit-/Integration-Auswahl benötigt keine Browser-Abhängigkeiten.
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.fail("E2E benötigt die Abhängigkeitsgruppe e2e und den Chromium-Browser.")
    with sync_playwright() as playwright:
        instance = playwright.chromium.launch(headless=True)
        try:
            yield instance
        finally:
            instance.close()


@pytest.fixture
def page(browser, live_application, request):
    # Ausnahme ausschliesslich für die zuvor streng geprüfte lokale Test-CA.
    settings = getattr(request, "param", True)
    options = settings if isinstance(settings, dict) else {"javascript": settings}
    context = browser.new_context(
        base_url=live_application.public_url,
        ignore_https_errors=True,
        locale=options.get("locale", "en"),
        java_script_enabled=options.get("javascript", True),
    )
    # HTTP(S)-Anfragen der Testseiten auf die lokale Test-Origin begrenzen.
    context.route(
        "**/*",
        lambda route: (
            route.continue_()
            if route.request.url.startswith(live_application.public_url + "/")
            else route.abort()
        ),
    )
    browser_page = context.new_page()
    browser_page.set_default_timeout(10_000)
    try:
        yield browser_page
    finally:
        context.close()
