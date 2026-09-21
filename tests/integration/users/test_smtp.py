"""Echter SMTP-Versand an einen isolierten lokalen Empfänger ohne Internetzustellung."""

import asyncio
from email import policy
from email.parser import BytesParser
from threading import Thread

import pytest
from aiosmtpd.smtp import SMTP

from app import create_app
from app.extensions import db

from .test_registration import register


@pytest.mark.parametrize("language", ["en", "de-CH"])
def test_confirmation_message_is_sent_over_smtp(identity_app, language):
    messages = []

    class Receiver:
        async def handle_DATA(self, server, session, envelope):
            messages.append(BytesParser(policy=policy.default).parsebytes(envelope.content))
            return "250 OK"

    loop = asyncio.new_event_loop()
    server = loop.run_until_complete(loop.create_server(lambda: SMTP(Receiver()), "127.0.0.1", 0))
    thread = Thread(target=loop.run_forever, daemon=True)
    thread.start()
    application = create_app(
        {
            **identity_app.config,
            "MAIL_BACKEND": "smtp",
            "MAIL_SERVER": "127.0.0.1",
            "MAIL_PORT": server.sockets[0].getsockname()[1],
            "MAIL_USE_TLS": False,
            "MAIL_USE_SSL": False,
            "MAIL_DEFAULT_SENDER": "noreply@example.org",
            "SECURITY_EMAIL_SENDER": "noreply@example.org",
        }
    )
    try:
        client = application.test_client()
        client.environ_base["HTTP_ACCEPT_LANGUAGE"] = language
        assert register(client).status_code == 302
        assert len(messages) == 1
        assert messages[0]["To"] == "lea@example.org"
        plain = messages[0].get_body(preferencelist=("plain",)).get_content()
        html = messages[0].get_body(preferencelist=("html",)).get_content()
        assert "/confirm/" in plain
        welcome = "Willkommen bei RepairHub." if language == "de-CH" else "Welcome to RepairHub."
        motto = (
            "Gute Dinge verdienen ein zweites Leben."
            if language == "de-CH"
            else "Good things deserve a second life."
        )
        assert welcome in plain and welcome in html
        assert ("Willkommen" if language == "de-CH" else "Welcome") in str(messages[0]["Subject"])
        assert "#b84020" in html and 'role="presentation"' in html
        assert motto in plain
        assert motto in html
        assert "<script" not in html and "<link" not in html
    finally:
        with application.app_context():
            db.session.remove()
            db.engine.dispose()
        loop.call_soon_threadsafe(server.close)
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=10)
        loop.run_until_complete(server.wait_closed())
        loop.close()
