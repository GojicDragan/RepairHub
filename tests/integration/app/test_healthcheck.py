"""Interne Prüfungen müssen trotz produktiver Hostbeschränkung funktionieren."""

import pytest

from app import create_app
from scripts.healthcheck import check


@pytest.mark.parametrize("public_url", ["https://lab19.ifalabs.org", "https://example.org:9443"])
def test_internal_check_uses_public_host_without_public_connection(
    app_config, monkeypatch, public_url
):
    from urllib.parse import urlsplit

    host = urlsplit(public_url).netloc
    app = create_app(
        {**app_config, "SERVER_NAME": host, "TRUSTED_HOSTS": [urlsplit(public_url).hostname]}
    )
    monkeypatch.setenv("PUBLIC_URL", public_url)
    monkeypatch.setattr("app.web.routes.health.check_readiness", lambda: True)
    client = app.test_client()
    assert client.get("/health/ready", headers={"Host": "127.0.0.1:8000"}).status_code == 400
    assert client.get("/health/ready", headers={"Host": "foreign.invalid"}).status_code == 400

    class Opener:
        def open(self, request, timeout):
            assert request.full_url == "http://127.0.0.1:8000/health/ready"
            assert request.get_header("Host") == host
            assert timeout == 4
            response = client.get("/health/ready", headers={"Host": request.get_header("Host")})
            assert response.status_code == 200
            return Response()

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr("scripts.healthcheck.build_opener", lambda handler: Opener())
    check()
