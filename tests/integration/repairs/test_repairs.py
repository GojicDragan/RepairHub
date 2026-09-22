"""Echte PostgreSQL-/Sitzungsabläufe inklusive Fremdzugriff, CSRF und Datenintegrität."""

import re
from unittest.mock import patch

import pytest
from flask_migrate import upgrade
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.data.repairs.model import Repair, RepairStep
from app.extensions import db
from tests.integration.devices.test_devices import csrf, save
from tests.integration.devices.test_devices import owner as owner
from tests.integration.users.test_registration import PASSWORD, confirmation, register, submit


def post(client, path, **values):
    return client.post(
        path,
        json=values,
        headers={
            "Accept": "application/json",
            "X-CSRFToken": csrf(client),
            "Referer": "https://localhost/",
        },
    )


def create(client, device=None, description="Radio switches off when warm"):
    device = device or save(client).json["device"]["id"]
    response = post(client, f"/devices/{device}/repairs/new", description=description)
    assert response.status_code == 200, response.text
    return int(re.search(r"/repairs/(\d+)", response.json["url"])[1])


def step_id(response):
    assert response.status_code == 200, response.text
    return int(re.search(r'data-step-id="(\d+)"', response.json["html"])[1])


def test_full_repair_lifecycle_persists_and_can_be_reopened(owner, identity_app):
    repair_id = create(owner)
    for state in ("in_progress", "completed", "in_progress", "open"):
        response = post(owner, f"/repairs/{repair_id}/status", status=state)
        assert response.status_code == 200
        assert f"repair-status-{state}" in response.json["html"]
        assert f"repair-status-{state}" in owner.get("/repairs").text
    response = post(
        owner, f"/repairs/{repair_id}/description", description="  New fault\nSecond line  "
    )
    assert "New fault\nSecond line" in response.json["html"]
    sid = step_id(post(owner, f"/repairs/{repair_id}/steps", description="Check cable"))
    for done in (True, True, False):
        assert (
            post(
                owner,
                f"/repairs/{repair_id}/steps/{sid}",
                description="Replace cable",
                completed=done,
            ).status_code
            == 200
        )
        with identity_app.app_context():
            row = db.session.get(RepairStep, sid)
            assert row.completed is done
            assert row.description == "Replace cable"
    with identity_app.app_context():
        row = db.session.get(Repair, repair_id)
        assert row.status == "open" and row.created_at.tzinfo is not None
        assert row.description == "New fault\nSecond line"


def test_foreign_and_unknown_objects_are_indistinguishable(owner, identity_app):
    device_id = save(owner).json["device"]["id"]
    repair_id = create(owner, device_id)
    sid = step_id(post(owner, f"/repairs/{repair_id}/steps", description="Private step"))
    other = identity_app.test_client()
    register(other, username="Other", email="other@example.org")
    other.get(confirmation(identity_app))
    submit(other, "/login", identity="Other", password=PASSWORD)
    assert str(repair_id) not in re.findall(r'/repairs/(\d+)"', other.get("/repairs").text)
    paths = [
        f"/repairs/{repair_id}",
        f"/devices/{device_id}/repairs/new",
        f"/repairs?device_id={device_id}",
    ]
    for path in paths:
        assert other.get(path).status_code == 404
    for path, values in [
        (f"/devices/{device_id}/repairs/new", {"description": "x"}),
        (f"/repairs/{repair_id}/description", {"description": "x"}),
        (f"/repairs/{repair_id}/status", {"status": "completed"}),
        (f"/repairs/{repair_id}/steps", {"description": "x"}),
        (f"/repairs/{repair_id}/steps/{sid}", {"description": "x", "completed": True}),
    ]:
        response = post(other, path, **values)
        assert response.status_code == 404
        assert response.json == {"error": "Repair not found."}
    assert other.get("/repairs/999999").status_code == 404
    own_repair = create(other)
    assert (
        post(
            other, f"/repairs/{own_repair}/steps/{sid}", description="Hijack", completed=True
        ).status_code
        == 404
    )
    another = create(owner)
    assert (
        post(
            owner, f"/repairs/{another}/steps/{sid}", description="Wrong case", completed=True
        ).status_code
        == 404
    )


@pytest.mark.parametrize("description", ["", " \n\t", "bad\x00value", "x" * 10001, None, []])
def test_invalid_fault_does_not_change_saved_data(owner, description):
    rid = create(owner)
    assert post(owner, f"/repairs/{rid}/description", description=description).status_code == 422
    assert "Radio switches off when warm" in owner.get(f"/repairs/{rid}").text


@pytest.mark.parametrize("value", ["closed", "", None, [], 1])
def test_invalid_status_is_rejected(owner, value):
    rid = create(owner)
    assert post(owner, f"/repairs/{rid}/status", status=value).status_code == 422
    assert "repair-status-open" in owner.get(f"/repairs/{rid}").text


def test_steps_validate_description_and_boolean(owner):
    rid = create(owner)
    for value in ("", "x" * 2001):
        assert post(owner, f"/repairs/{rid}/steps", description=value).status_code == 422
    sid = step_id(post(owner, f"/repairs/{rid}/steps", description="Check cable"))
    for value in ("false", 0, 1, None):
        assert (
            post(
                owner, f"/repairs/{rid}/steps/{sid}", description="Cable", completed=value
            ).status_code
            == 422
        )


