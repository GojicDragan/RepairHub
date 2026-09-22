"""Geräteslices über echte Sitzungen, CSRF und PostgreSQL abnehmen."""

import re

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.data.devices.model import Device
from app.extensions import db
from tests.integration.users.test_registration import PASSWORD, confirmation, register, submit


@pytest.fixture
def owner(identity_app):
    client = identity_app.test_client()
    register(client)
    client.get(confirmation(identity_app))
    submit(client, "/login", identity="Lea", password=PASSWORD)
    return client


def csrf(client):
    return re.search(r'name="csrf_token"[^>]*value="([^"]+)"', client.get("/devices/new").text)[1]


def save(client, path="/devices/new", **values):
    return client.post(
        path,
        json={"name": "Radio", "manufacturer": "Maker", "model": "R1", **values},
        headers={
            "Accept": "application/json",
            "X-CSRFToken": csrf(client),
            "Referer": "https://localhost/devices/new",
        },
    )


def listing(client, query=""):
    return client.get("/devices" + query, headers={"Accept": "application/json"})


def test_create_update_and_render_persisted_values(owner, identity_app):
    response = save(owner, name="  Kitchen radio  ", owner_id=999, id=999)
    assert response.status_code == 201
    device = response.json["device"]
    assert device["name"] == "Kitchen radio"
    assert set(device) == {"id", "name", "manufacturer", "model"}
    assert owner.get(response.json["url"]).status_code == 200
    changed = save(
        owner, response.json["edit_url"], name="Bedroom radio", manufacturer="Other", model="R2"
    )
    assert changed.status_code == 200
    assert "Bedroom radio" in owner.get(response.json["url"]).text
    assert listing(owner).json["items"] == [changed.json["device"]]
    with identity_app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Device)) == 1
        assert db.session.scalar(select(Device)).owner_id != 999


@pytest.mark.parametrize("path", ["/devices", "/devices/new", "/devices/1", "/devices/1/edit"])
def test_requires_authenticated_session(identity_app, path):
    client = identity_app.test_client()
    assert client.get(path).status_code == 302
    assert client.get(path, headers={"Accept": "application/json"}).status_code == 401


def test_unknown_and_foreign_devices_are_indistinguishable(owner, identity_app):
    created = save(owner).json["device"]
    other = identity_app.test_client()
    register(other, "Other", "other@example.org")
    other.get(confirmation(identity_app))
    submit(other, "/login", identity="Other", password=PASSWORD)
    assert listing(other).json["items"] == []
    for suffix in ["", "/edit"]:
        foreign = other.get(f"/devices/{created['id']}{suffix}")
        missing = other.get(f"/devices/999999{suffix}")
        assert foreign.status_code == missing.status_code == 404
        assert foreign.data == missing.data
    for device_id in [created["id"], 999999, 2**64]:
        response = save(other, f"/devices/{device_id}/edit", name="")
        assert response.status_code == 404
        assert response.json == {"error": "Device not found."}
    assert listing(owner).json["items"][0]["name"] == "Radio"


@pytest.mark.parametrize("field", ["name", "manufacturer", "model"])
@pytest.mark.parametrize("invalid", ["", " \t ", "x" * 121, None, 12, "a\x00b"])
def test_domain_validation_is_authoritative_over_ajax(owner, identity_app, field, invalid):
    response = save(owner, **{field: invalid})
    assert response.status_code == 422 and field in response.json["errors"]
    with identity_app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Device)) == 0


def test_failed_edit_keeps_database_and_form_values(owner):
    created = save(owner).json
    response = owner.post(
        created["edit_url"],
        data={
            "csrf_token": csrf(owner),
            "name": "My radio",
            "manufacturer": "",
            "model": "Valid model",
        },
        headers={"Referer": "https://localhost/"},
    )
    assert response.status_code == 422
    assert 'value="My radio"' in response.text and 'value="Valid model"' in response.text
    assert listing(owner).json["items"][0]["name"] == "Radio"


def test_csrf_is_required_for_ajax_create_and_edit(owner):
    created = save(owner).json
    for path in ["/devices/new", created["edit_url"]]:
        response = owner.post(
            path, json={"name": "Changed"}, headers={"Accept": "application/json"}
        )
        assert response.status_code == 400
    assert listing(owner).json["items"][0]["name"] == "Radio"


def test_bounded_windows_stay_stable_when_another_device_is_created(owner, identity_app):
    first = save(owner).json["device"]
    with identity_app.app_context():
        owner_id = db.session.get(Device, first["id"]).owner_id
        db.session.add_all(
            Device(owner_id=owner_id, name=f"Device {i}", manufacturer="Maker", model="Model")
            for i in range(124)
        )
        db.session.commit()
    initial = owner.get("/devices")
    assert initial.text.count("data-device-id=") == 20
    page = listing(owner, "?offset=20&limit=60").json
    assert len(page["items"]) == 60 and page["total"] == 125
    save(owner, name="New arrival")
    last = listing(owner, f"?offset=120&snapshot={page['snapshot']}").json
    assert len(last["items"]) == 5 and last["total"] == 125
    assert listing(owner).json["total"] == 126
    for query in [
        "?limit=61",
        "?offset=-1",
        "?snapshot=bad",
        "?offset=bad",
        "?limit=0",
        "?offset=18446744073709551616",
    ]:
        assert listing(owner, query).status_code == 400


