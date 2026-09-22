"""Nur im wegwerfbaren CI-/Deployment-Testcontainer ausführen, nie in Produktion."""

import json
import secrets
import ssl
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from decimal import Decimal

from flask_security import hash_password

from app import create_app
from app.adapters.users.api_keys import ApiKeys
from app.data.devices.model import Device
from app.data.parts.model import PartItem
from app.data.repairs.model import Repair, RepairStep
from app.domains.users.create_api_key.dto import Command
from app.extensions import db


def seed():
    username = "api-check-" + secrets.token_hex(8)
    password = secrets.token_urlsafe(32)
    application = create_app()
    with application.app_context():
        store = application.extensions["security"].datastore
        user = store.create_user(
            username=username,
            email=username + "@example.org",
            password=hash_password(password),
            confirmed_at=datetime.now(UTC),
        )
        db.session.flush()
        device = Device(owner_id=user.id, name="CI radio", manufacturer="CI", model="Test")
        db.session.add(device)
        db.session.flush()
        repair = Repair(
            device_id=device.id,
            description="CI repair",
            status="open",
            created_at=datetime.now(UTC),
            hours=Decimal("2"),
            hourly_rate=Decimal("80"),
        )
        db.session.add(repair)
        db.session.flush()
        db.session.add(
            PartItem(repair_id=repair.id, name="Cable", unit_price=Decimal("15"), quantity=3)
        )
        db.session.add(RepairStep(repair_id=repair.id, description="Check cable", completed=True))
        store.commit()
        key = ApiKeys(store).create(Command(user.id)).value
        return {"username": username, "key": key, "repair_id": repair.id}


def smoke(credentials):
    context = ssl.create_default_context(cafile="/tmp/smoke-ca.crt")
    origin = "https://nginx:8443"

    def request(path, *, data=None, token=None, method=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        req = urllib.request.Request(
            origin + path,
            data=json.dumps(data).encode() if data else None,
            headers=headers,
            method=method,
        )
        try:
            response = urllib.request.urlopen(req, context=context, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response), response.headers

    path = "/api/repairs/" + str(credentials["repair_id"])
    status, detail, headers = request(path, token=credentials["key"])
    assert status == 200 and detail["costs"]["total"] == "205.00"
    assert headers["Cache-Control"] == "no-store" and not headers.get("Set-Cookie")
    status, listing, _ = request("/api/repairs?limit=1", token=credentials["key"])
    assert status == 200 and listing["items"][0]["id"] == credentials["repair_id"]
    assert detail["work"]["hours"] == "2.00" and detail["steps"][0]["completed"] is True
    assert detail["parts"][0]["total"] == "45.00"
    assert request(path)[0] == 401
    assert request(path, token=credentials["key"] + "invalid")[0] == 401
    assert request("/api/repairs/9223372036854775807", token=credentials["key"])[0] == 404
    assert request(path, method="DELETE", token=credentials["key"])[0] == 405


if __name__ == "__main__":
    credentials = seed()
    if len(sys.argv) == 2 and sys.argv[1] == "seed-only":
        # Ausschliesslich vom lokalen Fixture-Controller in eine 0600-Datei übernehmen.
        print(json.dumps(credentials))
    else:
        smoke(credentials)
        print("API über HTTPS: API-Key, Falldaten, Kosten und negative Zugriffe geprüft.")
