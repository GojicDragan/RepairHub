"""Reparaturabläufe über Nginx in beiden Sprachen, mit AJAX und ohne JavaScript."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_devices import device_account as device_account
from tests.e2e.test_devices import login


@pytest.mark.parametrize("device_account", [1], indirect=True)
@pytest.mark.parametrize(
    "page",
    [
        True,
        {"javascript": True, "locale": "de-CH"},
        False,
        {"javascript": False, "locale": "de-CH"},
    ],
    indirect=True,
)
def test_repair_lifecycle(page, device_account, request):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    login(page, device_account)
    page.goto("/devices")
    page.locator('[data-action="view"]').first.click()
    page.locator('a[href$="/repairs/new"]').click()
    options = request.node.callspec.params["page"]
    ajax = options.get("javascript", True) if isinstance(options, dict) else options
    if ajax:
        # Die Erwartung stammt aus der Testkonfiguration, nicht aus einem möglichen Ladefehler.
        expect(page.locator("[data-repair-form]")).to_have_js_property("noValidate", True)
    description = page.locator("#new-description")
    submit = page.locator("[data-repair-form] [type=submit]")
    if ajax:
        expect(submit).to_be_disabled()
    description.fill("Radio stops when warm")
    navigations = []
    # replaceState ändert die URL im selben Dokument und löst bei Playwright ebenfalls
    # framenavigated aus. Nur echte Dokumentanfragen würden den AJAX-Vertrag verletzen.
    page.on(
        "request",
        lambda sent: navigations.append(sent.url) if sent.resource_type == "document" else None,
    )
    submit.click()
    expect(page.locator(".repair-workspace")).to_be_visible()
    assert "/repairs/" in page.url
    if ajax:
        assert not navigations
    expect(page.locator(".repair-status-open")).to_be_visible()
    repair_url = page.url
    for status in ("in_progress", "completed", "in_progress"):
        page.locator("#repair-status").select_option(status)
        page.locator('form[action*="/status"] [type=submit]').click()
        expect(page.locator(".repair-status-" + status)).to_be_visible()
    page.locator("#new-step-description").fill("Inspect power cable")
    page.locator('form[action$="/steps?offset=0"] [type=submit]').click()
    expect(page.locator("[data-step-id]")).to_have_count(1)
    step = page.locator("[data-step-id]")
    step.locator("textarea").fill("Replace power cable")
    step.locator("[type=checkbox]").check()
    step.locator("[type=submit]").click()
    expect(page.locator(".repair-step.is-completed")).to_have_count(1)
    page.locator("#fault-description").fill("Intermittent power failure")
    if ajax:
        page.locator("#fault-description").fill("")
        page.locator("#repair-status").select_option("completed")
        page.locator('form[action*="/status"] [type=submit]').click()
        expect(page.locator(".repair-status-completed")).to_be_visible()
        expect(page.locator("#fault-description")).to_have_value("")
        expect(page.locator('form[action*="/description"] [type=submit]')).to_be_disabled()
        page.locator("#fault-description").fill("Intermittent power failure")
        # Eine separate Statusänderung darf den ungespeicherten Beschreibungstext nicht verlieren.
        page.locator("#repair-status").select_option("open")
        page.locator('form[action*="/status"] [type=submit]').click()
        expect(page.locator(".repair-status-open")).to_be_visible()
        expect(page.locator("#fault-description")).to_have_value("Intermittent power failure")
    page.locator('form[action*="/description"] [type=submit]').click()
    # Erst nach der AJAX-Antwort neu laden, sonst bricht der Browser den Schreibzugriff ab.
    expect(page.locator("#fault-description")).to_have_attribute(
        "data-original", "Intermittent power failure"
    )
    page.reload()
    expect(page.locator("#fault-description")).to_have_value("Intermittent power failure")
    expect(page.locator("[data-step-id] textarea")).to_have_value("Replace power cable")
    expect(page.locator("[data-step-id] [type=checkbox]")).to_be_checked()
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    Path("reports/t07").mkdir(parents=True, exist_ok=True)
    page.screenshot(
        path=f"reports/t07/repair-{page.locator('html').get_attribute('lang')}-{ajax}.png",
        full_page=True,
    )
    if ajax:
        page.route("**/repairs/*/description*", lambda route: route.abort())
        page.locator("#fault-description").fill("Draft while offline")
        page.locator('form[action*="/description"] [type=submit]').click()
        expect(
            page.locator('form[action*="/description"] [data-repair-form-status]')
        ).not_to_be_empty()
        expect(page.locator("#fault-description")).to_have_value("Draft while offline")
        page.unroute("**/repairs/*/description*")
    page.goto("/repairs")
    expect(page.locator(".repair-card")).to_have_count(1)
    expect(page.locator(".repair-card")).to_contain_text("Intermittent power failure")
    page.locator(".repair-card").click()
    assert page.url == repair_url
    assert not errors


@pytest.mark.parametrize("device_account", [2], indirect=True)
@pytest.mark.parametrize(
    "page", [True, {"javascript": True, "locale": "de-CH"}, False], indirect=True
)
def test_repair_virtual_list_and_restoration(page, device_account, live_application, request):
    from scripts.ci.images import docker

    docker(
        "exec",
        live_application.app,
        "python",
        "-c",
        """
