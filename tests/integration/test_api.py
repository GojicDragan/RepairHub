"""Persönliche API-Keys, Eigentum und Listenfenster mit echter PostgreSQL-Persistenz."""

import hashlib
import re
from decimal import Decimal

import pytest

from app.data.parts.model import PartItem
from app.data.repairs.model import RepairStep
from app.data.users.model import User
from app.extensions import db
from tests.integration.devices.test_devices import owner as owner
from tests.integration.repairs.test_repairs import create, post
from tests.integration.users.test_registration import PASSWORD, confirmation, register, submit


def create_key(owner):
    response = submit(owner, "/account/api-key")
    assert response.status_code == 200
    key = re.search(r'id="api-key-value"[^>]*>([^<]+)</textarea>', response.text)[1]
    assert response.headers["Cache-Control"] == "no-store"
    return key


def bearer(key):
    return {"Authorization": "Bearer " + key}


def test_key_is_one_time_hashed_and_owner_bound(owner, identity_app):
    key = create_key(owner)
    assert len(key) == 46 and key.startswith("rh_")
    assert key not in owner.get("/account/api-key").text
    with owner.session_transaction() as session:
        assert key not in str(dict(session))
    with identity_app.app_context():
        user = db.session.query(User).first()
        assert user.api_key_hash == hashlib.sha256(key.encode()).hexdigest()
        assert user.api_key_hash != key
        assert user.api_key_identity == user.fs_uniquifier
    client = identity_app.test_client()
    response = client.get("/api/repairs", headers=bearer(key))
    assert response.status_code == 200 and response.json["items"] == []
    assert response.headers.get("Set-Cookie") is None
    assert client.get("/devices").status_code == 302


def test_complete_detail_and_shared_costs(owner, identity_app):
    rid = create(owner)
    post(owner, f"/repairs/{rid}/work", hours="0.25", hourly_rate="0.10")
    with identity_app.app_context():
        db.session.add_all(
            [
                PartItem(repair_id=rid, name=f"Part {i}", unit_price=Decimal("0.10"), quantity=3)
                for i in range(25)
            ]
        )
        db.session.add_all(
            [RepairStep(repair_id=rid, description=f"Step {i}", completed=False) for i in range(25)]
        )
        db.session.commit()
    client = identity_app.test_client()
    response = client.get(f"/api/repairs/{rid}", headers=bearer(create_key(owner)))
    assert response.status_code == 200
    assert len(response.json["parts"]) == len(response.json["steps"]) == 25
    assert response.json["costs"] == {
        "currency": "CHF",
        "labor": "0.03",
        "parts": "7.50",
        "total": "7.53",
    }
    assert response.json["work"] == {"hours": "0.25", "hourly_rate": "0.10"}
    assert "CHF 7.53" in owner.get(f"/repairs/{rid}").text
    assert response.headers["Cache-Control"] == "no-store"


def test_rotation_revocation_and_csrf(owner, identity_app):
    first = create_key(owner)
    second = create_key(owner)
    client = identity_app.test_client()
    assert client.get("/api/repairs", headers=bearer(first)).status_code == 401
    assert client.get("/api/repairs", headers=bearer(second)).status_code == 200
    assert owner.post("/account/api-key/revoke").status_code == 400
    assert owner.post("/account/api-key").status_code == 400
    token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', owner.get("/account/api-key").text)[
        1
    ]
    response = owner.post(
        "/account/api-key/revoke",
        data={"csrf_token": token},
        headers={"Referer": "https://localhost/account/api-key"},
    )
    assert response.status_code == 303
    assert client.get("/api/repairs", headers=bearer(second)).status_code == 401
    assert "No API key is active." in owner.get("/account/api-key").text
    assert client.get("/account/api-key").status_code == 302
    with identity_app.app_context():
        row = db.session.query(User).first()
        assert row.api_key_hash is row.api_key_identity is row.api_key_created_at is None


@pytest.mark.parametrize("change", ["active", "confirmed_at", "fs_uniquifier"])
def test_account_change_revokes_key(owner, identity_app, change):
    key = create_key(owner)
    with identity_app.app_context():
        user = db.session.query(User).first()
        setattr(
            user,
            change,
            {"active": False, "confirmed_at": None, "fs_uniquifier": "rotated"}[change],
        )
        db.session.commit()
    assert identity_app.test_client().get("/api/repairs", headers=bearer(key)).status_code == 401


@pytest.mark.parametrize(
    "authorization",
    [
        None,
        "Bearer",
        "Basic xxx",
        "Bearer invalid",
        "Bearer a b",
        "Bearer " + "x" * 4097,
        "Bearer rh_" + "a" * 43,
    ],
)
def test_only_valid_header_key_authorizes(owner, authorization):
    headers = {"Authorization": authorization} if authorization else {}
    for path in ("/api/repairs", "/api/repairs/1"):
        response = owner.get(path, headers=headers)
        assert response.status_code == 401 and response.is_json
        assert response.headers["WWW-Authenticate"].startswith("Bearer")
        assert "Location" not in response.headers
    key = create_key(owner)
    assert owner.get("/api/repairs?api_key=" + key).status_code == 401
    assert owner.get("/api/repairs", headers={"X-API-Key": key}).status_code == 401


