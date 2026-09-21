# RepairHub

RepairHub wird eine Webanwendung zur Verwaltung privater Reparaturfälle für
Haushaltsgeräte und Elektronik. Der aktuelle T02-Stand enthält das minimale
Flask-Gerüst mit PostgreSQL-Bereitschaftsprüfung, Docker Compose und eine
Pipeline für Test → Build → Security → Deploy über GitHub Actions und Ansible.
Benutzerkonten, Geräte, Reparaturfälle und die fachliche API folgen ab T04.
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

docker compose -f compose.yaml -f compose.development.yaml up --build -d --wait
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
in die zuständigen Services, Datenzugriff in `app.data`; `app.services.costs`
bleibt eine reine Berechnungskomponente. Die technische Bereitschaftsprüfung
verwendet eine gekapselte Diagnoseschnittstelle.

- [Pipeline, Secrets-Namen, Branchregeln und Betrieb](docs/ci-cd.md)
- [Tatsächliche T02-Prüfergebnisse und offene externe Abnahme](docs/t02-validation.md)
- [Isolierter lokaler Ansible-Testhost](tests/deployment/README.md)

Test, Build und Security laufen auf allen Branches und bei Pull Requests.
`main`, Tag-Pushes und veröffentlichte GitHub-Releases durchlaufen zusätzlich
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
