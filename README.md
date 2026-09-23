# RepairHub

RepairHub verwaltet eigene Geräte und Reparaturfälle mit Schritten, Ersatzteilen
und Kostenschätzung in CHF. Enthalten sind Registrierung mit E-Mail-Bestätigung,
Passwort-Recovery, Suche, Statusübersicht, private Bilder, PDF-Berichte und eine
lesende API mit persönlichen Schlüsseln. Die Oberfläche unterstützt Deutsch und
Englisch anhand der Browsersprache.

Anwendung: <https://lab19.ifalabs.org>

Der modulare Flask-Monolith läuft mit Nginx, PostgreSQL und Garage unter Docker
Compose. GitHub Actions führt Test → Build → Security → Publish → Deploy aus;
Publish und Deploy laufen nur für veröffentlichte Releases.

## Lokal starten

Voraussetzungen: Docker mit Compose ab 2.30.0 sowie uv 0.12.16. Python 3.13.15
und die Abhängigkeiten sind in `.python-version`, `pyproject.toml` und `uv.lock`
festgelegt. Für uv gilt die
[offizielle Installationsanleitung](https://docs.astral.sh/uv/getting-started/installation/).

```bash
uv python install 3.13.15
uv sync --locked --group ci
cp .env.example .env
```

In `.env` die lokalen Werte setzen; die offiziellen Infrastruktur-Pins sind
bereits in `.env.example` hinterlegt:

```dotenv
REPAIRHUB_APP_IMAGE=repairhub-app:development
REPAIRHUB_NGINX_IMAGE=nginx:1.30.5-alpine@sha256:a5f2157a0302eb0c5e300415effb63a9e70ed1eb9c107283819bf6d149ab607c
REPAIRHUB_POSTGRES_IMAGE=postgres:17.11-alpine3.24@sha256:f02121de6f74d30d8a94cd1d9584125e2178d7e6c377d8130112d4e52d867995
POSTGRES_DB=repairhub
POSTGRES_USER=repairhub
```

Einmalig lokale Zufallsgeheimnisse in einer neuen, geschützten `runtime.env` erzeugen:

```bash
uv run --locked python - <<'PY'
import os
import secrets

password = secrets.token_urlsafe(32)
content = (
    f"SECRET_KEY={secrets.token_hex(32)}\nPOSTGRES_PASSWORD={password}\n"
    f"DATABASE_URL=postgresql+psycopg://repairhub:{password}@db:5432/repairhub\n"
)
fd = os.open("runtime.env", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w") as stream:
    stream.write(content)
PY

uv run --locked python scripts/setup_storage.py
docker compose -f compose.yaml -f compose.development.yaml build app
docker compose -f compose.yaml -f compose.development.yaml up -d --wait db mailpit garage
docker compose -f compose.yaml -f compose.development.yaml run --rm --no-deps app flask --app app db upgrade
docker compose -f compose.yaml -f compose.development.yaml up -d --wait
curl --fail http://127.0.0.1:8080/health/ready
```

Die Anwendung ist unter `http://127.0.0.1:8080` erreichbar. Entwicklung verwendet
lokales HTTP, Quellcode-Mounts und Reload. Mailpit fängt alle Entwicklungs-E-Mails
ab; die Nachrichten sind unter `http://127.0.0.1:8025` sichtbar. Es gibt keinen
externen Mailversand aus Development. Produktion verwendet verschlüsseltes SMTP.

Zum Beenden denselben Compose-Aufruf mit `down` verwenden. Benannte Volumes bleiben
erhalten. Volumes ersetzen keine Backups; bestehende Volumes nicht mit neuen
Zugangsdaten oder einer anderen Datenbankbasis wiederverwenden.
Migrationen explizit ausführen, niemals pro Gunicorn-Worker.

## Prüfen und weiterentwickeln

```bash
uv lock --check
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked python scripts/check_architecture.py
uv run --locked pytest tests/unit
uv run --locked pytest tests/integration
```

Für die PostgreSQL-Integration muss `TEST_DATABASE_URL` auf eine getrennte
Testdatenbank zeigen. Ohne diese Angabe werden die datenbankabhängigen Tests lokal
sichtbar übersprungen; datenbankfreie Integrationsprüfungen können trotzdem laufen.
Ein solcher Lauf ersetzt keine vollständige PostgreSQL-Abnahme. In CI ist eine
fehlende Testdatenbank ein Fehler.
Vollständige CI-Werkzeuge werden mit `uv sync --locked --group ci` installiert.

End-to-End-Tests verwenden einen echten Chromium-Browser gegen die gebauten
App-Images mit den festgelegten Nginx-/PostgreSQL-/Garage-Infrastrukturimages:

```bash
uv sync --locked --group e2e
uv run --locked --group e2e playwright install --with-deps --only-shell chromium
uv run --locked python scripts/ci/images.py build --commit "$(git rev-parse HEAD)"
uv run --locked --group e2e pytest tests/e2e
```

## Architektur

- `app.domains`: frameworkfreie vertikale Anwendungsfälle mit eigenen Ports und DTOs.
  Keine Imports zwischen Slices; nur Reparaturen und Teile verwenden die reine
  Kostenberechnung unter `app.domains.costs`.
- `app.data`: persistente Modelle und Adapter für PostgreSQL und privaten Bildspeicher.
- `app.adapters.users`: technische Integration von Flask-Security und API-Keys.
- `app.bootstrap`: Application Factory und explizite Verdrahtung der Adapter.
- `app.web` und `app.api`: HTTP, Formulare, Vorlagen und JSON; kein direkter ORM-Zugriff.

Das Frontend verwendet lokales Bootstrap, kleine DOM-Adapter und separat testbare
Presenter. Fachlogik bleibt in Python. Übersetzungen verwenden gettext unter
`app/translations`; Englisch ist der Fallback, URLs bleiben sprachunabhängig.
Die Grenzen werden von `scripts/check_architecture.py` und den Architekturtests geprüft.

## Bedienung und API

Nach Registrierung unter `/register` muss die E-Mail bestätigt werden. `/confirm`
fordert einen neuen Bestätigungslink an; `/reset` startet die Passwortwiederherstellung.
Benutzername und E-Mail sind eindeutig. Passwörter haben 8–128 Zeichen.

Unter `/devices` eigene Geräte erfassen und bearbeiten. Ein Gerät benötigt Name,
Hersteller und Modell. Reparaturfälle unter `/repairs` enthalten Fehlerbeschreibung,
Status, Schritte, Ersatzteile und Arbeitswerte. Zustände sind offen, in Bearbeitung
und abgeschlossen; Wiederaufnahme ist möglich. Bilder werden an Geräten und Fällen
hochgeladen. `/repairs/{id}/report.pdf` liefert den vollständigen PDF-Bericht.

Kosten werden serverseitig mit Decimal berechnet:
`Arbeitszeit × Stundensatz + Summe(Menge × Einzelpreis)`, in CHF und mit
`ROUND_HALF_UP` auf zwei Nachkommastellen. Jeder Zugriff prüft Eigentümerschaft.

Persönliche API-Keys unter `/account/api-key` erzeugen, ersetzen oder widerrufen.
Klartext wird einmal angezeigt; nur der Hash wird gespeichert.

```http
Authorization: Bearer <api-key>
GET /api/repairs?limit=20&offset=0
GET /api/repairs/{id}
```

Die API ist lesend. Dezimalwerte werden als Strings ausgegeben. Fehlende oder
ungültige Keys ergeben 401, fremde und unbekannte Fälle 404, Schreibmethoden 405.
Der technische `API_SMOKE_KEY` ermöglicht ausdrücklich einen systemweiten Lesezugriff
für Deployment-Prüfungen; persönliche Keys bleiben an den Benutzer gebunden.

## Auslieferung und Betrieb

Die Pipeline steht in [.github/workflows/ci-cd.yml](.github/workflows/ci-cd.yml).
Tests und Scans laufen auf Branches und Pull Requests. Veröffentlichte Releases
müssen auf den aktuellen `main`-Commit zeigen und liefern über die GitHub-Environment
`production` aus. Das App-Image wird einmal gebaut, geprüft, veröffentlicht und
über seinen Digest bereitgestellt. Infrastruktur-Pins stehen in
[deploy/infrastructure.json](deploy/infrastructure.json).

Ansible-Playbooks unter `deploy/ansible` übernehmen Hostvorbereitung (`bootstrap.yml`),
Auslieferung (`deploy.yml`) und kompatiblen Rollback (`rollback.yml`).
Host-/Umgebungswerte kommen aus Inventory und GitHub-Variables, Zugangsdaten aus
Environment-Secrets. Die konkreten Namen und Prüfungen stehen im Workflow,
in den Inventories und den Rollendefaults. Keine Geheimnisse einchecken.

Der Zielhost verwendet Debian 12, Docker und Compose v2. Nur Nginx veröffentlicht
Anwendungsports. Ansible richtet TLS über Let’s Encrypt ein; `ACME_EMAIL` und Port 80
für HTTP-01 sind erforderlich. Ein Timer übernimmt Zertifikatserneuerungen.
Release-Deployments gleichen Infrastruktur idempotent ab, sichern den vorherigen
Stand, führen Migrationen einmalig im neuen App-Image aus und prüfen HTTPS sowie API.
Kein automatisches Datenbank-Downgrade; Wiederherstellung muss zum Schema passen.

Lokale Ansible-Abnahme: [tests/deployment/README.md](tests/deployment/README.md).
Scanner-Ausnahmen bleiben einzeln in `deploy/security` versioniert.
Geheimnisse, lokale Umgebungen, QA-Artefakte und Berichte sind von Git ausgeschlossen.
