"""Navigation und Fehlermarkierung bleiben zwischen HTML und AJAX konsistent."""

import re
from html import unescape
from urllib.parse import parse_qs, urlsplit

from app.data.parts.model import PartItem
from app.data.repairs.model import RepairStep
from app.extensions import db
from tests.integration.devices.test_devices import csrf
from tests.integration.devices.test_devices import owner as owner
from tests.integration.repairs.test_repairs import create


def test_step_pagination_preserves_parts_and_device_context(owner, identity_app):
    rid = create(owner)
    with identity_app.app_context():
        from app.data.repairs.model import Repair

        device = db.session.get(Repair, rid).device_id
        db.session.add_all(
            RepairStep(repair_id=rid, description=f"Step {i}", completed=False) for i in range(25)
        )
        db.session.add_all(
            PartItem(repair_id=rid, name=f"Part {i}", unit_price=1, quantity=1) for i in range(25)
        )
        db.session.commit()
    response = owner.get(f"/repairs/{rid}?device_id={device}&part_offset=20")
    link = re.search(r'href="([^"]+)"[^>]*>Next steps</a>', response.text)[1]
    assert parse_qs(urlsplit(unescape(link)).query) == {
        "offset": ["20"],
        "part_offset": ["20"],
        "device_id": [str(device)],
    }
    response = owner.get(unescape(link))
    previous = re.search(r'href="([^"]+)"[^>]*>Previous steps</a>', response.text)[1]
    assert parse_qs(urlsplit(unescape(previous)).query)["part_offset"] == ["20"]


def test_html_numeric_errors_preserve_valid_inputs_and_mark_invalid_field(owner):
    rid = create(owner)
    response = owner.post(
        f"/repairs/{rid}/parts",
        data={"csrf_token": csrf(owner), "name": "Cable", "unit_price": "15", "quantity": "0"},
        headers={"Referer": "https://localhost/"},
    )
    assert response.status_code == 422
    assert re.search(r'<input[^>]*aria-invalid="true"[^>]*id="new-part-quantity"', response.text)
    assert 'value="Cable"' in response.text and 'value="15"' in response.text


def test_expired_session_json_has_actionable_message(identity_app):
    response = identity_app.test_client().get("/repairs", headers={"Accept": "application/json"})
    assert response.status_code == 401
    assert response.json == {"error": "Your session has expired. Please log in again."}


def test_expired_post_cannot_mutate_and_returns_login_hint(owner, identity_app):
    rid = create(owner)
    response = identity_app.test_client().post(
        f"/repairs/{rid}/description",
        json={"description": "Not authorized"},
        headers={
            "Accept": "application/json",
            "X-CSRFToken": "expired",
            "Referer": "https://localhost/",
        },
    )
    assert response.status_code == 401
    assert response.json == {"error": "Your session has expired. Please log in again."}
    assert "Not authorized" not in owner.get(f"/repairs/{rid}").text
