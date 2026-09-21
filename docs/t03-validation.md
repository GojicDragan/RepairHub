# T03 – Flask-Grundgerüst und Compose-Basis

Stand: 21. September 2026. Bezug: **M07, N09–N10**; Sicherheitsprüfungen ergänzen
N07. T03 erweitert das vorhandene T02-Gerüst. Fachliche Benutzer-, Geräte-,
Reparatur- und Teilefunktionen sowie Modelle bleiben T04–T09 vorbehalten.

## Umsetzung und Komponentengrenzen

| Bereich | Ergebnis / Schnittstelle |
| --- | --- |
| Application Factory | `create_app(config=None)` initialisiert unabhängige Flask-Instanzen, Erweiterungen, Web-/API-Blueprints und Fehlerbehandlung. Keine DB-Verbindung oder Schemaänderung beim Start. |
| Konfiguration | `load_config(environment=None)` lädt passende Umgebungsdefaults vor individuellen Overrides. `validate_config` weist fehlenden Schlüssel, ungültige PostgreSQL-URL und unsichere Produktionswerte verständlich ab. |
| Weboberfläche | Gemeinsame `base.html` mit deutscher Navigation, Sprunglink und Inhaltsbereich; Startseite und Fehlerseite erben davon. `app.web.errors.render_error` erzeugt ausschliesslich HTML. |
| REST-API | `app.api.errors.render_error` erzeugt ausschliesslich JSON. Noch keine Authentifizierung oder fachlichen API-Endpunkte. |
| Diagnose/Datenzugriff | `/health/ready` → `check_readiness()` → `database_ready()`. Echte PostgreSQL-Verbindung; Ausfall liefert 503 ohne Verbindungsdetails. |
| Fachliche Services | Die fünf vereinbarten Servicepakete bleiben getrennt. Ihre Fachschnittstellen entstehen mit den zugehörigen Funktionstasks; keine vorgezogenen Stub-Funktionen oder zusätzlichen Abhängigkeiten. |
| Compose | Gemeinsame Dienste nginx/app/db, Entwicklung mit lokalem HTTP und Reload, Produktion mit HTTPS. App und DB haben keine veröffentlichten Hostports. |