def test_foreign_unknown_and_invalid_ids_are_hidden(owner, identity_app):
    rid = create(owner)
    other = identity_app.test_client()
    register(other, username="Other", email="other@example.org")
    other.get(confirmation(identity_app))
    submit(other, "/login", identity="Other", password=PASSWORD)
    headers = bearer(create_key(other))
    responses = [
        other.get(f"/api/repairs/{i}?owner_id=1&username=Lea", headers=headers)
        for i in (rid, 99999, 0, 2**63)
    ]
    assert all(r.status_code == 404 for r in responses)
    assert all(r.json == responses[0].json for r in responses)
    assert other.get("/api/repairs?username=Lea&owner_id=1", headers=headers).json["items"] == []


def test_pagination_and_snapshot_reuse_web_domain(owner):
    ids = [create(owner) for _ in range(4)]
    headers = bearer(create_key(owner))
    response = owner.get("/api/repairs?limit=2", headers=headers).json
    assert [item["id"] for item in response["items"]] == ids[-1:-3:-1]
    assert response["total"] == 4 and response["next_offset"] == 2
    create(owner)
    second = owner.get(
        f"/api/repairs?limit=2&offset=2&snapshot={response['snapshot']}", headers=headers
    ).json
    assert [item["id"] for item in second["items"]] == ids[1::-1]
    assert second["total"] == 4 and second["next_offset"] is None
    assert owner.get("/api/repairs", headers=headers).json["total"] == 5


@pytest.mark.parametrize(
    "query",
    [
        "limit=0",
        "limit=61",
        "limit=-1",
        "offset=-1",
        "offset=abc",
        "snapshot=1.2",
        "limit=2&limit=3",
        "offset=" + "9" * 20,
    ],
)
def test_invalid_windows(owner, query):
    assert owner.get("/api/repairs?" + query, headers=bearer(create_key(owner))).status_code == 400


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_readonly_api_and_retired_token_route(owner, method):
    rid = create(owner)
    headers = bearer(create_key(owner))
    before = owner.get(f"/api/repairs/{rid}", headers=headers).json
    for path in ("/api/repairs", f"/api/repairs/{rid}"):
        response = owner.open(path, method=method, headers=headers, json={"description": "changed"})
        assert response.status_code == 405 and response.is_json
        assert "GET" in response.headers["Allow"]
        assert owner.head(path, headers=headers).status_code == 200
        assert owner.options(path).status_code == 200
    assert owner.get(f"/api/repairs/{rid}", headers=headers).json == before
    assert owner.post("/api/auth/token", json={}).status_code == 404


SYSTEM_KEY = "rh_" + "s" * 43


@pytest.fixture(autouse=True)
def system_key_configuration(app_config):
    app_config["API_SMOKE_KEY"] = SYSTEM_KEY


def test_system_key_reads_all_owners_without_session(owner, identity_app):
    first = create(owner)
    other = identity_app.test_client()
    register(other, username="Other", email="other@example.org")
    other.get(confirmation(identity_app))
    submit(other, "/login", identity="Other", password=PASSWORD)
    second = create(other)
    personal = create_key(owner)
    client = identity_app.test_client()
    headers = bearer(SYSTEM_KEY)
    page = client.get("/api/repairs?limit=1", headers=headers)
    assert page.status_code == 200
    assert page.json["total"] == 2 and page.json["next_offset"] == 1
    assert page.json["items"][0]["id"] == second
    following = client.get(
        f"/api/repairs?limit=1&offset=1&snapshot={page.json['snapshot']}", headers=headers
    ).json
    assert following["items"][0]["id"] == first
    for rid in (first, second):
        response = client.get(f"/api/repairs/{rid}", headers=headers)
        assert response.status_code == 200
        assert response.json["costs"]["currency"] == "CHF"
        assert response.headers["Cache-Control"] == "no-store"
        for method in ("POST", "PATCH", "PUT", "DELETE"):
            assert (
                client.open(f"/api/repairs/{rid}", method=method, headers=headers).status_code
                == 405
            )
    assert client.get("/api/repairs/999999", headers=headers).status_code == 404
    assert client.get("/api/repairs", headers=bearer(personal)).json["total"] == 1
    assert client.get(f"/api/repairs/{second}", headers=bearer(personal)).status_code == 404
    assert client.get("/devices", headers=headers).status_code == 302
    assert SYSTEM_KEY not in owner.get("/account/api-key").text


def test_system_key_accepts_empty_database_and_rejects_wrong_key(identity_app):
    client = identity_app.test_client()
    response = client.get("/api/repairs", headers=bearer(SYSTEM_KEY))
    assert response.status_code == 200 and response.json["items"] == []
    assert client.get("/api/repairs", headers=bearer("rh_" + "z" * 43)).status_code == 401


def test_system_key_disabled_and_rotation():
    from unittest.mock import Mock

    from app.adapters.users.api_keys import ApiKeys
    from app.domains.users.authenticate_api_key.dto import Command
    from app.domains.users.dto import SystemApiIdentity

    store = Mock()
    store.find_user.return_value = None
    assert ApiKeys(store).authenticate(Command(SYSTEM_KEY)) is None
    assert isinstance(
        ApiKeys(store, SYSTEM_KEY).authenticate(Command(SYSTEM_KEY)), SystemApiIdentity
    )
    assert ApiKeys(store, "rh_" + "z" * 43).authenticate(Command(SYSTEM_KEY)) is None
    with pytest.raises(ValueError, match="API_SMOKE_KEY"):
        ApiKeys(store, "short")
