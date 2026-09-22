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

1. Startseite, englische Darstellung, tatsächlich geladenes CSS und
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

## T03: Grundgerüst und Fehlerfälle

Zusätzlich geprüft werden getrennte HTML-/JSON-404-Antworten, erhaltene
Allow-/Retry-After-Header, CSRF-/Grössenfehler, 500 ohne Geheimnisse in Antwort
oder Log, unabhängige Factory-Instanzen und sichere Umgebungsdefaults.
Die Browsertests prüfen Fehlerseite, Rückkehr zur Startseite und API-404 durch
Nginx. Ein Datenbankausfall wird mit echtem gestopptem PostgreSQL getestet.
Konkrete Befehle und Ergebnisse: [t03-validation.md](t03-validation.md).

JavaScript-Unit-Tests: `node --test tests/unit/frontend/*.test.mjs tests/unit/ci/*.test.mjs` (Node.js 22 oder
neuer), zusätzlich zu pytest. DOM-freie Presenter werden mit Fake-Views geprüft;
DOM-Bindung, Bootstrap und progressive Erweiterung deckt Playwright ab.
Siehe [Frontend-Aufbau](frontend.md).

## T04: Standard-Registrierung und E-Mail-Verifikation

`pytest tests/integration/users` prüft Flask-Security mit echter PostgreSQL-Migration
in einem eigenen Schema pro Test: Validierung, Passwort-Hashing, Eindeutigkeit,
Konkurrenz, Bestätigung/Erneutversand/Ablauf, Login-Sperre und Mailfehler-Rollback.
SMTP wird zusätzlich gegen einen lokalen `aiosmtpd`-Empfänger geprüft.

`pytest tests/e2e --image-artifacts artifacts/t04` prüft Browser und echte Images.
Der Mail-Empfänger ist ein isolierter STARTTLS-Container mit eigener Test-CA, ohne
Host-Port und ohne Weiterleitung. Beide Browservarianten (mit/ohne JavaScript)
lesen ausschliesslich dieses Testpostfach. Der DB-Neuerstellungstest ersetzt nur
die eigene Fixture und übernimmt deren temporäres Volume. Tests prüfen zudem,
dass Bestätigungstokens nicht im Nginx-Zugriffslog stehen.

Für isolierte Laufzeitprüfungen wird die Dev-Abhängigkeit `aiosmtpd` benötigt;
`uv sync --locked --group e2e` installiert sie zusammen mit der standardmässigen
Dev-Gruppe. `tests/support/smtp_receiver.py` ist Testinfrastruktur und gehört
nicht als pytest-Test in eine der drei Teststufen.

## T05: Anmeldung und Browsersitzungen

`uv run --locked pytest tests/integration/users/test_sessions.py` prüft mit
`TEST_DATABASE_URL` dieselbe PostgreSQL-Fixture wie die Registrierung: echte
Sitzungs-/Remember-Cookies, CSRF für Login und Logout, deaktivierte Konten,
entzogene Bestätigung und den frameworkfreien Identitätsport. Es werden keine
Gerätefunktionen vorgezogen. Domain- und Routingtests sichern weiterhin den
Aufrufweg über injizierte Handler. Der E2E-Ablauf prüft deutsche und englische
Seiten mit und ohne JavaScript; Validierungsfehler ohne JS werden serverseitig
abgenommen. Ergebnisse und Grenzen: [T05-Abnahme](t05-validation.md).

## T06: Geräte, Eigentumsprüfung und AJAX

`tests/unit/domains/devices`, `tests/integration/devices` und
`tests/e2e/test_devices.py` prüfen die vier Geräteanwendungsfälle. Die PostgreSQL-
Schema-Fixture liegt nun gemeinsam in `tests/integration/conftest.py`; sie kann
auch die vorherige Migration für einen echten Upgrade-Test anlegen. Die zusätzliche
Tabelle ist im Modell-/Schemaabgleich berücksichtigt.

Node-Tests unter `tests/unit/frontend/device-presenters.test.mjs` prüfen begrenzte
Fenster, verspätete Antworten, Rückscrollen, Netzfehler, Wiederholung und paralleles
Absenden ohne DOM. Browserprüfungen verwenden je 240 eigene Geräte, prüfen zuerst
20 Zeilen im gelieferten HTML und danach höchstens 60 Zeilen im DOM. AJAX-Speichern,
Fehlererhalt und der Betrieb ohne JavaScript werden auf Englisch/Deutsch geprüft.
Ergebnisse und Releasehinweise: [T06-Abnahme](t06-validation.md).

## T07: Reparaturfälle und Schritte

- `tests/unit/domains/repairs/test_repairs.py`: frameworkfreie Regeln und alle
  sieben Slices mit Fakes, einschliesslich unzulässiger Identitäten/Zuordnungen.
- `tests/integration/repairs/test_repairs.py`: PostgreSQL-Persistenz, Migration
  ab T06, Eigentum, HTML/JSON, CSRF, Validierung, DB-Constraints und Rollback.
- `tests/unit/frontend/repair-form-presenter.test.mjs`: Formzustand, expliziter
  Erledigungszustand, leere Entwürfe, paralleles Absenden und Fehler.
- `tests/e2e/test_repairs.py`: Anlage, Beschreibung, Status einschliesslich
  Wiederaufnahme, Schritte, Entwurfserhalt und Netzwerkfehler. Deutsch/Englisch,
  mit und ohne JavaScript, mobile Darstellung. AJAX wird ausdrücklich anhand
  der Testkonfiguration erwartet; ein Ladefehler kann nicht als HTML-Fallback
  einen grünen AJAX-Test erzeugen.

Die bestehenden Befehle für die vollständigen Unit-, Integrations- und E2E-Suiten
schliessen diese Tests ein. Ergebnisse: [T07-Abnahme](t07-validation.md).

## T08: Ersatzteile, Arbeitswerte und Kosten

`tests/unit/domains/costs` prüft die reinen CHF-Beispiele, Rundung, grosse Werte,
unabhängigen Decimal-Kontext und Eingabegrenzen. `tests/unit/domains/parts`
prüft Teile-Slices und Arbeitswerte mit Fake-/Mock-Repositories, insbesondere
Eigentum vor Validierung und fehlende Schreibzugriffe bei ungültigen Eingaben.

`tests/integration/parts` verwendet PostgreSQL: Kosten nach Anlegen/Bearbeiten,
manipulierte Gesamtsummen, atomare Rücknahme nach Commit-Fehler, Eigentums- und
Fallzuordnung, DB-Constraints, Pagination mit vollständiger Kostensumme sowie
Upgrade vorhandener T07-Daten. `tests/e2e/test_parts.py` prüft Englisch/Deutsch
mit und ohne JavaScript, AJAX ohne Dokumentnavigation, Formularentwürfe,
Validierungsfehler, Persistenz und mobile Darstellung. Derselbe Presenter wird
weiter durch die bestehenden JavaScript-Tests abgesichert.

Der neue Task benötigt keine zusätzlichen Ausnahmen der Architekturregeln und
keine neue Abhängigkeit. Ergebnisse und Betriebsprüfung: [T08-Abnahme](t08-validation.md).
