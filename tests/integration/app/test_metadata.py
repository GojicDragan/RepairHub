"""Suchmetadaten bleiben übersetzt und enthalten keine privaten URLs oder Identitäten."""

from html.parser import HTMLParser
from types import SimpleNamespace

import pytest


class Head(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.meta = {}
        self.links = {}
        self.feed(html.split("</head>")[0])

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            self.meta[attrs.get("name", attrs.get("property"))] = attrs.get("content")
        if tag == "link":
            self.links.setdefault(attrs["rel"], []).append(attrs)


@pytest.mark.parametrize(
    ("language", "title", "locale"),
    [
        ("en", "Your personal repair workshop", "en_US"),
        ("de-CH", "Deine persönliche Reparaturwerkstatt", "de_DE"),
    ],
)
def test_public_metadata_uses_configured_origin_without_query(app, language, title, locale):
    app.config.update(
        SERVER_NAME="repairhub.example",
        PREFERRED_URL_SCHEME="https",
        REPAIRHUB_ENV="production",
    )
    response = app.test_client().get("/?token=private-value", headers={"Accept-Language": language})
    head = Head(response.get_data(as_text=True))
    assert head.meta["robots"] == "index, follow"
    assert head.meta["og:title"] == f"{title} | RepairHub"
    assert head.meta["twitter:title"] == head.meta["og:title"]
    assert head.meta["og:locale"] == locale
    assert head.meta["description"] == head.meta["og:description"]
    assert head.links["canonical"][0]["href"] == "https://repairhub.example/"
    assert head.meta["og:url"] == "https://repairhub.example/"
    assert head.meta["og:image"] == "https://repairhub.example/static/brand-mark-512.png"
    assert "private-value" not in str(head.meta)


@pytest.mark.parametrize(
    "path", ["/login", "/register", "/confirm", "/reset", "/missing/private-token"]
)
def test_account_and_error_pages_are_not_search_content(client, path):
    head = Head(client.get(path).get_data(as_text=True))
    assert head.meta["robots"] == "noindex, nofollow"
    assert head.meta["description"]
    assert "canonical" not in head.links
    assert "og:url" not in head.meta


def test_signed_in_home_does_not_expose_identity_in_metadata(app, monkeypatch):
    monkeypatch.setattr(
        app.extensions["identity_provider"],
        "current",
        lambda: SimpleNamespace(username="private-user"),
    )
    head = Head(app.test_client().get("/").get_data(as_text=True))
    assert head.meta["robots"] == "noindex, nofollow"
    assert "og:url" not in head.meta
    assert "private-user" not in str(head.meta)


def test_development_is_not_indexed_and_icons_are_available(client):
    head = Head(client.get("/").get_data(as_text=True))
    assert head.meta["robots"] == "noindex, nofollow"
    for icon in head.links["icon"] + head.links["apple-touch-icon"]:
        response = client.get(icon["href"])
        assert response.status_code == 200
        assert response.mimetype in {"image/png", "image/svg+xml"}
