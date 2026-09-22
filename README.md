# RepairHub

RepairHub wird eine Webanwendung zur Verwaltung privater Reparaturfälle für
Haushaltsgeräte und Elektronik. Der aktuelle Stand enthält
Flask mit PostgreSQL-Bereitschaftsprüfung, Docker Compose und eine
Pipeline für Test → Build → Security → Deploy über GitHub Actions und Ansible.
Registrierung, E-Mail-Verifikation, Anmeldung und Passwort-Recovery verwenden
Flask-Security. T06 ergänzt eigene Geräte unter `/devices`: AJAX-Erfassung und
Bearbeitung, serverseitiger Listenstart und virtuelle AJAX-Liste. T07 ergänzt
Reparaturfälle, Fehlerbeschreibungen, Schritte und Statuswechsel mit Wiederaufnahme.
Details: [Reparaturverwaltung](docs/repairs.md) und [T07-Abnahme](docs/t07-validation.md).
T08 ergänzt Ersatzteilpositionen, Arbeitswerte und geschätzte Kosten in CHF.
Details: [Teile und Kosten](docs/parts-and-costs.md) und [T08-Abnahme](docs/t08-validation.md).
T09 ergänzt die lesende API mit persönlichen Schlüsseln aus dem Frontend und
dem zentralen System-Leseschlüssel `API_SMOKE_KEY`. Details: [API](docs/api.md).
Die Security-Stufe verwendet Open-Source-Scanner: Bandit für SAST, ZAP für aktive
DAST-Prüfungen in einer isolierten CI-Instanz sowie pip-audit, Gitleaks und Trivy
für Abhängigkeiten, Geheimnisse und Container.
Normale Releases bauen und veröffentlichen nur das App-Image. Ansible verwaltet
Nginx und PostgreSQL als offizielle, über Version und Digest festgelegte Images.
Ein eigener PostgreSQL-Build oder ein separates Datenbankpaket in GHCR entfällt.

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

docker compose -f compose.yaml -f compose.development.yaml build app
docker compose -f compose.yaml -f compose.development.yaml up -d --wait db mailpit
docker compose -f compose.yaml -f compose.development.yaml run --rm --no-deps app flask --app app db upgrade
docker compose -f compose.yaml -f compose.development.yaml up -d --wait
curl --fail http://127.0.0.1:8080/health/ready
```

Die Startseite ist unter `http://127.0.0.1:8080` erreichbar. Entwicklung verwendet
lokales HTTP, Quellcode-Mounts und Reload. Produktion verwendet HTTPS und
geprüfte Image-Digests; die konkreten Abläufe stehen in
[docs/ci-cd.md](docs/ci-cd.md). Es werden weder App- noch Datenbankports veröffentlicht.

Beenden mit demselben Compose-Aufruf und `down` anstelle von `up --build -d --wait`.
Das benannte PostgreSQL-Volume bleibt erhalten. Bestehende Volumes nicht mit
neuen Zugangsdaten oder einer anderen Datenbankbasis wiederverwenden, ohne den
entsprechenden Übernahmeweg zu prüfen. Volumes ersetzen keine Backups.

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
Testdatenbank zeigen. Ohne diese Angabe wird der entsprechende Test lokal
sichtbar übersprungen; in CI ist eine fehlende Testdatenbank ein Fehler.
Vollständige CI-Werkzeuge werden mit `uv sync --locked --group ci` installiert.

End-to-End-Tests verwenden einen echten Chromium-Browser gegen die gebauten
App-Images mit den festgelegten Nginx-/PostgreSQL-Infrastrukturimages:

```bash
uv sync --locked --group e2e
uv run --locked --group e2e playwright install --with-deps --only-shell chromium
uv run --locked python scripts/ci/images.py build --commit "$(git rev-parse HEAD)"
uv run --locked --group e2e pytest tests/e2e
```

Die offiziellen Nginx-/PostgreSQL-Pins stehen bereits in
`deploy/infrastructure.json`; ein vorheriger eigener Infrastruktur-Release ist
nicht erforderlich. Ansible richtet die Infrastruktur beim ersten Deployment
ein. Die begrenzte, vom Benutzer freigegebene Ausnahme für die bekannten
`gosu`-Befunde im PostgreSQL-Image ist in [docs/ci-cd.md](docs/ci-cd.md) dokumentiert.

Die drei Stufen lassen sich auch mit `-m unit`, `-m integration` und `-m e2e`
auswählen. Ein Aufruf ohne Auswahl sammelt alle Stufen und benötigt deren
Voraussetzungen. Einteilung, Berichte und Erweiterungsregeln stehen in
[docs/testing.md](docs/testing.md).

