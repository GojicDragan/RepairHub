"""Filterformular, Rücknavigation und virtuelle Trefferfenster im echten Browser."""

from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from playwright.sync_api import expect

from scripts.ci.images import docker
from tests.e2e.test_devices import device_account as device_account
from tests.e2e.test_devices import login


@pytest.mark.parametrize("device_account", [1], indirect=True)
@pytest.mark.parametrize(
    "page",
    [
        {"javascript": True, "locale": "en"},
        {"javascript": True, "locale": "de-CH"},
        {"javascript": False, "locale": "en"},
        {"javascript": False, "locale": "de-CH"},
    ],
    indirect=True,
)
def test_search_status_windows_and_return(page, device_account, live_application, request):
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
    device = db.session.scalar(select(Device).join(User).where(User.username == sys.argv[1]))
    db.session.add_all(Repair(device_id=device.id, description=f'Warm signal {i:04}', status='open')
                      for i in range(100))
    db.session.add(Repair(device_id=device.id, description='Warm finished', status='completed'))
    db.session.add(Repair(device_id=device.id, description='Cold fault', status='open'))
    db.session.commit()
""",
        device_account,
        capture=True,
    )
    login(page, device_account)
    page.goto("/repairs")
    ajax = request.node.callspec.params["page"]["javascript"]
    if ajax:
        requests = []
        page.on(
            "request",
            lambda req: requests.append(req.url) if req.resource_type == "fetch" else None,
        )
        page.evaluate("window.repairFilterDocument = true")
        with page.expect_response(
            lambda response: parse_qs(urlparse(response.url).query).get("q") == ["WARM signal"]
        ):
            for value in ("W", "WARM", "WARM signal"):
                page.locator("#repair-search").fill(value)
        expect(page.locator("[data-repair-list]")).to_have_attribute("data-total", "100")
        expect(page.locator("#repair-search")).to_be_focused()
        assert page.evaluate("window.repairFilterDocument") is True
        assert len([url for url in requests if parse_qs(urlparse(url).query).get("q")]) == 1
    else:
        page.locator("#repair-search").fill("WARM signal")
    page.locator("#repair-filter-status").select_option("open")
    if not ajax:
        page.locator("form[role=search] button").click()
    else:
        expect(page.locator("form[role=search] button")).to_have_count(0)
    expect(page.locator("#repair-search")).to_have_value("WARM signal")
    expect(page.locator("[data-repair-list]")).to_have_attribute("data-total", "100")
    ajax = request.node.callspec.params["page"]["javascript"]
    rows = page.locator("[data-repair-rows] > li")
    expect(rows).to_have_count(60 if ajax else 20)
    if ajax:
        page.locator("[data-list-viewport]").evaluate("(e) => e.scrollTop = 112 * 65")
        expect(page.locator("[data-spacer-before]")).not_to_have_attribute("style", "height: 0px;")
        assert rows.count() <= 60
    else:
        page.locator("[data-list-pagination] a").last.click()
        assert "offset=20" in page.url and "status=open" in page.url
    # Der sichtbare Rückweg erhält Filter; normales Browser-Zurück bleibt ebenso nutzbar.
    if ajax:
        page.get_by_role("heading", name="Warm signal 0034", exact=True).click()
    else:
        rows.locator("a").first.click()
    page.locator(".repair-breadcrumb a").first.click()
    expect(page.locator("#repair-search")).to_have_value("WARM signal")
    expect(page.locator("#repair-filter-status")).to_have_value("open")
    expect(page.locator("[data-repair-list]")).to_have_attribute("data-total", "100")
    if ajax:
        # Nach der Detailnavigation zuerst die erneute JS-Anbindung abwarten.
        expect(page.locator("[data-repair-rows] > li")).to_have_count(60)
    page.locator("#repair-filter-status").select_option("completed")
    if not ajax:
        page.locator("form[role=search] button").click()
    else:
        expect(page.locator("form[role=search] button")).to_have_count(0)
    expect(page.locator("[data-repair-list]")).to_have_attribute("data-total", "0")
    expect(page.locator(".device-empty")).to_be_visible()
    page.locator("form[role=search] a").click()
    expect(page.locator("#repair-search")).to_have_value("")
    expect(page.locator("[data-repair-list]")).to_have_attribute("data-total", "102")
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    Path("reports/kt01").mkdir(parents=True, exist_ok=True)
    locale = page.locator("html").get_attribute("lang")
    page.screenshot(path=f"reports/kt01/filters-{locale}-{ajax}.png", full_page=True)