import sys
from sqlalchemy import select
from app import create_app
from app.extensions import db
from app.data.users.model import User
from app.data.devices.model import Device
from app.data.repairs.model import Repair
with create_app().app_context():
    uid=db.session.scalar(select(User.id).where(User.username==sys.argv[1]))
    devices=db.session.scalars(select(Device.id).where(Device.owner_id==uid).order_by(Device.id)).all()
    db.session.add_all(Repair(device_id=devices[0],description=f'Scroll fault {i:04}')
                      for i in range(240))
    db.session.add(Repair(device_id=devices[1],description='Other device fault'))
    db.session.commit()
""",
        device_account,
        capture=True,
    )
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    login(page, device_account)
    page.goto("/repairs")
    response = page.request.get("/repairs")
    assert response.text().count("data-repair-id=") == 20
    ajax = request.node.callspec.params["page"] is not False
    if not ajax:
        expect(page.locator("[data-repair-rows] > li")).to_have_count(20)
        page.locator("[data-list-pagination] a").last.click()
        assert "offset=20" in page.url and "snapshot=" in page.url
        expect(page.locator("[data-repair-rows] > li")).to_have_count(20)
        return
    rows = page.locator("[data-repair-rows] > li")
    expect(rows).to_have_count(60)
    expect(page.locator("[data-list-pagination]")).to_be_hidden()
    viewport = page.locator("[data-list-viewport]")
    for backwards in (True, False):
        viewport.evaluate("(element) => {element.scrollTop = 112 * 100 + 23;}")
        target = page.get_by_role("heading", name="Scroll fault 0139", exact=True)
        expect(target).to_be_visible()
        top = viewport.evaluate("element => element.scrollTop")
        target.click()
        expect(page.locator(".repair-workspace")).to_be_visible()
        if backwards:
            page.go_back()
        else:
            page.locator(".repair-breadcrumb a").first.click()
        expect(rows).to_have_count(60)
        expect(page.get_by_role("heading", name="Scroll fault 0139", exact=True)).to_be_visible()
        assert abs(viewport.evaluate("element => element.scrollTop") - top) <= 1
    viewport.evaluate("(element) => {element.scrollTop = 112 * 220;}")
    expect(page.get_by_role("heading", name="Scroll fault 0000", exact=True)).to_be_attached()
    assert rows.count() <= 60
    page.route("**/repairs?*", lambda route: route.abort())
    viewport.evaluate("element => {element.scrollTop = 0;}")
    expect(page.locator("[data-list-retry]")).to_be_visible()
    page.unroute("**/repairs?*")
    page.locator("[data-list-retry]").click()
    expect(page.get_by_role("heading", name="Other device fault", exact=True)).to_be_visible()
    expect(page.locator("[data-list-retry]")).to_be_hidden()
    page.goto("/devices")
    page.locator("[data-action=view]").first.click()
    page.locator('a[href*="/repairs?device_id="]').click()
    filtered_url = page.url
    expect(rows).to_have_count(60)
    expect(page.get_by_role("heading", name="Other device fault", exact=True)).to_have_count(0)
    viewport.evaluate("(element) => {element.scrollTop = 112 * 100;}")
    target = page.get_by_role("heading", name="Scroll fault 0139", exact=True)
    expect(target).to_be_visible()
    target.click()
    page.locator(".repair-breadcrumb a").first.click()
    assert page.url == filtered_url
    expect(target).to_be_visible()
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    Path("reports/repair-scroll").mkdir(parents=True, exist_ok=True)
    page.screenshot(
        path=f"reports/repair-scroll/list-{page.locator('html').get_attribute('lang')}.png",
        full_page=True,
    )
    assert not errors
