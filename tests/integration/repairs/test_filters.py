"""Suchbeispiele mit PostgreSQL: kombinierte Filter, Literalzeichen und Eigentum."""

import pytest

from app.data.repairs.model import Repair
from app.extensions import db
from tests.integration.devices.test_devices import owner as owner
from tests.integration.devices.test_devices import save
from tests.integration.repairs.test_repairs import create, post
from tests.integration.users.test_registration import PASSWORD, confirmation, register, submit

HEADERS = {"Accept": "application/json"}


def listing(client, **query):
    return client.get("/repairs", query_string=query, headers=HEADERS)


def test_words_across_fields_status_and_literal_wildcards(owner):
    device = save(owner, name="Kitchen radio", manufacturer="Müller", model="RX-50").json["device"][
        "id"
    ]
    rid = create(owner, device, "Warm 50% volume_under / quiet")
    other = create(owner, description="Cold fault")
    post(owner, f"/repairs/{other}/status", status="completed")
    for search in ("RAD", "müll", "rx-50", "WARM", "RAD warm MÜLL", "%", "_", "/"):
        result = listing(owner, q=search, status="open")
        assert result.status_code == 200
        assert [item["id"] for item in result.json["items"]] == [rid]
        assert result.json["total"] == 1
    for search in ("missing", "warm cold", "' OR 1=1 --", "<script>", "\\"):
        assert listing(owner, q=search).json["total"] == 0
    assert listing(owner, q="warm", status="completed").json["items"] == []
    assert listing(owner, q="  ", status="").json["total"] == 2
    for state in ("in_progress", "completed", "open"):
        post(owner, f"/repairs/{rid}/status", status=state)
        assert listing(owner, q="warm", status=state).json["total"] == 1


def test_filter_count_snapshot_and_windows_do_not_leak_other_users(owner, identity_app):
    device = save(owner).json["device"]["id"]
    with identity_app.app_context():
        db.session.add_all(
            Repair(device_id=device, description=f"matching fault {i}", status="open")
            for i in range(85)
        )
        db.session.add(Repair(device_id=device, description="matching fault", status="completed"))
        db.session.commit()
    query = {"q": "matching", "status": "open", "device_id": device}
    first = listing(owner, **query, limit=60).json
    assert first["total"] == 85 and len(first["items"]) == 60
    create(owner, device, "matching new fault")
    second = listing(owner, **query, offset=60, limit=60, snapshot=first["snapshot"]).json
    assert second["total"] == 85 and len(second["items"]) == 25
    assert not {item["id"] for item in first["items"]} & {item["id"] for item in second["items"]}
    html = owner.get("/repairs", query_string=query).text
    assert html.count('class="repair-card"') == 20
    assert "q=matching" in html and "status=open" in html
    assert "offset=20" in html
    foreign = identity_app.test_client()
    register(foreign, username="SearchOther", email="search-other@example.org")
    foreign.get(confirmation(identity_app))
    submit(foreign, "/login", identity="SearchOther", password=PASSWORD)
    result = listing(foreign, q="matching", status="open", snapshot=first["snapshot"]).json
    assert result["items"] == [] and result["total"] == 0
    assert listing(foreign, **query).status_code == 404
    assert listing(foreign, q="matching", device_id=999999).status_code == 404
    assert listing(identity_app.test_client(), q="matching").status_code == 401


@pytest.mark.parametrize("query", [{"q": "x" * 201}, {"q": "a\x00b"}, {"status": "invalid"}])
def test_invalid_filters_are_bad_requests_for_html_and_json(owner, query):
    assert listing(owner, **query).status_code == 400
    assert owner.get("/repairs", query_string=query).status_code == 400


def test_empty_translated_state_and_detail_return_context(owner):
    rid = create(owner, description="Matching fault")
    response = owner.get("/repairs?q=absent&status=open", headers={"Accept-Language": "de"})
    assert "Keine passenden Reparaturfälle." in response.text
    assert "Filter zurücksetzen" in response.text
    row = listing(owner, q="Matching", status="open").json["items"][0]
    detail = owner.get(row["url"]).text
    assert "q=Matching" in detail and "status=open" in detail
    updated = post(
        owner, f"/repairs/{rid}/description?q=Matching&status=open", description="Matching updated"
    )
    assert "q=Matching" in updated.json["url"]
    assert "status=open" in updated.json["url"]
    escaped = owner.get("/repairs?q=%22%3E%3Cscript%3E").text
    assert "<script>" not in escaped and "&lt;script&gt;" in escaped
