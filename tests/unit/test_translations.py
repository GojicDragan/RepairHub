"""Jede extrahierte Anwendungsmeldung besitzt eine aktuelle kompilierte deutsche Übersetzung."""

from pathlib import Path

from babel.messages.extract import extract_from_dir
from babel.messages.mofile import read_mo
from babel.messages.pofile import read_po

ROOT = Path(__file__).resolve().parents[2]


def test_german_catalog_covers_source_and_matches_compiled_catalog():
    directory = ROOT / "app" / "translations" / "de_DE" / "LC_MESSAGES"
    with (directory / "messages.po").open() as stream:
        source = read_po(stream)
    with (directory / "messages.mo").open("rb") as stream:
        compiled = read_mo(stream)
    messages = {
        message
        for _, _, message, _, _ in extract_from_dir(
            ROOT / "app",
            method_map=[
                ("**.py", "python"),
                ("web/templates/**.html", "jinja2"),
                ("web/templates/**.txt", "jinja2"),
            ],
        )
    }
    assert messages
    for message in messages:
        assert message in source, f"Missing German translation: {message}"
        assert source[message].string and not source[message].fuzzy
        assert compiled[message].string == source[message].string
