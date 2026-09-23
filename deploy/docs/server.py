"""Lokale Markdown-Vorschau; nur explizit eingehängte Dokumentation ausliefern."""

import re
from html import escape
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt

ROOT = Path("/content")


def render(source):
    # Tabellen aktivieren, eingebettetes HTML nicht ausführen. Keine CDN-Abhängigkeit.
    # Parser-Vertrag: https://markdown-it-py.readthedocs.io/en/latest/using.html
    parser = MarkdownIt("commonmark", {"html": False}).enable("table")
    tokens = parser.parse(source)
    counts = {}
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            # GitHub-artige Anker erhalten die Sprunglinks der Markdown-Anleitung.
            title = tokens[index + 1].content
            slug = re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")
            count = counts.get(slug, 0)
            counts[slug] = count + 1
            token.attrSet("id", f"{slug}-{count}" if count else slug)
    body = parser.renderer.render(tokens, parser.options, {})
    return (
        '<!doctype html><html lang="de"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>RepairHub · Dokumentation</title><link rel="stylesheet" href="/style.css">'
        '<header><a href="/docs/user-guide/">RepairHub · Benutzeranleitung</a>'
        "<span>Lokale Vorschau</span></header><main>" + body + "</main></html>"
    ).encode()


class Viewer(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def send_head(self):
        url = urlsplit(self.path)
        if url.path == "/":
            self.send_response(302)
            self.send_header("Location", "/docs/user-guide/")
            self.end_headers()
            return None
        if url.path == "/style.css":
            return self.content(Path("style.css").read_bytes(), "text/css; charset=utf-8")
        target = (ROOT / unquote(url.path).lstrip("/")).resolve()
        # Auch Symlinks dürfen die ausschliesslich lesbare Dokumentationswurzel nicht verlassen.
        if not target.is_relative_to(ROOT):
            self.send_error(404)
            return None
        if target.is_dir():
            if not url.path.endswith("/"):
                self.send_response(302)
                self.send_header("Location", url.path + "/")
                self.end_headers()
                return None
            target /= "README.md"
        if target.suffix == ".md" and target.is_file():
            return self.content(render(target.read_text()), "text/html; charset=utf-8")
        if not target.is_file():
            self.send_error(404, escape("Dokument nicht gefunden"))
            return None
        return super().send_head()

    def content(self, data, content_type):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        return BytesIO(data)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8000), Viewer).serve_forever()
