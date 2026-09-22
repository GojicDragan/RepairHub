"""PostgreSQL und echte HTTP-Anwendungsfälle für Teile, Arbeit und Kosten."""

import re
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DataError, IntegrityError

from app.data.parts.model import PartItem
from app.data.repairs.model import Repair
from app.extensions import db
from tests.integration.devices.test_devices import owner as owner
from tests.integration.repairs.test_repairs import create, post
from tests.integration.users.test_registration import PASSWORD, confirmation, register, submit


def part(client, rid, **values):
    return post(
        client,
        f"/repairs/{rid}/parts",
        **{"name": "Cable", "unit_price": "15", "quantity": "3", **values},
    )


def test_costs_persist_and_ignore_client_total(owner, identity_app):
    rid = create(owner)
    response = post(owner, f"/repairs/{rid}/work", hours="2", hourly_rate="80", total_cost="0.01")
    assert response.status_code == 200
    assert "CHF 160.00" in response.json["html"]
    response = part(owner, rid)
    assert response.status_code == 200, response.text
    assert "CHF 205.00" in response.json["html"]
    pid = int(re.search(r'data-part-id="(\d+)"', response.json["html"])[1])
    response = post(
        owner,
        f"/repairs/{rid}/parts/{pid}",
        name="New cable",
        unit_price="0.10",
        quantity="3",
        repair_id=999,
        total="10000",
    )
    assert "CHF 160.30" in response.json["html"]
    assert "CHF 160.30" in owner.get(f"/repairs/{rid}").text
    with identity_app.app_context():
        row = db.session.get(PartItem, pid)
        assert row.repair_id == rid and row.unit_price == Decimal("0.10") and row.quantity == 3
        assert db.session.get(Repair, rid).hours == Decimal("2.00")


@pytest.mark.parametrize(
    "field,value",
    [
        ("unit_price", "NaN"),
        ("unit_price", "Infinity"),
        ("unit_price", "-1"),
        ("unit_price", "1000000000"),
        ("unit_price", "0.001"),
        ("unit_price", 0.1),
        ("quantity", 0),
        ("quantity", "1.5"),
        ("quantity", "2147483648"),
        ("name", ""),
    ],
)
def test_invalid_part_not_persisted(owner, identity_app, field, value):
    rid = create(owner)
    assert part(owner, rid, **{field: value}).status_code == 422
    with identity_app.app_context():
        assert db.session.query(PartItem).count() == 0


def test_foreign_and_cross_case_parts_are_hidden(owner, identity_app):
    rid = create(owner)
    pid = int(re.search(r'data-part-id="(\d+)"', part(owner, rid).json["html"])[1])
    second = create(owner)
    assert (
        post(
            owner, f"/repairs/{second}/parts/{pid}", name="x", unit_price="1", quantity="1"
        ).status_code
        == 404
    )
    other = identity_app.test_client()
    register(other, username="Other", email="other@example.org")
    other.get(confirmation(identity_app))
    submit(other, "/login", identity="Other", password=PASSWORD)
    for target in (rid, 999999):
        assert part(other, target).status_code == 404
        assert post(other, f"/repairs/{target}/work", hours="1", hourly_rate="1").status_code == 404
        assert (
            post(
                other, f"/repairs/{target}/parts/{pid}", name="x", unit_price="1", quantity="1"
            ).status_code
            == 404
        )


def test_all_parts_count_even_when_page_is_bounded(owner, identity_app):
    rid = create(owner)
    with identity_app.app_context():
        db.session.add_all(
            [
                PartItem(repair_id=rid, name=f"Part {i}", unit_price=Decimal("0.10"), quantity=3)
                for i in range(25)
            ]
        )
        db.session.commit()
    html = owner.get(f"/repairs/{rid}").text
    assert html.count("data-part-id=") == 20 and "CHF 7.50" in html
    html = owner.get(f"/repairs/{rid}?part_offset=20").text
    assert html.count("data-part-id=") == 5 and "CHF 7.50" in html


