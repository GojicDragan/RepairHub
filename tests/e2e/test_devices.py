"""SSR, AJAX und begrenzte virtuelle Liste unter echter Nginx-CSP im Browser."""

import uuid
from pathlib import Path

import pytest
from playwright.sync_api import expect

from scripts.ci.images import docker


@pytest.fixture
def device_account(live_application, request):
    username = "devices" + uuid.uuid4().hex[:10]
    # Ausschliesslich die isolierte E2E-Datenbank befüllen; keine Produktionszugänge.
    docker(
        "exec",
        live_application.app,
        "python",
        "-c",
        """
import sys
from datetime import UTC, datetime
from app import create_app
from app.extensions import db
from app.data.devices.model import Device
from flask_security import hash_password
app = create_app()
with app.app_context():
    store = app.extensions['security'].datastore
    user = store.create_user(username=sys.argv[1], email=sys.argv[1]+'@example.org',
        password=hash_password('device-test-password'), confirmed_at=datetime.now(UTC))
    db.session.flush()
    db.session.add_all(Device(owner_id=user.id, name=f'Device {i:04}',
        manufacturer='Repair maker', model=f'Model {i}') for i in range(int(sys.argv[2])))
    store.commit()
""",
        username,
        str(getattr(request, "param", 240)),
        capture=True,
    )
    return username


def login(page, username):
    page.goto("/login")
    page.locator('[name="identity"]').fill(username)
    page.locator('[name="password"]').fill("device-test-password")
    page.locator('main [type="submit"]').click()
    page.wait_for_url("**/")


@pytest.mark.parametrize("page", [True, {"javascript": True, "locale": "de-CH"}], indirect=True)
def test_ajax_save_and_virtual_scroll_remain_bounded(page, device_account):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    login(page, device_account)
    response = page.request.get("/devices")
    assert response.text().count("data-device-id=") == 20
    page.goto("/devices")
    rows = page.locator("[data-device-rows] > li")
    expect(rows).to_have_count(60)
    viewport = page.locator("[data-list-viewport]")
    expect(page.locator("[data-list-pagination]")).to_be_hidden()
    viewport.focus()
    viewport.press("PageDown")
    page.wait_for_function("() => document.querySelector('[data-list-viewport]').scrollTop > 0")
    viewport.press("Home")
    page.wait_for_function("() => document.querySelector('[data-list-viewport]').scrollTop === 0")
    assert page.url.endswith("/devices")
    for position, name in [
        (112 * 100, "Device 0100"),
        (112 * 220, "Device 0239"),
        (0, "Device 0000"),
    ]:
        viewport.evaluate("(element, top) => {element.scrollTop = top;}", position)
        expect(page.get_by_role("link", name=name, exact=True)).to_be_attached()
        assert rows.count() <= 60
    # Sowohl Browser-Zurück als auch der Listenlink erhalten die Position.
    for browser_back in (True, False):
        viewport.evaluate("element => { element.scrollTop = 112 * 100 + 23; }")
        target = page.get_by_role("link", name="Device 0101", exact=True)
        expect(target).to_be_visible()
        top = viewport.evaluate("element => element.scrollTop")
        target.click()
        expect(page.get_by_role("heading", name="Device 0101")).to_be_visible()
        if browser_back:
            page.go_back()
        else:
            page.locator("article.device-editor > a").first.click()
        expect(page.locator("[data-device-rows] > li")).to_have_count(60)
        expect(page.get_by_role("link", name="Device 0101", exact=True)).to_be_visible()
        assert abs(viewport.evaluate("element => element.scrollTop") - top) <= 1
    viewport.evaluate("element => { element.scrollTop = 0; }")
    expect(page.get_by_role("link", name="Device 0000", exact=True)).to_be_attached()
    # Ein Netzfehler muss wiederholbar bleiben, statt die Liste dauerhaft zu sperren.
    page.route("**/devices?*", lambda route: route.abort())
    viewport.evaluate("(element) => {element.scrollTop = 112*100;}")
    expect(page.locator("[data-list-retry]")).to_be_visible()
    page.unroute("**/devices?*")
    page.locator("[data-list-retry]").click()
    expect(page.get_by_role("link", name="Device 0100", exact=True)).to_be_attached()
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    Path("reports/t06").mkdir(parents=True, exist_ok=True)
    language = page.locator("html").get_attribute("lang")
    page.screenshot(path=f"reports/t06/devices-{language}.png", full_page=True)
    page.goto("/devices/new")
    page.locator('[name="name"]').fill("New radio")
    page.locator('[name="manufacturer"]').fill("Maker")
    page.locator('[name="model"]').fill("R1")
    navigations = []
    page.on("framenavigated", lambda frame: navigations.append(frame.url))
    page.locator('main [type="submit"]').click()
    expect(page.locator("[data-saved-link]")).to_be_visible()
    assert not navigations
    expect(page.locator('main [type="submit"]')).to_be_disabled()
    detail_url = page.locator("[data-saved-link]").get_attribute("href")
    page.locator('[name="name"]').fill("Changed radio")
    page.locator('main [type="submit"]').click()
    expect(page.locator("[data-device-form]")).to_have_attribute("aria-busy", "false")
    expect(page.locator('main [type="submit"]')).to_be_disabled()
    assert page.locator("[data-saved-link]").get_attribute("href") == detail_url
    page.goto(detail_url)
    expect(page.get_by_role("heading", name="Changed radio")).to_be_visible()
    page.goto(detail_url + "/edit")
    save_button = page.locator('main [type="submit"]')
    expect(save_button).to_be_disabled()
    page.locator('[name="name"]').fill("Changed again")
    expect(save_button).to_be_enabled()
    page.locator('[name="name"]').fill("Changed radio")
    expect(save_button).to_be_disabled()
    page.locator('[name="name"]').fill(" Changed radio ")
    expect(save_button).to_be_disabled()
    page.locator('[name="name"]').fill("Changed radio")
    page.locator('[name="manufacturer"]').fill("   ")
    expect(page.locator('main [type="submit"]')).to_be_disabled()
    expect(page.locator('[name="name"]')).to_have_value("Changed radio")
    page.locator('[name="manufacturer"]').fill("New maker")
    page.route(
        "**/devices/*/edit",
        lambda route: route.abort() if route.request.method == "POST" else route.continue_(),
    )
    page.locator('main [type="submit"]').click()
    expect(page.locator("[data-save-status]")).not_to_be_empty()
    expect(page.locator('[name="manufacturer"]')).to_have_value("New maker")
    expect(page.locator('main [type="submit"]')).to_be_enabled()
    assert not errors


