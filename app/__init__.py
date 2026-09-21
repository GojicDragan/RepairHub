"""Paketwurzel ohne Framework-Import; Verdrahtung erst beim Anwendungsstart."""


def create_app(config=None):
    """Öffentlicher Flask-Einstieg; Domain-Imports laden keine Infrastruktur."""
    # Python lädt diese Paketwurzel auch bei `import app.domains.repairs`.
    # Der lokale Import verhindert, dass dabei Flask und ORM mitgeladen werden.
    from app.bootstrap import create_app as build_app

    return build_app(config)
