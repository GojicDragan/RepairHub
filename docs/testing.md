# Teststufen

Stand: 18. September 2026. Benutzerentscheid: Tests der Anwendung werden in
**Unit**, **Integration** und **End-to-End** aufgeteilt. Bezug: T02, M07,
N03–N05 und N07–N10. Mit den folgenden Funktionstasks wächst jede passende Stufe
zusammen mit der Implementierung.

| Stufe | Verzeichnis und Umfang | Voraussetzungen |
| --- | --- | --- |
| Unit | `tests/unit/app`: einzelne Konfigurationsfunktionen; `tests/unit/ci`: isolierte CI-Auswertung; `tests/unit/test_architecture.py`: Importregeln | Python und gesperrte Entwicklungsabhängigkeiten; keine laufende Datenbank und kein Browser |
| Integration | `tests/integration/app`: Factory, Flask-Routen, CSRF und PostgreSQL; `tests/integration/ci`: tatsächlich gestartete Scanner-Ersatzprozesse | Für den DB-Fall eine eigene PostgreSQL-Testdatenbank über `TEST_DATABASE_URL` |
| End-to-End | `tests/e2e`: echter Chromium-Browser über HTTPS/Nginx und Gunicorn/Flask bis zu PostgreSQL | Docker, OpenSSL, verifizierte Image-Archive und die Gruppe `e2e` samt Chromium |

Die bestehenden Prüffälle bleiben erhalten. Konfigurations-Unit-Tests rufen
`load_config` beziehungsweise `validate_config` direkt auf. Das Zusammenbauen
der Flask-Anwendung und ihre Routen gehören zur Integration. Zusätzliche
Factory-Tests sichern ab, dass die isoliert geprüfte Validierung tatsächlich
beim Start verwendet wird. Prozessfehler werden mit echten Unterprozessen in
der Integrationsstufe geprüft; rein simulierte Scanner bleiben Unit-Tests.

`tests/conftest.py` weist anhand des Verzeichnisses genau einen Marker `unit`,
`integration` oder `e2e` zu. Widersprüchliche Marker und Tests ausserhalb dieser
Verzeichnisse brechen die Sammlung ab. App-/DB-Fixtures liegen nur unter
`tests/integration`, Browser-/Container-Fixtures nur unter `tests/e2e`.
Neue Tests sind direkt in die passende Stufe einzuordnen.

## Lokal ausführen

```bash
uv sync --locked
uv run --locked pytest tests/unit
uv run --locked pytest tests/integration
```

Für die Datenbankintegration muss `TEST_DATABASE_URL` auf eine separate
PostgreSQL-Testdatenbank zeigen. SQLite ist kein Ersatz. Ohne URL wird genau
der PostgreSQL-Fall lokal sichtbar übersprungen; bei `CI=true` schlägt die
fehlende Voraussetzung fehl. Ein lokaler Lauf mit einem übersprungenen DB-Fall
ist keine vollständige Integrationsabnahme.

Browserabhängigkeiten separat installieren und die zu prüfenden Images bauen:

```bash
uv sync --locked --group e2e
uv run --locked --group e2e playwright install --with-deps --only-shell chromium
uv run --locked python scripts/ci/images.py build --commit "$(git rev-parse HEAD)"
uv run --locked --group e2e pytest tests/e2e
```

Der Build erzeugt nur das App-Image. Nginx und PostgreSQL werden mit den Pins
aus `deploy/infrastructure.json` bezogen und für die Prüfung ebenfalls
archiviert. Beide offiziellen Images sind bereits per Digest festgelegt;
ein eigener PostgreSQL-Build oder GHCR-Release ist nicht nötig. Für eine lokale
Registry-Fixture kann `REPAIRHUB_INFRASTRUCTURE_FILE` auf deren eigene geprüfte
Pin-Datei zeigen. Diesen Override bei Build, Verifikation, Scans und E2E gleich
setzen, damit alle Schritte dieselbe Infrastruktur prüfen.