def test_html_fallback_preserves_input_and_saves_checkbox(owner):
    rid = create(owner)
    sid = step_id(post(owner, f"/repairs/{rid}/steps", description="First step"))
    response = owner.post(
        f"/repairs/{rid}/steps/{sid}",
        data={"csrf_token": csrf(owner), "description": "Changed step", "completed": "true"},
        headers={"Referer": "https://localhost/"},
    )
    assert response.status_code == 303
    assert "is-completed" in owner.get(response.location).text
    response = owner.post(
        f"/repairs/{rid}/description",
        data={"csrf_token": csrf(owner), "description": " "},
        headers={"Referer": "https://localhost/"},
    )
    assert response.status_code == 422
    assert "This field is required." in response.text


def test_csrf_authentication_escaping_and_ignored_assignment(owner, identity_app):
    rid = create(owner, description='<script>alert("x")</script>')
    page = owner.get(f"/repairs/{rid}")
    assert '<script>alert("x")</script>' not in page.text
    assert "&lt;script&gt;" in page.text
    assert "no-store" in page.headers["Cache-Control"]
    assert owner.post(f"/repairs/{rid}/status", json={"status": "completed"}).status_code == 400
    anonymous = identity_app.test_client()
    assert (
        anonymous.get(f"/repairs/{rid}", headers={"Accept": "application/json"}).status_code == 401
    )
    assert anonymous.get(f"/repairs/{rid}").status_code == 302
    assert (
        post(
            owner, f"/repairs/{rid}/description", description="Safe", device_id=9999, owner_id=9999
        ).status_code
        == 200
    )
    with identity_app.app_context():
        assert db.session.get(Repair, rid).device_id != 9999
    assert owner.get(f"/repairs/{rid}/status").status_code == 405


def test_windows_and_appending_last_step(owner, identity_app):
    rid = create(owner)
    with identity_app.app_context():
        device_id = db.session.get(Repair, rid).device_id
        db.session.add_all(Repair(device_id=device_id, description=f"Fault {i}") for i in range(25))
        db.session.add_all(RepairStep(repair_id=rid, description=f"Step {i}") for i in range(25))
        db.session.commit()
    assert owner.get("/repairs").text.count('class="repair-card"') == 20
    assert owner.get("/repairs?offset=20").text.count('class="repair-card"') == 6
    assert owner.get(f"/repairs/{rid}").text.count("data-step-id=") == 20
    response = post(owner, f"/repairs/{rid}/steps", description="Newest step")
    assert "offset=20" in response.json["url"] and "Newest step" in response.json["html"]
    assert owner.get("/repairs?offset=-1").status_code == 400


def test_storage_constraints_and_transaction_rollback(owner, identity_app):
    rid = create(owner)
    with identity_app.app_context():
        for sql in (
            "UPDATE repairs SET status='invalid'",
            "UPDATE repairs SET description=' '",
            "INSERT INTO repairs(device_id,description) VALUES (999999,'Missing parent')",
            "INSERT INTO repair_steps(repair_id,description) VALUES (999999,'Missing parent')",
            f"INSERT INTO repair_steps(repair_id,description) VALUES ({rid},' ')",
        ):
            with pytest.raises(IntegrityError):
                db.session.execute(text(sql))
                db.session.commit()
            db.session.rollback()
    with patch.object(db.session, "commit", side_effect=RuntimeError("write failed")):
        response = post(owner, f"/repairs/{rid}/description", description="Should roll back")
    assert response.status_code == 500
    assert "Radio switches off when warm" in owner.get(f"/repairs/{rid}").text


@pytest.mark.parametrize("identity_app", ["0002_devices"], indirect=True)
def test_migration_preserves_users_and_devices(owner, identity_app):
    device_id = save(owner).json["device"]["id"]
    with identity_app.app_context():
        upgrade()
        assert db.session.scalar(select(func.count()).select_from(Repair)) == 0
    assert owner.get(f"/devices/{device_id}").status_code == 200
    create(owner, device_id)


def test_virtual_list_bounds_snapshot_filter_and_ownership(owner, identity_app):
    rid = create(owner)
    with identity_app.app_context():
        device_id = db.session.get(Repair, rid).device_id
        db.session.add_all(
            Repair(device_id=device_id, description=f"Window {i}") for i in range(125)
        )
        db.session.commit()
    headers = {"Accept": "application/json"}
    first = owner.get(f"/repairs?device_id={device_id}&limit=60", headers=headers)
    assert first.status_code == 200
    page = first.json
    assert len(page["items"]) == 60 and page["total"] == 126
    assert all(f"device_id={device_id}" in item["url"] for item in page["items"])
    create(owner, device_id)
    frozen = owner.get(
        f"/repairs?device_id={device_id}&limit=60&snapshot={page['snapshot']}", headers=headers
    ).json
    assert frozen == page
    second = owner.get(
        f"/repairs?offset=60&limit=60&snapshot={page['snapshot']}", headers=headers
    ).json
    assert not ({item["id"] for item in page["items"]} & {item["id"] for item in second["items"]})
    assert owner.get("/repairs?limit=60").text.count('class="repair-card"') == 20
    for query in (
        "limit=61",
        "limit=0",
        "snapshot=-1",
        "snapshot=9223372036854775808",
        "offset=invalid",
    ):
        assert owner.get("/repairs?" + query, headers=headers).status_code == 400
    assert owner.get("/repairs?device_id=999999", headers=headers).status_code == 404
    other = identity_app.test_client()
    register(other, username="WindowOther", email="windowother@example.org")
    other.get(confirmation(identity_app))
    submit(other, "/login", identity="WindowOther", password=PASSWORD)
    assert other.get(f"/repairs?snapshot={page['snapshot']}", headers=headers).json["items"] == []
    assert other.get(f"/repairs?device_id={device_id}", headers=headers).status_code == 404
    assert identity_app.test_client().get("/repairs", headers=headers).status_code == 401
