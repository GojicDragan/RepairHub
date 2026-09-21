"""Wegwerfbarer STARTTLS-Empfänger; keine Weiterleitung an externe Empfänger."""

import asyncio
import ssl
import uuid
from pathlib import Path

from aiosmtpd.smtp import SMTP


class Inbox:
    async def handle_DATA(self, server, session, envelope):
        Path("/outbox", uuid.uuid4().hex + ".eml").write_bytes(envelope.content)
        return "250 OK"


async def main():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain("/tls/server.crt", "/tls/server.key")
    loop = asyncio.get_running_loop()
    server = await loop.create_server(
        lambda: SMTP(Inbox(), tls_context=context, require_starttls=True), "0.0.0.0", 1025
    )
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