@pytest.mark.parametrize("assignment", ["hours = -1", "hourly_rate = 'NaN'", "hours = 'Infinity'"])
def test_database_rejects_invalid_work(owner, identity_app, assignment):
    rid = create(owner)
    with identity_app.app_context():
        with pytest.raises((IntegrityError, DataError)):
            db.session.execute(text(f"UPDATE repairs SET {assignment} WHERE id = :id"), {"id": rid})
            db.session.commit()
        db.session.rollback()
        assert db.session.get(Repair, rid).hours == 0


def test_part_csrf_and_html_fallback(owner):
    from tests.integration.devices.test_devices import csrf

    rid = create(owner)
    assert owner.post(f"/repairs/{rid}/parts", json={"name": "X"}).status_code == 400
    response = owner.post(
        f"/repairs/{rid}/parts",
        data={"name": "Cable", "unit_price": "15", "quantity": "3", "csrf_token": csrf(owner)},
        headers={"Referer": "https://localhost/"},
    )
    assert response.status_code == 303
    assert "CHF 45.00" in owner.get(response.location).text


@pytest.mark.parametrize("identity_app", ["0003_repairs"], indirect=True)
def test_upgrade_preserves_existing_repairs(identity_app):
    from flask_migrate import check, upgrade
    from sqlalchemy import select

    from app.data.devices.model import Device
    from app.data.users.model import User

    with identity_app.app_context():
        from tests.support.legacy_user import seed_user

        user_id = seed_user("Migration")
        device = Device(owner_id=user_id, name="Radio", manufacturer="Maker", model="One")
        db.session.add(device)
        db.session.flush()
        rid = db.session.scalar(
            text(
                "INSERT INTO repairs(device_id,description) "
                "VALUES (:device,'Preserved fault') RETURNING id"
            ),
            {"device": device.id},
        )
        db.session.commit()
        upgrade()
        upgrade()
        check()
        row = db.session.get(Repair, rid)
        assert row.description == "Preserved fault" and row.hours == 0 and row.hourly_rate == 0
        assert db.session.scalar(select(User.username)) == "Migration"


def test_failed_part_commit_rolls_back_all_fields(owner, identity_app):
    from unittest.mock import patch

    rid = create(owner)
    pid = int(re.search(r'data-part-id="(\d+)"', part(owner, rid).json["html"])[1])
    with patch.object(db.session, "commit", side_effect=RuntimeError("synthetic commit failure")):
        response = post(
            owner, f"/repairs/{rid}/parts/{pid}", name="Changed", unit_price="8", quantity="7"
        )
    assert response.status_code == 500
    assert "synthetic commit failure" not in response.text
    with identity_app.app_context():
        row = db.session.get(PartItem, pid)
        assert (row.name, row.unit_price, row.quantity) == ("Cable", Decimal("15.00"), 3)


def test_invalid_work_keeps_both_saved_values(owner, identity_app):
    rid = create(owner)
    assert post(owner, f"/repairs/{rid}/work", hours="2", hourly_rate="80").status_code == 200
    assert post(owner, f"/repairs/{rid}/work", hours="3", hourly_rate="NaN").status_code == 422
    with identity_app.app_context():
        row = db.session.get(Repair, rid)
        assert (row.hours, row.hourly_rate) == (Decimal("2"), Decimal("80"))


@pytest.mark.parametrize(
    "values",
    [
        {"quantity": 0},
        {"unit_price": Decimal("NaN")},
        {"repair_id": 999999},
        {"name": " "},
    ],
)
def test_database_guards_parts(owner, identity_app, values):
    rid = create(owner)
    with identity_app.app_context():
        row = PartItem(
            **{
                "repair_id": rid,
                "name": "Cable",
                "unit_price": Decimal("15"),
                "quantity": 3,
                **values,
            }
        )
        db.session.add(row)
        with pytest.raises((IntegrityError, DataError)):
            db.session.commit()
        db.session.rollback()
        assert db.session.query(PartItem).count() == 0