@pytest.mark.parametrize("page", [False, {"javascript": False, "locale": "de-CH"}], indirect=True)
def test_device_forms_and_pagination_work_without_javascript(page, device_account):
    login(page, device_account)
    page.goto("/devices")
    expect(page.locator("[data-device-rows] > li")).to_have_count(20)
    page.locator("[data-list-pagination] a").last.click()
    expect(page.get_by_role("link", name="Device 0020", exact=True)).to_be_visible()
    page.goto("/devices/new")
    for name, value in [("name", "No JS radio"), ("manufacturer", "Maker"), ("model", "R1")]:
        page.locator(f'[name="{name}"]').fill(value)
    page.locator('main [type="submit"]').click()
    expect(page.get_by_role("heading", name="No JS radio")).to_be_visible()
    page.goto(page.url + "/edit")
    page.locator('[name="model"]').fill("R2")
    page.locator('main [type="submit"]').click()
    expect(page.locator("dd").last).to_have_text("R2")


@pytest.mark.parametrize("device_account", [0], indirect=True)
def test_empty_list_invites_creation_without_an_empty_scroll_area(page, device_account):
    login(page, device_account)
    page.goto("/devices")
    expect(page.get_by_role("heading", name="Start with your first device.")).to_be_visible()
    expect(page.locator("[data-list-viewport]")).to_be_hidden()
    expect(page.locator("[data-list-controls]")).to_have_count(0)


@pytest.mark.parametrize("page", [True, {"javascript": True, "locale": "de-CH"}], indirect=True)
def test_own_device_autocomplete_and_free_entry(page, device_account):
    login(page, device_account)
    page.goto("/devices/new")
    expect(page.locator('main [type="submit"]')).to_be_disabled()
    manufacturer = page.locator('[name="manufacturer"]')
    manufacturer.fill("Repair")
    option = page.locator("#manufacturer-suggestions [role=option]")
    expect(option).to_have_text(["Repair maker"])
    Path("reports/device-suggestions").mkdir(parents=True, exist_ok=True)
    page.screenshot(
        path=f"reports/device-suggestions/{page.locator('html').get_attribute('lang')}.png",
        full_page=True,
    )
    manufacturer.press("ArrowDown")
    manufacturer.press("Enter")
    expect(manufacturer).to_have_value("Repair maker")
    model = page.locator('[name="model"]')
    model.fill("Model 1")
    expect(page.locator("#model-suggestions [role=option]")).to_have_count(10)
    page.locator("#model-suggestions [role=option]").first.click()
    expect(model).to_have_value("Model 1")
    name = page.locator('[name="name"]')
    name.fill("Device 00")
    expect(page.locator("#name-suggestions [role=option]")).to_have_count(10)
    name.press("Escape")
    expect(page.locator("#name-suggestions")).to_be_hidden()
    name.fill("New personal radio")
    expect(page.locator('main [type="submit"]')).to_be_enabled()
    name.fill("   ")
    expect(page.locator('main [type="submit"]')).to_be_disabled()
    name.fill("New personal radio")
    manufacturer.fill("New maker")
    model.fill("Unique model")
    expect(page.locator("#model-suggestions")).to_be_hidden()
    page.locator('main [type="submit"]').click()
    expect(page.locator("[data-saved-link]")).to_be_visible()
    page.goto("/devices/new")
    manufacturer.fill("New ma")
    expect(option).to_have_text(["New maker"])
    # Fehler des optionalen Vorschlagsabrufs dürfen Freitext/Speichern nicht blockieren.
    page.route("**/devices/suggestions?*", lambda route: route.abort())
    manufacturer.fill("Offline maker")
    expect(manufacturer.locator("..").locator("[data-suggestion-status]")).not_to_be_empty()
    name.fill("Offline radio")
    model.fill("Offline model")
    page.locator('main [type="submit"]').click()
    expect(page.locator("[data-saved-link]")).to_be_visible()