Die acht Paketgrenzen unter `app/` folgen dem Komponentenentwurf. Fachlogik gehört
in die zuständigen Services, Datenzugriff in `app.data`; `app.domains.costs`
bleibt eine reine Berechnungskomponente. Die technische Bereitschaftsprüfung
verwendet eine gekapselte Diagnoseschnittstelle.

- [Pipeline, Secrets-Namen, Branchregeln und Betrieb](docs/ci-cd.md)
- [ZAP-Formularprüfung, Browserabdeckung und DAST-Nachweis](docs/dast.md)
- [Tatsächliche T02-Prüfergebnisse und offene externe Abnahme](docs/t02-validation.md)
- [Isolierter lokaler Ansible-Testhost](tests/deployment/README.md)

Test, Build und Security laufen auf allen Branches und bei Pull Requests.
Nur veröffentlichte GitHub-Releases durchlaufen zusätzlich
Publish und Deploy in die GitHub-Environment `production`; Release-Tags müssen
auf den aktuellen `main`-Commit zeigen. Host und vorhandener SSH-Benutzer werden dort als **Variables**, SSH-Passwort,
Anwendungs-/DB-Geheimnisse als **Secrets** hinterlegt; die
[Einrichtungsliste](docs/ci-cd.md#github-einrichtung) nennt alle Werte.
Automatisierte Tests und ZAP verwenden kurzlebige isolierte Instanzen;
ein zusätzlicher Testserver oder eine Environment `test` ist nicht erforderlich.
Die vorhandenen Planungsunterlagen und ältere lokale Arbeitsnachweise bleiben
auf ausdrücklichen Benutzerwunsch ignoriert. Geheimnisse und lokale QA-Artefakte
gehören ebenfalls nicht in das Repository oder Quellcode-ZIP.

TLS für `lab19.ifalabs.org` stellt Ansible beim ersten Deployment über Let’s Encrypt
aus. Ein Host-Timer prüft danach die Erneuerung. Dafür `ACME_EMAIL` im GitHub-Environment
setzen und Port 80 für HTTP-01 freigeben; siehe [TLS-Einrichtung](docs/ci-cd.md#tls-automatisch-ausstellen-und-erneuern).

Das in T03 vervollständigte Grundgerüst verwendet eine gemeinsame englische
Seitenvorlage sowie getrennte HTML- und JSON-Fehlerantworten. Konfiguration,
Fehlervertrag, Komponentengrenzen und Abnahme stehen in
[docs/t03-validation.md](docs/t03-validation.md). Registrierung und E-Mail-Verifikation sind mit T04 umgesetzt;
Geräte, Reparaturfälle, Ersatzteile und Kosten sind mit T06–T08 umgesetzt.

Das Frontend verwendet lokal eingebundenes Bootstrap und JavaScript mit kleinen
DOM-Adaptern nach dem Humble-Object-Muster: [Frontend-Aufbau](docs/frontend.md).

Fachkomponenten bleiben frameworkfrei; Datenadapter implementieren ihre Ports und
werden injiziert: [Architektur und Abhängigkeitsumkehr](docs/domain-architecture.md).


## Registrierung und E-Mail-Bestätigung

`/register` erstellt ein Konto; eine Bestätigung per E-Mail ist vor der
Anmeldung erforderlich. Benutzername und E-Mail sind eindeutig, auch bei
abweichender Gross-/Kleinschreibung. Benutzernamen: 1–80 Buchstaben/Ziffern;
Passwörter: 8–128 Zeichen. Bestätigungslinks sind 24 Stunden gültig und können
unter `/confirm` erneut angefordert werden. `/login` und die POST-Abmeldung
stammen ebenfalls aus Flask-Security. `/reset` ermöglicht das Zurücksetzen des
Passworts per E-Mail mit einem eine Stunde gültigen Link. Details und Nachweise:
[Passwort-Recovery](docs/password-reset.md). Administratorfunktionen sind deaktiviert.

In Produktion sind externer SMTP-Zugang und Absenderfreigabe Voraussetzung für
tatsächlichen Mailversand; siehe [GitHub-Einrichtung](docs/ci-cd.md) und [T04-Nachweis](docs/t04-validation.md).
Nach dem lokalen Build die Datenbank starten und die Migration explizit ausführen:

```bash
docker compose -f compose.yaml -f compose.development.yaml up -d db
docker compose -f compose.yaml -f compose.development.yaml run --rm --no-deps app flask --app app db upgrade
docker compose -f compose.yaml -f compose.development.yaml up -d
```

Migrationen werden nicht beim Start jedes Workers ausgeführt. In Produktion
übernimmt das Ansible-Deployment den kontrollierten Migrationsschritt.


### E-Mails in Development abfangen

Development startet automatisch **Mailpit** mit der Anwendung. Alle Nachrichten
landen unter **http://127.0.0.1:8025**, auch die Bestätigungslinks der Registrierung.
Die Links zeigen auf die lokale Anwendung unter `http://127.0.0.1:8080`
(beziehungsweise `HTTP_LOCAL_PORT`). Es werden keine externen E-Mails versendet:
Mailpit hat keinen konfigurierten Relay oder Forwarder und keinen
veröffentlichten SMTP-Port. Seine Weboberfläche ist nur auf Loopback erreichbar.

Die Development-Datei überschreibt SMTP-Host, Port, Zugangsdaten, Absender und
TLS-Einstellungen ausdrücklich; externe SMTP-Werte aus `runtime.env` werden daher
nicht genutzt. Unverschlüsseltes SMTP auf `mailpit:1025` bleibt auf das interne
Entwicklungsnetz begrenzt. Produktion verwendet weiterhin verschlüsseltes SMTP.

```bash
docker compose -f compose.yaml -f compose.development.yaml up --build -d --wait
```

Bei Bedarf `MAILPIT_LOCAL_PORT` in `.env` ändern. Nachrichten sind temporäre
Testdaten und gehen beim Stoppen/Neuerstellen des Mailpit-Containers verloren.
Nach erstmaligem Build die oben beschriebene Migration ausführen, bevor ein
Benutzer registriert wird. Keine zusätzlichen SMTP-Secrets für Development nötig.

Mailpit ist ein reines Entwicklungswerkzeug; es wird weder nach GHCR veröffentlicht
noch durch Produktions-Ansible ausgerollt. Die isolierten CI-Mailtests bleiben
unabhängig davon. Grundlage: [offizielle Docker-Dokumentation](https://mailpit.axllent.org/docs/install/docker/).

Die Anwendung unterstützt Deutsch und Englisch anhand der Browsersprache
(`Accept-Language`), mit Englisch als Fallback. Endpoints bleiben Englisch: [i18n-Konvention und Befehle](docs/i18n.md).

Die visuelle Marke folgt dem Werkstatt-Thema mit klarer Formularhierarchie und
Gestaltregeln: [Design-System](docs/design-system.md).

Die Benutzerabläufe verwenden injizierte Domain-Handler und Flask-Security als
technischen Adapter: [Aufrufwege und Grenzen](docs/user-use-cases.md).


## Geräteverwaltung (T06)

Nach Anmeldung führt **Your devices / Deine Geräte** zur Geräteübersicht. Name,
Hersteller und Modell sind erforderlich. Erfassung und Bearbeitung speichern per
AJAX; Listen starten mit 20 serverseitigen Zeilen und behalten danach höchstens
60 Gerätezeilen im DOM. Ohne JavaScript bleiben Formulare und Seitenlinks nutzbar.
Details: [Geräteverwaltung](docs/devices.md), [Abnahme](docs/t06-validation.md).

Der normale `deploy.yml`-Aufruf gleicht die Nginx-CSP mit `connect-src 'self'`
automatisch ab und liefert den geprüften App-Digest samt Migration aus.
Identische Wiederholungen erstellen keine Container neu; eine separate
Infrastrukturfreigabe ist nicht erforderlich.
Keine neuen Environment-Variablen oder Secrets. Offene Security-Abnahmen bleiben
im T06-Nachweis ausdrücklich ausgewiesen.

Die authentifizierte, lesende REST-API und die zusätzlich erforderlichen
Deployment-Prüfwerte sind in [docs/api.md](docs/api.md) beschrieben.

T10 vervollständigt Navigation und Fehlerpfade. Der vollständige Browserablauf
von Registrierung bis Kostenanzeige wird in beiden Sprachen mit und ohne
JavaScript geprüft: [T10-Abnahme](docs/t10-validation.md).

Deployment, Backupaufbewahrung und Wiederherstellung sind in der
[Betriebsanleitung](docs/operations.md) beschrieben. T11 ist als Dokumentationsaufgabe
abgeschlossen; eine Datenbankwiederherstellung wurde ausdrücklich nicht ausgeführt:
[T11-Nachweis](docs/t11-validation.md).

Reparaturfälle unterstützen Suche und kombinierbare Statusfilter mit SSR und
virtuellen AJAX-Fenstern: [Suchsemantik](docs/repairs.md),
[K-T01-Abnahme](docs/kt01-validation.md).
