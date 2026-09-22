"""Eigene Gerätesuche über echte PostgreSQL-Abfragen und HTTP-Fenster."""

import pytest

from app.data.devices.model import Device
from app.extensions import db
from tests.integration.devices.test_devices import listing, save
from tests.integration.devices.test_devices import owner as owner
from tests.integration.users.test_registration import PASSWORD, confirmation, register, submit


def search(client, term, **window):
    return client.get(
        "/devices", query_string={"q": term, **window}, headers={"Accept": "application/json"}
    )


def test_terms_cross_fields_and_wildcards_are_literal(owner):
    matching = save(
        owner, name="Kitchen radio 50%_quiet", manufacturer="Müller", model="RX/200"
    ).json["device"]
    save(owner, name="Other appliance", manufacturer="Brand", model="R2")
    for term in ("RAD", "MÜLL", "rx/2", "  RAD   müll  ", "%", "_"):
        result = search(owner, term)
        assert result.status_code == 200
        assert result.json["items"] == [matching]
        assert result.json["total"] == 1
    for term in ("absent", "radio Brand", "' OR 1=1 --", "\\", "<script>"):
        assert search(owner, term).json["total"] == 0
    assert search(owner, " ").json["total"] == 2
    assert search(owner, "mueller").json["total"] == 0


def test_search_scopes_count_snapshot_and_every_window(owner, identity_app):
    first = save(owner, name="Window 000").json["device"]
    with identity_app.app_context():
        uid = db.session.get(Device, first["id"]).owner_id
        db.session.add_all(
            Device(owner_id=uid, name=f"Window {i:03}", manufacturer="Maker", model="RX")
            for i in range(1, 85)
        )
        db.session.commit()
    initial = search(owner, "window", limit=60).json
    assert initial["total"] == 85 and len(initial["items"]) == 60
    save(owner, name="Window new")
    later = search(owner, "window", offset=60, limit=60, snapshot=initial["snapshot"]).json
    assert later["total"] == 85 and len(later["items"]) == 25
    assert not {i["id"] for i in initial["items"]} & {i["id"] for i in later["items"]}
    html = owner.get("/devices?q=window").text
    assert html.count('class="device-row"') == 20
    assert "q=window" in html and "offset=20" in html
    other = identity_app.test_client()
    register(other, username="SearchOther", email="device-search-other@example.org")
    other.get(confirmation(identity_app))
    submit(other, "/login", identity="SearchOther", password=PASSWORD)
    assert search(other, "window").json == {"items": [], "offset": 0, "snapshot": 0, "total": 0}
    assert search(other, "window", snapshot=initial["snapshot"]).json["items"] == []
    assert search(identity_app.test_client(), "window").status_code == 401


@pytest.mark.parametrize("term", ["x" * 201, "bad\x00value", "bad\nvalue"])
def test_invalid_search_rejected_in_json_and_html(owner, term):
    assert search(owner, term).status_code == 400
    assert owner.get("/devices", query_string={"q": term}).status_code == 400


def test_search_context_survives_detail_edit_and_translated_empty_state(owner):
    device = save(owner, name="Kitchen radio").json["device"]
    device_id = device["id"]
    for path in (f"/devices/{device_id}", f"/devices/{device_id}/edit"):
        html = owner.get(path + "?q=Kitchen").text
        assert "/devices?q=Kitchen" in html
    changed = save(owner, f"/devices/{device_id}/edit?q=Kitchen", name="Kitchen receiver")
    assert "?q=Kitchen" in changed.json["url"]
    assert search(owner, "radio").json["total"] == 0
    assert search(owner, "receiver").json["total"] == 1
    html = owner.get("/devices?q=absent", headers={"Accept-Language": "de"}).text
    assert "Keine passenden Geräte." in html
    assert "data-list-empty" in html
    escaped = owner.get("/devices?q=%22%3E%3Cscript%3E").text
    assert "<script>" not in escaped and "&lt;script&gt;" in escaped
    assert listing(owner).json["total"] == 1
