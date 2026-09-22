"""Die Übersicht zählt eigene Fälle unabhängig von Filtern und Listenfenstern."""

import re

from app.data.repairs.model import Repair
from app.extensions import db
from tests.integration.devices.test_devices import owner as owner
from tests.integration.devices.test_devices import save
from tests.integration.repairs.test_repairs import create, post
from tests.integration.users.test_registration import PASSWORD, confirmation, register, submit


def counts(response):
    assert response.status_code == 200
    return {
        state: int(count)
        for state, count in re.findall(r'data-status-count="(\w+)">(\d+)', response.text)
    }


def test_empty_overview_and_authentication(owner, identity_app):
    assert counts(owner.get("/repairs")) == {"open": 0, "in_progress": 0, "completed": 0}
    assert identity_app.test_client().get("/repairs").status_code == 302
    german = owner.get("/repairs", headers={"Accept-Language": "de"}).text
    assert "Deine Reparaturübersicht" in german


def test_counts_ignore_filters_and_windows_but_never_ownership(owner, identity_app):
    device = save(owner).json["device"]["id"]
    with identity_app.app_context():
        db.session.add_all(
            Repair(device_id=device, description=f"Fault {i}", status="open") for i in range(65)
        )
        db.session.commit()
    rid = create(owner, description="Another device")
    post(owner, f"/repairs/{rid}/status", status="completed")
    other = identity_app.test_client()
    register(other, username="OverviewOther", email="overview-other@example.org")
    other.get(confirmation(identity_app))
    submit(other, "/login", identity="OverviewOther", password=PASSWORD)
    foreign = create(other)
    post(other, f"/repairs/{foreign}/status", status="in_progress")
    expected = {"open": 65, "in_progress": 0, "completed": 1}
    for query in (
        {},
        {"q": "missing"},
        {"device_id": device, "status": "open"},
        {"offset": 60, "limit": 20},
        {"snapshot": 0},
    ):
        assert counts(owner.get("/repairs", query_string=query)) == expected
    assert counts(other.get("/repairs")) == {"open": 0, "in_progress": 1, "completed": 0}
    for state in ("in_progress", "open", "completed"):
        assert post(owner, f"/repairs/{rid}/status", status=state).status_code == 200
        expected = {"open": 65, "in_progress": 0, "completed": 0}
        expected[state] += 1
        assert counts(owner.get("/repairs")) == expected
