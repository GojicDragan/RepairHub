"""Fehlerzustände erhalten Entwürfe und bieten einen sichtbaren nächsten Schritt."""

import pytest
from playwright.sync_api import expect

from tests.e2e.test_devices import device_account as device_account
from tests.e2e.test_devices import login


@pytest.mark.parametrize("device_account", [1], indirect=True)
@pytest.mark.parametrize("page", [True, {"javascript": True, "locale": "de-CH"}], indirect=True)
def test_repair_network_failure_and_expired_session(page, device_account):
    login(page, device_account)
    page.goto("/devices")
    page.locator('[data-action="view"]').first.click()
    page.locator('a[href$="/repairs/new"]').click()
    page.locator("#new-description").fill("Keep this description")
    endpoint = page.locator("[data-repair-form]").get_attribute("action")
    page.route("**" + endpoint, lambda route: route.abort(), times=1)
    page.locator('[data-repair-form] [type="submit"]').click()
    expect(page.locator("[data-repair-form-status]")).not_to_be_empty()
    expect(page.locator("#new-description")).to_have_value("Keep this description")
    expect(page.locator('[data-repair-form] [type="submit"]')).to_be_enabled()
    page.locator('[data-repair-form] [type="submit"]').click()
    expect(page.locator("[data-total-cost]")).to_have_text("CHF 0.00")
    form = page.locator('form[action*="/description?"]')
    page.locator("#fault-description").fill("Unsaved correction")
    # Die Sitzung tatsächlich entfernen: Der alte CSRF-Wert darf keine Änderung erlauben.
    page.context.clear_cookies()
    form.locator('[type="submit"]').click()
    expect(form.locator("[data-repair-login]")).to_be_visible()
    expect(page.locator("#fault-description")).to_have_value("Unsaved correction")
    expect(form.locator("[data-repair-form-status]")).not_to_be_empty()