`--with-deps` installiert erforderliche Browser-Systembibliotheken. Wenn diese
bereits vorhanden sind, genügt `playwright install --only-shell chromium`.
Playwright 1.63.0 und seine Python-Abhängigkeiten stehen im Lockfile; diese
Version legt die Chromium-Revision 1243 fest. Die Browserbibliothek gehört nicht
zu den produktiven Anwendungsabhängigkeiten. Grundlagen:
[Playwright-Browser](https://playwright.dev/python/docs/browsers) und
[Python-Bibliothek](https://playwright.dev/python/docs/library).

Alternativ wählt `pytest -m unit`, `pytest -m integration` beziehungsweise
`pytest -m e2e` die jeweilige Stufe. Für E2E die Gruppe `e2e` verwenden. `pytest`
ohne Auswahl sammelt alle drei Stufen und benötigt alle Voraussetzungen.
Fehlende Image-Archive, falscher Commit, fehlender Browser oder Dockerfehler
werden in der E2E-Stufe als Fehler behandelt, nicht übersprungen.

## Echte Ende-zu-Ende-Abläufe

Die E2E-Fixture verwendet die bereits gebauten und verifizierten Archive unter
`artifacts/images`; sie baut keine zweite Anwendung. Ein anderer Ablageort kann
über `--image-artifacts`, der zugehörige Commit über `--image-commit` angegeben
werden. In CI stammt der Commit aus `GITHUB_SHA`, lokal standardmässig aus HEAD.
Uncommittete lokale Änderungen sind dadurch noch kein veröffentlichter Release.
Die statischen Dateien stammen aus dem verifizierten App-Container. Das
offizielle Nginx-Image bekommt sie zusammen mit der geprüften Konfiguration
als schreibgeschützte Verzeichniseinbindungen; es enthält keinen App-Code.

Eine neue temporäre PostgreSQL-Instanz, Gunicorn und Nginx laufen pro Sitzung in
einem eigenen Docker-Bridge-Netz. Für den Browser auf dem Testrechner wird
ausschliesslich Nginx an einen zufälligen Port auf `127.0.0.1` gebunden; App und
Datenbank bleiben unveröffentlicht. Der gemeinsame Runtime-Helfer veröffentlicht
bei DAST- und Build-Smoke-Tests standardmässig weiterhin keine Ports und verwendet
dort ein zusätzlich mit `--internal` abgeschottetes Netz. Docker veröffentlicht
auf einem solchen internen Netz keine Hostports; E2E benötigt deshalb die
eigene normale Bridge mit ausdrücklich auf Loopback begrenzter Bindung.

Vor dem Browserstart prüft die Fixture die HTTPS-Verbindung mit vollständiger
Zertifikats- und Hostnamenprüfung gegen ihre neu erzeugte Test-CA. Nur der
zugehörige Browserkontext akzeptiert danach diese nicht systemweit installierte
Testidentität mittels `ignore_https_errors`. HTTP(S)-Anfragen der Testseiten
werden auf die lokale Test-Origin begrenzt; das ersetzt keine allgemeine
Browser-Firewall. Es werden keine produktiven Zugangsdaten verwendet.

Das T02-Grundgerüst hat drei Browserprüfungen:

1. Startseite, deutsche Darstellung, tatsächlich geladenes CSS und
   Sicherheitsheader über HTTPS.
2. Bereitschaft über die gesamte Verbindung bis zur realen PostgreSQL-Datenbank.
3. Ausfall der eigenen temporären Datenbank: generisches HTTP 503 ohne interne
   Details; anschliessend Wiederanlauf der Testdatenbank.

Anwendung, Browserkontexte und Datenbank werden nicht durch Mocks ersetzt.
Container, Netz und temporäre Geheimnisdateien werden auch nach Testfehlern
bereinigt. Noch nicht vorhandene Registrierung, Geräte- und Reparaturabläufe
können in T02 nicht als Ende-zu-Ende geprüft gelten. Ab T05–T09 kommen diese
Browser-/API-Abläufe mit Testkonten und eigenen Daten hinzu.

## Pipeline und Berichte

Im Job **Test** laufen Unit und Integration in getrennten Schritten. Die
Pipeline stellt PostgreSQL bereit und führt auch die Architektur- und
Ansible-Prüfungen aus. Im Job **Build** folgen nach dem einmaligen Image-Build
und Bereitschaftstest die verpflichtenden Browser-E2E-Tests. Erst danach werden
die Image-Archive an **Security** weitergegeben. ZAP bleibt zusätzlich als
aktiver DAST-Scan in der Security-Stufe erhalten.

| Bericht | Workflow-Artefakt |
| --- | --- |
| `reports/test/unit.xml` | `test-<Commit>-<Versuch>` |
| `reports/test/integration.xml` | `test-<Commit>-<Versuch>` |
| `reports/e2e/pytest.xml` | `build-<Commit>-<Versuch>` gemeinsam mit dem Image-Manifest |

Berichte werden soweit vorhanden auch nach Fehlern hochgeladen. Ein roter
Testschritt verhindert den erfolgreichen Abschluss seiner Stufe und damit
Veröffentlichung/Deployment. Tatsächliche Ergebnisse stehen in
[t02-validation.md](t02-validation.md); eine lokale Prüfung ersetzt keinen
ausgeführten GitHub-Actions-Lauf.