Die Factory wählt den Fehlerrenderer anhand des API-Pfads (`/api` oder `/api/…`).
Das ist notwendig, weil Routing-404/405 entstehen können, bevor ein Blueprint
zugeordnet ist. Weboberfläche und API importieren einander nicht und greifen
auch in Fehlerfällen nicht auf ORM-Modelle oder Sessions zu. Die Architekturtests
prüfen diese Grenzen zusätzlich für die neuen Fehlerdarstellungen.
[Flask-Fehlerbehandlung](https://flask.palletsprojects.com/en/stable/errorhandling/).

## Fehlervertrag und Diagnose

Browserfehler enthalten deutsche, festgelegte Texte und einen Link zur Startseite.
API-Fehler besitzen HTTP-Status und JSON nach diesem Beispiel:

```json
{
  "error": {
    "status": 404,
    "title": "Seite nicht gefunden",
    "message": "Die angeforderte Ressource wurde nicht gefunden."
  }
}
```

Der Vertrag gilt bereits für unbekannte API-Routen. Statuscodes und fachlich
notwendige HTTP-Header wie `Allow` und `Retry-After` bleiben erhalten. HEAD liefert
keinen Body; automatische OPTIONS-Anfragen bleiben erlaubt. Bereitschaftsantworten
bleiben unverändert: `{"status":"ready"}` (200) beziehungsweise
`{"status":"unavailable"}` (503).

Unerwartete Ausnahmen ergeben 500. Protokolliert werden Fehlertyp, registrierter
Endpoint sowie Modul-/Funktionsnamen und Zeilennummern des Aufrufwegs. Exception-
Texte, SQL-Parameter, lokale Variablen, URLs und Request-Inhalte werden nicht
protokolliert. Damit lassen sich Fehler im Quellcode zuordnen, ohne Zugangsdaten
oder Tokens aus Exceptions zu übernehmen. Das ist bewusst kein vollständiger
Traceback-Dump. CSRF- und Grössenfehler erhalten ebenfalls verständliche Antworten.

## Sichere Konfiguration

Produktion verlangt aktivierten CSRF-Schutz, Secure/HttpOnly für Sitzungs- und
Remember-Cookies sowie SameSite Lax oder Strict. Debug, Testing und SQL-Echo
werden abgewiesen. SQLAlchemy blendet Parameter aus. Die explizite Entwicklung
kann lokale HTTP-Cookies verwenden; Factory-Overrides wählen die Defaults der
gewünschten Umgebung, unabhängig vom Umgebungsmodus des aufrufenden Prozesses.
[Flask-Cookie-Einstellungen](https://flask.palletsprojects.com/en/stable/web-security/).

## Abnahme

Die folgenden Prüfungen verwenden den lokalen Arbeitsbaum. Der Image-Commit-
Bezeichner `a0d8174be766ca7289c9a8f853894edd362d0f82` ist der bisherige HEAD,
kein Commit der noch nicht eingecheckten T03-Änderungen und kein veröffentlichter
T03-Release.

| Prüfung | Befehl / Ergebnis |
| --- | --- |
| Unit | `pytest tests/unit -q --junitxml=reports/test/t03-unit.xml`: **261 bestanden**, einschliesslich Konfiguration und Architektur |
| Integration | `.qa/t03/run-integration.py` startet eine eigene PostgreSQL-Instanz und führt `pytest tests/integration -q --junitxml=reports/test/t03-integration.xml` aus: **69 bestanden, keine Skips** |
| Build | `scripts/ci/images.py build --directory artifacts/t03 --commit <HEAD>`: erfolgreich, finale App samt gepinnter Infrastruktur archiviert und geprüft |
| Browser | `pytest tests/e2e --image-artifacts artifacts/t03 --junitxml=reports/t03/final-e2e.xml -q`: **5 bestanden**, inklusive tatsächlichem DB-Ausfall und Wiederanlauf |
| Frischer Compose-Start | `.qa/t03/check-compose.py`: eigenes Projekt mit neuen Zugangsdaten und Volume; Nginx-Startseite, echte DB-Bereitschaft, API-404 und zweites `up` erfolgreich |
| Produktionseinstellungen | Gerenderte Produktions-Compose-Konfiguration: keine Hostports für App/DB, REPAIRHUB_ENV=production; unsichere Einstellungen werden in Factory-/Konfigurationstests abgewiesen |
| Security | `scripts/ci/security.py --artifacts artifacts/t03 --reports reports/t03/final-security --binaries /tmp/repairhub-t02-scanners`: pip-audit, Bandit, Gitleaks und Trivy für alle drei Images bestanden |
| Aktiver DAST | `scripts/ci/dast.py --artifacts artifacts/t03 --reports reports/t03/final-security --commit <HEAD>`: OWASP ZAP 2.17.0 bestanden; keine Befunde mit niedrigem, mittlerem oder hohem Risiko, ein informativer Regelhinweis (10015, drei Instanzen) |
| Arbeitsbaum-Secrets | `gitleaks dir app --redact=100`: keine Funde; ergänzt den History-Scan für neue, noch nicht eingecheckte Quelldateien |
| Architektur / Qualität | `python scripts/check_architecture.py`, Ruff, Formatprüfung und Actionlint erfolgreich |
| Ansible-Erstlauf | Aktuelles Playbook mit finalen Image-Archiven auf isolierter SSH-/Docker-Fixture: ok=65, changed=23, failed=0, externe HTTPS-Prüfung erfolgreich |
| Ansible-Wiederholung | Identische Eingaben: ok=46, **changed=0**, failed=0. IDs und Startzeiten aller drei Container unverändert; `reports/t03/deployment.json` |

Insgesamt **335 Unit-/Integrations-/E2E-Tests bestanden**. Zusätzlich erfolgten
Compose- und Ansible-Prüfungen. Python-Aufrufe verwendeten die gesperrte `.venv`;
Docker-Aufrufe die separate lokale Konfiguration
`DOCKER_CONFIG=/tmp/repairhub-t02-public-docker`. Der Ansible-Test folgte
`tests/deployment/README.md` mit `artifacts/t03`, eigenem lokalen Inventory und
Test-CA. Die isolierte Fixture ersetzt keinen öffentlichen ACME-Test.

Die bestehende ausdrücklich akzeptierte PostgreSQL-gosu-Ausnahme bleibt
unverändert; es wurden keine neuen Scan-Ausnahmen eingeführt. Berichte stehen
unter `reports/t03/final-security/`, einschliesslich `zap.json` mit den geprüften
Image-Digests. Der aktive Scan lief ausschliesslich gegen die isolierte Testinstanz.

Das finale App-Archiv besitzt SHA-256
`b66cb6e802e96c0600a54f1740edcadcc8b67dd0082f7f894ab375c066709769` und
Config-Digest `sha256:3337683c44ea14687cfb14e29649901f1f354bf101a7ff224965543431b97307`.
Details und Infrastruktur-Digests stehen in `artifacts/t03/manifest.json`.

## Grenzen und nächster Schritt

Testcontainer, eigenes Compose-Volume und temporäre Zugangsdaten wurden gezielt
entfernt; bestehende lokale Benutzerdienste blieben erhalten. Kein Commit, Push,
GHCR-Publish oder Produktionsdeployment dieses T03-Stands wurde ausgeführt.
Der Benutzer hatte zuvor den Produktionslauf von T02 bestätigt. Der eingecheckte
T03-Stand muss später die normale Branch-/PR-Pipeline und für Produktion einen
Release-/Tag-Lauf durchlaufen. Eine vierwöchige Verfügbarkeit wird nicht behauptet.

Die Muss-Ziele M01–M06 sind mit diesem technischen Grundgerüst noch nicht
umgesetzt. Nächster Task ist **T04: Datenmodell und Migrationen**.

## Ergänzung: Bootstrap und Humble Objects

Nach der obigen Abnahme am 21. September 2026 auf Benutzerwunsch ergänzt:
lokales Bootstrap 5.3.8, Rückmeldungs-Presenter mit Humble-Object-DOM-Adapter
und ES-Module samt Nginx-MIME/CSP-Konfiguration. Details: [frontend.md](frontend.md).
Die obigen Image-Digests und Security-/Ansible-Ergebnisse beziehen sich auf den
Stand vor dieser Ergänzung. Für den ergänzten Stand wurde ein neues Image unter
`artifacts/t03-frontend` gebaut; GitHub-Security und Release-Abnahme bleiben
für diesen Stand auszuführen.

Frontend-Ergänzung am 21. September 2026 geprüft: 1 DOM-freier JavaScript-Unit-Test,
268 Python-Unit-/Factory-Tests und 7 E2E-Tests bestanden (einschliesslich Bootstrap,
ES-Modulen unter Nginx-CSP, Tastaturfokus und mobiler Ansicht ohne JavaScript).
Build, Ruff, Architekturprüfung und Actionlint erfolgreich. Browserbericht:
`reports/t03/frontend-e2e.xml`. Frontend-Unit-Berichte werden in CI als
`reports/test/frontend.xml` mit den übrigen Testartefakten gespeichert.

## Ergänzung: frameworkfreier Fachkern

Benutzerentscheidung vom 21. September 2026 umgesetzt als verbindliche Grundlage:
[Abhängigkeitsumkehr und Injection](architecture.md). Factory-Verdrahtung liegt nun
in `app.bootstrap`; die Paketwurzel lädt keine Frameworks beim Domain-Import.
Architekturtests verbieten konkrete Infrastruktur in sämtlichen Fachpaketen und
beschränken Datenadapter auf Ports/DTOs. Konkrete Fach-Ports entstehen erst mit den
Anwendungsfällen; noch keine Repository-Implementierungen vorhanden.

Prüfung: `pytest tests/unit tests/integration/app/test_factory.py
 tests/integration/app/test_errors.py -q`: **322 bestanden**. Ruff und
`python scripts/check_architecture.py` bestanden; separater Importtest ohne
site-packages erfolgreich. Für diese anschliessende Python-Architekturänderung
wurden Build, E2E, Security und Deployment nicht erneut ausgeführt; die oben
protokollierten Läufe und Image-Digests gelten jeweils für ihren vorherigen Stand.

## Ergänzung: vertikale Fachdomänen

Auf Benutzerwunsch die fünf Fachpakete von `app.services` nach `app.domains`
verschoben und Regeln für vertikale Anwendungsfälle ergänzt. Konkrete Slices
entstehen mit T05–T09. Architekturprüfung und Tests sichern Slice-Grenzen sowie
frameworkfreie Imports. **333 Unit-/Factory-/Fehlertests bestanden**, Ruff und
Architekturprüfung ebenfalls. Details: [domain-architecture.md](domain-architecture.md).
Kein neuer Build oder Deployment für diesen anschliessenden Strukturstand.
