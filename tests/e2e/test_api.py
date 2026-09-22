"""Browserdaten mit einem unabhängigen HTTPS-Client über die Lese-API abrufen."""

import json
import ssl
import urllib.error
import urllib.request

import pytest
from playwright.sync_api import expect

from tests.e2e.test_devices import device_account as device_account
from tests.e2e.test_devices import login


@pytest.mark.parametrize("device_account", [1], indirect=True)
@pytest.mark.parametrize("page", [True, {"javascript": False, "locale": "de-CH"}], indirect=True)
def test_browser_and_browserless_api_share_data(page, live_application, device_account):
    login(page, device_account)
    page.goto("/devices")
    page.locator('[data-action="view"]').first.click()
    page.locator('a[href$="/repairs/new"]').click()
    page.locator("#new-description").fill("API read example")
    page.locator("[data-repair-form] [type=submit]").click()
    expect(page.locator("[data-total-cost]")).to_have_text("CHF 0.00")
    repair_id = page.url.split("/repairs/")[1].split("?")[0]
    page.locator("#work-hours").fill("2")
    page.locator("#work-rate").fill("80")
    page.locator('form[action*="/work?"] [type=submit]').click()
    expect(page.locator("[data-total-cost]")).to_have_text("CHF 160.00")
    # urllib besitzt keine Browsercookies; die Fixture-CA wird ausdrücklich geprüft.
    context = ssl.create_default_context(cafile=live_application.ca_path)
    page.goto("/account/api-key")
    page.locator('form[action="/account/api-key"] button').click()
    key = page.locator("#api-key-value").input_value()
    assert len(key) == 46
    page.goto("/account/api-key")
    expect(page.locator("#api-key-value")).to_have_count(0)
    token = key
    url = live_application.public_url + "/api/repairs/" + repair_id
    with urllib.request.urlopen(
        urllib.request.Request(url, headers={"Authorization": "Bearer " + token}),
        context=context,
        timeout=10,
    ) as response:
        document = json.load(response)
    assert document["description"] == "API read example"
    assert document["costs"]["total"] == "160.00"
    assert document["work"] == {"hours": "2.00", "hourly_rate": "80.00"}
    # Die vorhandene Browseranmeldung allein berechtigt trotzdem keinen API-Zugriff.
    denied = page.request.get("/api/repairs/" + repair_id)
    assert denied.status == 401

    with urllib.request.urlopen(
        urllib.request.Request(
            live_application.public_url + "/api/repairs?limit=1",
            headers={"Authorization": "Bearer " + key},
        ),
        context=context,
        timeout=10,
    ) as response:
        assert json.load(response)["items"][0]["id"] == int(repair_id)
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.locator('form[action$="/revoke"] button').click()
    with pytest.raises(urllib.error.HTTPError) as denied:
        urllib.request.urlopen(
            urllib.request.Request(url, headers={"Authorization": "Bearer " + key}),
            context=context,
            timeout=10,
        )
    assert denied.value.code == 401
