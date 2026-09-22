"""Kosten und Teile über denselben AJAX-/HTML-Ablauf in Englisch und Deutsch."""

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
def test_parts_and_costs(page, device_account, request):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    login(page, device_account)
    page.goto("/devices")
    page.locator('[data-action="view"]').first.click()
    page.locator('a[href$="/repairs/new"]').click()
    page.locator("#new-description").fill("Power supply failed")
    page.locator("[data-repair-form] [type=submit]").click()
    expect(page.locator("[data-total-cost]")).to_have_text("CHF 0.00")
    settings = request.node.callspec.params["page"]
    ajax = settings.get("javascript", True) if isinstance(settings, dict) else settings
    navigations = []
    page.on(
        "request",
        lambda sent: navigations.append(sent.url) if sent.resource_type == "document" else None,
    )
    work = page.locator('form[action*="/work?"]')
    if ajax:
        expect(work.locator("[type=submit]")).to_be_disabled()
    page.locator("#work-hours").fill("2")
    page.locator("#work-rate").fill("80")
    work.locator("[type=submit]").click()
    expect(page.locator("[data-total-cost]")).to_have_text("CHF 160.00")
    new = page.locator('form[action*="/parts?"]')
    if ajax:
        expect(new.locator("[type=submit]")).to_be_disabled()
    page.locator("#new-part-name").fill("Power cable")
    page.locator("#new-part-price").fill("15")
    page.locator("#new-part-quantity").fill("3")
    new.locator("[type=submit]").click()
    expect(page.locator("[data-total-cost]")).to_have_text("CHF 205.00")
    part = page.locator("[data-part-id]").first
    if ajax:
        expect(part.locator("[type=submit]")).to_be_disabled()
        # Ein anderer Speichervorgang darf diesen Entwurf nicht verwerfen.
        page.locator("#new-part-name").fill("Unsaved fuse")
        part.locator("[name=unit_price]").fill("-1")
        part.locator("[type=submit]").click()
        expect(part.locator("[data-error-for=unit_price]")).not_to_be_empty()
        expect(page.locator("[data-total-cost]")).to_have_text("CHF 205.00")
    part.locator("[name=unit_price]").fill("0.10")
    part.locator("[type=submit]").click()
    expect(page.locator("[data-total-cost]")).to_have_text("CHF 160.30")
    if ajax:
        expect(page.locator("#new-part-name")).to_have_value("Unsaved fuse")
        assert not navigations
    page.reload()
    expect(page.locator("[data-total-cost]")).to_have_text("CHF 160.30")
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    target = Path("reports/t08")
    target.mkdir(parents=True, exist_ok=True)
    language = "de" if isinstance(settings, dict) else "en"
    page.screenshot(path=str(target / f"costs-{language}-{ajax}.png"), full_page=True)
    assert not errors
