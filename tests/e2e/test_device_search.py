"""Gerätesuche mit Debounce, begrenzten Fenstern und GET-Fallback."""

from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from playwright.sync_api import expect

from tests.e2e.test_devices import device_account as device_account
from tests.e2e.test_devices import login


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
def test_device_search_windows_navigation_and_reset(page, device_account, request):
    ajax = request.node.callspec.params["page"]["javascript"]
    login(page, device_account)
    page.goto("/devices")
    rows = page.locator("[data-device-rows] > li")
    expect(rows).to_have_count(60 if ajax else 20)
    search = page.locator("#device-search")
    term = "DEVICE maker model"
    if ajax:
        requests = []
        page.on(
            "request",
            lambda req: requests.append(req.url) if req.resource_type == "fetch" else None,
        )
        page.evaluate("window.sameDeviceDocument = true")
        with page.expect_response(
            lambda response: parse_qs(urlparse(response.url).query).get("q") == [term]
        ):
            for value in ("D", "DEVICE maker", term):
                search.fill(value)
        expect(search).to_be_focused()
        assert page.evaluate("window.sameDeviceDocument")
        assert len([url for url in requests if parse_qs(urlparse(url).query).get("q")]) == 1
    else:
        search.fill(term)
        page.locator("form[role=search] button").click()
    expect(page.locator("[data-device-list]")).to_have_attribute("data-total", "240")
    expect(rows).to_have_count(60 if ajax else 20)
    if ajax:
        viewport = page.locator("[data-list-viewport]")
        viewport.evaluate("(e) => e.scrollTop = 112 * 100 + 23")
        page.get_by_role("link", name="Device 0101", exact=True).click()
    else:
        page.locator("[data-list-pagination] a").last.click()
        assert "offset=20" in page.url and parse_qs(urlparse(page.url).query)["q"] == [term]
        rows.locator("[data-action=view]").first.click()
    assert parse_qs(urlparse(page.url).query)["q"] == [term]
    page.locator("article.device-editor > a.btn").click()
    assert "/edit?" in page.url and parse_qs(urlparse(page.url).query)["q"] == [term]
    page.locator(".device-editor > a").first.click()
    expect(search).to_have_value(term)
    expect(rows).to_have_count(60 if ajax else 20)
    if ajax:
        assert page.locator("[data-list-viewport]").evaluate("e => e.scrollTop") > 10000
    search.fill("no matching device")
    if not ajax:
        page.locator("form[role=search] button").click()
    expect(page.locator("[data-device-list]")).to_have_attribute("data-total", "0")
    expect(page.locator("[data-list-empty]")).to_be_visible()
    page.locator("[data-filter-clear]").click()
    expect(search).to_have_value("")
    expect(page.locator("[data-device-list]")).to_have_attribute("data-total", "240")
    expect(rows).to_have_count(60 if ajax else 20)
    if ajax:
        assert page.locator("[data-list-viewport]").evaluate("e => e.scrollTop") == 0
        page.route("**/devices?q=offline*", lambda route: route.abort())
        search.fill("offline")
        expect(page.locator("[data-list-retry]")).to_be_visible()
        page.unroute("**/devices?q=offline*")
        page.locator("[data-list-retry]").click()
        expect(page.locator("[data-device-list]")).to_have_attribute("data-total", "0")
        expect(page.locator("[data-list-retry]")).to_be_hidden()
        search.fill("Model 239")
        expect(rows).to_have_count(1)
        expect(rows).to_contain_text("Device 0239")
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    Path("reports/kt02").mkdir(parents=True, exist_ok=True)
    page.screenshot(
        path=f"reports/kt02/devices-{page.locator('html').get_attribute('lang')}-{ajax}.png",
        full_page=True,
    )
