"""Interner HTTP-Bereitschaftstest mit der öffentlichen Hostidentität."""

import os
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, Request, build_opener


def check() -> None:
    # Die Verbindung bleibt lokal, der Host-Header muss aber Flasks TRUSTED_HOSTS
    # entsprechen. PUBLIC_URL darf den Test nicht auf den öffentlichen Server umleiten.
    host = urlsplit(os.environ.get("PUBLIC_URL", "")).netloc or "127.0.0.1:8000"
    request = Request("http://127.0.0.1:8000/health/ready", headers={"Host": host})
    # Auch bei gesetztem HTTP_PROXY ausschliesslich den eigenen Container prüfen.
    with build_opener(ProxyHandler({})).open(request, timeout=4) as response:
        if response.status != 200:
            raise RuntimeError("Readiness check failed.")


if __name__ == "__main__":
    try:
        check()
    except (OSError, URLError, ValueError, RuntimeError):
        # Docker speichert die Ausgabe im Health-Status; keine Konfigurationswerte ausgeben.
        raise SystemExit("Readiness check failed.") from None