def test_device_text_is_escaped_and_pages_are_private(owner):
    response = save(owner, name='<script>alert("test")</script>')
    for path in ["/devices", response.json["url"], response.json["edit_url"]]:
        page = owner.get(path)
        assert "<script>alert" not in page.text
        assert "&lt;script&gt;" in page.text
        assert page.headers["Cache-Control"] == "no-store"
        assert "noindex, nofollow" in page.text


def test_database_constraints_reject_blank_values_and_missing_owner(owner, identity_app):
    created = save(owner).json["device"]
    with identity_app.app_context():
        for statement in [
            "UPDATE devices SET name = '   '",
            "UPDATE devices SET manufacturer = NULL",
            "UPDATE devices SET owner_id = 999999",
            "UPDATE devices SET model = repeat('x', 121)",
        ]:
            from sqlalchemy.exc import DataError

            with pytest.raises((IntegrityError, DataError)):
                db.session.execute(text(statement))
                db.session.commit()
            db.session.rollback()
        assert db.session.get(Device, created["id"]).name == "Radio"


def test_save_failure_rolls_back_without_exposing_internal_details(
    owner, identity_app, monkeypatch
):
    with identity_app.app_context():

        def fail():
            raise RuntimeError("private-database-detail")

        monkeypatch.setattr(db.session, "commit", fail)
        response = save(owner)
        assert response.status_code == 500 and "private-database-detail" not in response.text
        assert db.session.scalar(select(func.count()).select_from(Device)) == 0


@pytest.mark.parametrize("identity_app", ["0001_register_user"], indirect=True)
def test_upgrade_preserves_existing_accounts_and_enables_devices(identity_app):
    from flask_migrate import check, upgrade

    from app.data.users.model import User
    from tests.support.legacy_user import seed_user

    with identity_app.app_context():
        user_id = seed_user()
        upgrade()
        check()
        assert db.session.get(User, user_id).username == "Lea"
    client = identity_app.test_client()
    submit(client, "/login", identity="Lea", password=PASSWORD)
    response = save(client)
    assert response.status_code == 201
    assert listing(client).json["total"] == 1


def suggestions(client, **query):
    return client.get(
        "/devices/suggestions", query_string=query, headers={"Accept": "application/json"}
    )


def test_suggestions_learn_saved_values_and_filter_models(owner, identity_app):
    save(owner, name="Kitchen radio", manufacturer="Maker", model="R100")
    save(owner, name="Other radio", manufacturer="maker", model="R100")
    save(owner, manufacturer="Other", model="R200")
    assert len(suggestions(owner, field="manufacturer", term="MA").json["items"]) == 1
    assert suggestions(owner, field="model", term="R1", manufacturer="MAKER").json == {
        "items": ["R100"]
    }
    assert suggestions(owner, field="model", term="R2", manufacturer="Maker").json == {"items": []}
    assert suggestions(owner, field="name", term="kitchen").json == {"items": ["Kitchen radio"]}
    # Ein zweites bestätigtes Konto darf keine Werte des ersten sehen.
    other = identity_app.test_client()
    register(other, username="Other", email="other@example.org")
    other.get(confirmation(identity_app))
    submit(other, "/login", identity="Other", password=PASSWORD)
    assert suggestions(other, field="manufacturer", term="Ma").json == {"items": []}


def test_suggestions_validate_and_escape_queries(owner, identity_app):
    save(owner, name="A%_test", model="R100")
    assert suggestions(owner, field="name", term="%_").json == {"items": ["A%_test"]}
    assert suggestions(owner, field="name", term="' OR 1=1 --").json == {"items": []}
    assert suggestions(owner, field="name", term="A").json == {"items": []}
    for query in [dict(field="password", term="ab"), dict(field="name", term="x" * 121)]:
        assert suggestions(owner, **query).status_code == 400
    assert suggestions(identity_app.test_client(), field="name", term="ab").status_code == 401
    assert "no-store" in suggestions(owner, field="name", term="test").headers["Cache-Control"]


def test_suggestions_are_limited_and_failed_saves_are_not_learned(owner):
    for number in range(12):
        save(owner, name=f"Radio {number:02d}")
    assert len(suggestions(owner, field="name", term="Radio").json["items"]) == 10
    assert save(owner, name="Rejected device", manufacturer="").status_code == 422
    assert suggestions(owner, field="name", term="Rejected").json == {"items": []}


@pytest.mark.parametrize("field", ["name", "manufacturer", "model"])
def test_suggestions_match_parts_anywhere_in_any_order(owner, field):
    save(owner, **{field: "Küche – grosses Radio"})
    for term in ("RADIO", "ÜCHE", "radio küche", "  dio   ÜCH  "):
        assert suggestions(owner, field=field, term=term).json == {
            "items": ["Küche – grosses Radio"]
        }
    assert suggestions(owner, field=field, term="radio fehlt").json == {"items": []}
