"""Mosaik, AJAX, normaler Upload und private Abrufe gegen das Produktionsimage."""

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image, ImageDraw
from playwright.sync_api import expect

from scripts.ci.images import docker
from tests.e2e.test_devices import device_account as device_account
from tests.e2e.test_devices import login


def photo(size, color):
    stream = BytesIO()
    picture = Image.new("RGB", size, color)
    draw = ImageDraw.Draw(picture)
    draw.rectangle(
        (size[0] // 5, size[1] // 5, size[0] * 4 // 5, size[1] * 4 // 5), outline="white", width=6
    )
    picture.save(stream, format="PNG")
    return stream.getvalue()


@pytest.mark.parametrize("device_account", [1], indirect=True)
@pytest.mark.parametrize(
    "page",
    [
        {"javascript": True, "locale": "de-CH"},
        {"javascript": False, "locale": "en"},
    ],
    indirect=True,
)
def test_images_for_devices_and_repairs(page, device_account, live_application, request):
    ids = (
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
    device = db.session.scalar(select(Device).join(User).where(User.username==sys.argv[1]))
    repair = Repair(device_id=device.id, description='Visible fault', status='open')
    db.session.add(repair)
    db.session.commit()
    print(f'{device.id},{repair.id}')
""",
            device_account,
            capture=True,
        )
        .strip()
        .split(",")
    )
    login(page, device_account)
    js = request.node.callspec.params["page"]["javascript"]
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    for domain, id in zip(("devices", "repairs"), ids, strict=True):
        page.goto(f"/{domain}/{id}")
        button = page.locator("[data-image-form] button")
        if js:
            expect(button).to_be_disabled()
        samples = [((420, 240), "#243b35"), ((220, 420), "#b84020"), ((320, 320), "#596660")]
        for index, (size, color) in enumerate(samples):
            page.locator("#image-file").set_input_files(
                {
                    "name": f"Repair photo {index}.png",
                    "mimeType": "image/png",
                    "buffer": photo(size, color),
                }
            )
            expect(button).to_be_enabled()
            button.click()
            expect(page.locator(".image-tile")).to_have_count(index + 1)
        for image in page.locator(".image-tile img").all():
            image.scroll_into_view_if_needed()
            expect(image).to_be_visible()
            page.wait_for_function(
                "(img) => img.complete && img.naturalWidth > 0", arg=image.element_handle()
            )
        original = page.locator(".image-tile a").first.get_attribute("href")
        response = page.request.get(original)
        assert response.status == 200 and response.headers["content-type"] == "image/webp"
        assert "no-store" in response.headers["cache-control"]
        # Ungültiger Inhalt trotz gefälschtem MIME-Typ; Galerie bleibt unverändert.
        page.locator("#image-file").set_input_files(
            {
                "name": "fake.png",
                "mimeType": "image/png",
                "buffer": b"<svg onload='alert(1)'/>",
            }
        )
        page.locator("[data-image-form] button").click()
        expect(page.locator("[data-image-message]")).not_to_be_empty()
        expect(page.locator(".image-tile")).to_have_count(3)
        for width in (1280, 390):
            page.set_viewport_size({"width": width, "height": 900})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            gallery = page.locator("[data-image-gallery]")
            gallery.scroll_into_view_if_needed()
            path = Path(f"reports/kt04/{domain}-{width}-{'js' if js else 'nojs'}.png")
            path.parent.mkdir(parents=True, exist_ok=True)
            gallery.screenshot(path=str(path))
        anonymous = page.context.browser.new_context(ignore_https_errors=True)
        try:
            assert anonymous.request.get(live_application.public_url + original).status == 401
        finally:
            anonymous.close()
        # Bestätigung und Löschung funktionieren mit AJAX und ohne JavaScript.
        page.locator(".image-delete summary").first.click()
        page.locator("[data-image-delete] button").first.click()
        expect(page.locator(".image-tile")).to_have_count(2)
        assert page.request.get(original).status == 404
        assert page.request.get(original + "?thumbnail=1").status == 404
    assert not errors
