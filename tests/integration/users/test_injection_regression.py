"""ZAP-40018-Eingaben gegen PostgreSQL wiederholen, ohne Scannerregeln abzuschwächen."""

import re
from html import escape

import pytest
from sqlalchemy import event, func, select

from app.data.users.model import User
from app.extensions import db

from .test_registration import outbox, register, submit


@pytest.mark.parametrize(
    "path,parameter,original",
    [
        ("/confirm", "email", "zaproxy@example.com"),
        ("/confirm", "submit", "Resend Confirmation Instructions"),
        ("/confirm", "query", "query"),
        ("/login", "identity", "ZAP"),
        ("/login", "password", "ZAP"),
        ("/reset", "email", "zaproxy@example.com"),
        ("/reset", "submit", "Recover Password"),
        ("/reset", "query", "query"),
    ],
)
def test_boolean_scan_payloads_cannot_change_queries_or_expose_accounts(
    identity_app, path, parameter, original
):
    client = identity_app.test_client()
    register(client)
    with identity_app.app_context():
        engine = db.engine
    statements = []

    def record(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    bodies = []
    try:
        for condition in [" AND 1=1 -- ", " AND 1=2 -- ", " OR 1=1 -- "]:
            attack = original + condition
            values = {
                "email": "zaproxy@example.com",
                "identity": "ZAP",
                "password": "ZAP",
                parameter: attack,
            }
            response = submit(client, path, **values)
            assert response.status_code == 200
            assert all(attack not in statement for statement in statements)
            assert "lea@example.org" not in response.text
            with client.session_transaction() as session:
                assert "_user_id" not in session
            # Sichtbare Ausgabe vergleichen; nur zurückgespiegelte Eingaben und das
            # zeitabhängige signierte CSRF-Token entfernen. CSRF bleibt aktiviert.
            normalized = response.text.replace(escape(attack, quote=True), "INPUT")
            normalized = re.sub(r'(name="csrf_token"[^>]*value=")[^"]+', r"\1TOKEN", normalized)
            bodies.append(normalized)
        assert len(set(bodies)) == 1
        assert len(outbox(identity_app)) == 1
        with identity_app.app_context():
            assert db.session.scalar(select(func.count()).select_from(User)) == 1
    finally:
        event.remove(engine, "before_cursor_execute", record)
