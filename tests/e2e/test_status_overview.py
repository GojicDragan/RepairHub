"""Statuszahlen bleiben mit und ohne JavaScript sowie auf schmalen Geräten lesbar."""

from pathlib import Path

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
        {"javascript": False, "locale": "de-CH"},
    ],
    indirect=True,
)
def test_status_overview(page, device_account, live_application, request):
    login(page, device_account)
    page.goto("/repairs")
    for state in ("open", "in_progress", "completed"):
        expect(page.locator(f'[data-status-count="{state}"]')).to_have_text("0")
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
    db.session.add_all(Repair(device_id=device.id, description='Fault', status=state)
                      for state in ('open', 'open', 'in_progress', 'completed'))
    db.session.commit()
""",
        device_account,
        capture=True,
    )
    page.goto("/repairs?q=absent")
    for state, count in (("open", "2"), ("in_progress", "1"), ("completed", "1")):
        expect(page.locator(f'[data-status-count="{state}"]')).to_have_text(count)
    german = request.node.callspec.params["page"]["locale"] == "de-CH"
    expect(page.locator("#overview-heading")).to_have_text(
        "Deine Reparaturübersicht" if german else "Your repair overview"
    )
    for width in (1280, 390):
        page.set_viewport_size({"width": width, "height": 900})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        for state in ("open", "in_progress", "completed"):
            expect(page.locator(f'[data-status-count="{state}"]')).to_be_visible()
        path = Path(f"reports/kt03/overview-{width}-{'de' if german else 'en'}.png")
        path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(path), full_page=True)
