# CI/CD und Bereitstellung

Stand: 21. September 2026. Bezug T02, M07 und N03–N05/N07–N10.
Die normale GitHub-Actions-Pipeline prüft und veröffentlicht das App-Image.
Nginx und PostgreSQL besitzen davon unabhängige Infrastruktur-Versionen.
Ansible verwaltet den gemeinsamen Zustand mit den Compose-Dateien dieses
Repositorys. Die Anwendung bleibt ein modularer
Flask-Monolith in den drei Diensten `nginx`, `app` und `db`.

## Pipeline und Branches

Für diese Praxisarbeit gibt es gemäss aktuellem Benutzerentscheid genau ein
Bereitstellungsziel: Release-Tags → GitHub-Environment `production`. Eine separate
Testumgebung und ein Integrationsbranch für Deployments sind nicht vorgesehen.
Dies ersetzt die frühere Zuordnung `develop` → `test`.
Pushes auf **alle Branches**, einschliesslich `main`, sowie Pull Requests führen
Test, Build und Security aus; bei offenem PR übernimmt dessen Lauf die Prüfungen
des Feature-Branches und der zusätzliche Push-Lauf überspringt sie.
Nur veröffentlichte GitHub-Releases dürfen anschliessend
das geprüfte App-Image veröffentlichen und nach `production` ausliefern.

| Auslöser | Test → Build → Security | Publish → Deploy |
| --- | --- | --- |
| Push auf beliebigen anderen Branch | Ja, sofern kein offener PR existiert | Nein |
| Push auf `main` (auch Merge) | Ja | Nein |
| Pull Request | Ja | Nein |
| Push eines Tags (beliebiger Name) | Kein Lauf | Nein |
| GitHub-Release veröffentlicht (`release.published`) | Ja | Ja, für aktuellen `main`-Commit |
| Manueller Lauf (`workflow_dispatch`) | Ja | Nein |

Vor Veröffentlichung und erneut vor Deployment prüft `check_release_ref.py`,
dass der Commit weiterhin dem aktuellen `main`-Stand entspricht. Bei Tags wird
zusätzlich die aktuelle Tag-Zuordnung geprüft; annotierte und einfache Tags
werden über die Commit-API aufgelöst. Verschobene, gelöschte oder veraltete Tags
und API-Fehler blockieren die Auslieferung. Tags deshalb auf dem aktuellen
`main`-Commit setzen. Erst die Veröffentlichung des GitHub-Releases löst den
vollständigen Release-Lauf aus, auch bei einem Prerelease. Der Tag-Push selbst
ist kein Workflow-Auslöser mehr: So entstehen beim Taggen und anschliessenden
Veröffentlichen nicht zwei vollständige Auslieferungen desselben Releases.
Branch-Pushes ohne offenen PR behalten ihren eigenen Prüflauf ohne Publish/Deploy.
[GitHub: Branch-/Tag-Filter](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax),
[Release-Ereignisse](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows),
[Commit-API](https://docs.github.com/en/rest/commits/commits).

Unit-, Integrations- und End-to-End-Tests sowie aktiver ZAP laufen weiterhin mit
kurzlebigen isolierten CI-Instanzen und eigenen Testdaten. Die lokale
[Ansible-Fixture](../tests/deployment/README.md) prüft Deployment-Fehlerpfade.
Diese Prüfstände benötigen weder eine GitHub-Environment `test` noch einen
dauerhaften Testserver. Aktive Sicherheitsscans richten sich auf die CI-Instanz.

| Stufe | Tatsächlicher Inhalt |
| --- | --- |
| Test | Gesperrte Python-Abhängigkeiten; Ruff und actionlint; getrennte Unit- und Integrationstest-Schritte mit eigenen JUnit-Berichten; Architekturprüfung, echte PostgreSQL- und Scanner-Prozessintegration; Ansible-Lint und Syntaxprüfung |
| Build | App einmal bauen; festgelegte Nginx-/PostgreSQL-Images beziehen; alle drei archivieren und verifizieren; PostgreSQL-/HTTPS-Smoke-Test und verpflichtende Chromium-End-to-End-Tests |
| Security | Open-Source-Scanner für Abhängigkeiten, SAST, Secrets und Container; zusätzlich aktiver ZAP-DAST-Scan der isoliert gestarteten Image-Kombination |
| Publish | Nach bestandenem Security-Job Archive erneut verifizieren; ausschliesslich das geprüfte App-Image nach GHCR übertragen und per Registry-Digest zurücklesen/vergleichen |
| Deploy | Für `production` serialisiert; überholten Branchstand abweisen; geschützte Eingaben bereitstellen; `ansible-playbook` mit geprüften SSH-Hostschlüsseln aufrufen |

`Publish` ist technisch ein eigener Job, damit nur dieser `packages: write`
erhält. Standardberechtigung ist `contents: read`. Produktionsgeheimnisse sind
nur dem Deploy-Job mit Environment `production` zugänglich. Es gibt kein
`pull_request_target`, keine Ausführung auf dem Produktionshost als CI-Runner
und keinen erneuten Image-Build auf dem Zielserver.

Die App liegt unter `ghcr.io/gojicdragan/repairhub/app`. Ein Commit-Tag dient der
Zuordnung, ausgeliefert wird ausschliesslich `@sha256:…`. Die normale Pipeline
liefert nur `app_image` als Veröffentlichungs-Ausgabe. Infrastruktur-Pins stehen
versioniert in `deploy/infrastructure.json`; Ansible liest dieselbe Datei.
`artifacts/images/manifest.json` verbindet Commit, Plattform `linux/amd64`, alle
drei Image-IDs, zugehörige Konfigurations-Digests und Archivprüfsummen;
`release.json` hält die freigegebenen
Registry-Digests und den Datenbank-Kompatibilitätsvertrag fest. Das Commit-Label
bindet die App an ihren Quellstand; Infrastruktur wird gegen ihre eigenen Pins
geprüft. Eine fremde App-Version oder ein beschädigtes Archiv wird abgewiesen. Bei
OCI-Archiven wird die Kette Index → Plattformmanifest → Konfiguration geprüft;
damit bleibt die Identität auch zwischen unterschiedlichen Docker-Image-Speichern
nachweisbar.

Das Image-Artefakt verwendet Commit und Workflow-Run-ID als Namen, damit die
Wiederholung eines fehlgeschlagenen Folgejobs das bereits geprüfte Artefakt
verwenden kann. Test-/Scanberichte tragen zusätzlich den Versuch und werden
auch bei Fehlern soweit vorhanden aufbewahrt: Berichte 30 Tage, Image-Archive
7 Tage, Release-Zuordnung 90 Tage.

Die Teststufen stehen in `tests/unit`, `tests/integration` und `tests/e2e`.
`reports/test/unit.xml`, `reports/test/integration.xml` und
`reports/e2e/pytest.xml` weisen sie getrennt aus. E2E läuft im Build-Job, weil
erst dort die auszuliefernden Images vorliegen; ein Fehler verhindert Security,
Veröffentlichung und Deployment. Browserabhängigkeiten sind in der separaten
Gruppe `e2e` gesperrt. Die genaue Einteilung und lokalen Aufrufe stehen in
[testing.md](testing.md).

## Offizielle Infrastrukturimages

Nginx verwendet das offizielle, über Version und Digest festgelegte Image.
Konfiguration und TLS-Dateien stellt Ansible in stabilen Hostverzeichnissen
bereit. Statische Dateien werden aus dem geprüften App-Image entnommen und über
`www/current` auf die passende Release-Version umgeschaltet. Dafür wird kein
eigenes Nginx-Image gebaut oder veröffentlicht.

PostgreSQL wird ebenso direkt als offizielles Image bezogen:
`postgres:17.11-alpine3.24@sha256:f02121de6f74d30d8a94cd1d9584125e2178d7e6c377d8130112d4e52d867995`.
Der Benutzer hat für die Praxisarbeit ausdrücklich entschieden, auf den eigenen
`gosu`-/`su-exec`-Fix und den separaten DB-Release zu verzichten. Deshalb gibt es
weder ein eigenes PostgreSQL-Dockerfile noch einen zusätzlichen GitHub-Workflow
oder ein eigenes GHCR-Datenbankpaket. Diese Entscheidung ersetzt die frühere
Anleitung zur ersten DB-Veröffentlichung.

Beide offiziellen Pins stehen vollständig in `deploy/infrastructure.json`.
CI bezieht diese Images, prüft ihre Identität und testet/scant dieselbe
Kombination mit dem App-Image. Für die Datenbank werden PostgreSQL-Version,
Hauptversion und Datenverzeichnis geprüft; eigene RepairHub-Labels werden
nicht vorausgesetzt. Der Layoutvertrag lautet
`postgres-17-alpine-uid70-pgdata-v1`. Er verhindert automatische Wechsel auf
andere Datenlayouts, ersetzt aber keine Prüfung einer Datenübernahme.

Zur Einrichtung den Host einmalig mit `bootstrap.yml` vorbereiten. Der erste
App-Release über `deploy.yml` richtet alle drei Compose-Dienste ein. Jeder weitere
Release gleicht den gesamten Sollzustand idempotent ab; unveränderte Dienste
werden nicht neu erstellt. Für PostgreSQL ist keine eigene
Veröffentlichung und kein manuelles Kopieren eines GHCR-Digests mehr erforderlich.

Bei späteren Infrastruktur-Updates werden die offiziellen Image-Pins
gezielt geändert und erneut geprüft. Auch auf einem bereits eingerichteten Host übernimmt `deploy.yml` diese
Änderungen automatisch. Ein zusätzlicher Wartungsaufruf oder Freigabe-Tag ist
nicht erforderlich. Ein geänderter Datenbankvertrag
benötigt weiterhin einen separat geprüften Datenübernahme-/Migrationsplan.

Lokale isolierte Prüfungen können eine eigene Pin-Datei über
`REPAIRHUB_INFRASTRUCTURE_FILE` beziehungsweise `--infrastructure` verwenden.
Für Ansible heisst der entsprechende Controllerpfad
`repairhub_infrastructure_file`. Ein lokaler Registry-Digest ist kein
veröffentlichter GHCR-Release und wird nicht als produktiver Pin eingecheckt.

## Versionen, Scanner und Quellen

Direkte Python-Versionen und alle transitiven Abhängigkeiten stehen in
`pyproject.toml`/`uv.lock`; CI-Werkzeuge liegen in der separaten Gruppe `ci`.
Das App-Basisimage ist im Dockerfile auf Version und Digest festgelegt;
die offiziellen Nginx- und PostgreSQL-Laufzeitimages stehen
in `deploy/infrastructure.json`. Ansible setzt die geprüften Registry-Digests
ein. Neue Versionsstände benötigen erneute Tests und Scans.

Die Laufzeit basiert auf Python 3.13.15 mit Alpine 3.24, Nginx 1.30.5 mit Alpine
und PostgreSQL 17.11 mit Alpine 3.24. Erste Scans der Debian-Varianten zeigten
blockierende Befunde. Das App-Image enthält deshalb keine für den Betrieb
unnötigen System-pip-/ensurepip-Werkzeuge. PostgreSQL verwendet unverändert den
offiziellen Entrypoint einschliesslich `gosu`. Die bekannten Befunde in dessen
Go-Laufzeit werden aufgrund des Benutzerentscheids eng begrenzt akzeptiert;
die Sicherheitslücken sind damit nicht behoben. Der Container wird weiterhin
gescannt und mit der Anwendung geprüft.
[Quelle: offizielles PostgreSQL-Image](https://hub.docker.com/_/postgres).

| Werkzeug | Version | Sperrkriterium |
| --- | --- | --- |
| Python / uv | 3.13.15 / 0.12.16 | `uv … --locked`; abweichendes Lockfile ist ein Fehler |
| Ruff / pytest | 0.16.8 / 9.1.1 | Lint-/Formatfehler oder fehlgeschlagene Tests |
| Playwright / Chromium Headless Shell | 1.63.0 / Revision 1243 | Jeder fehlgeschlagene Browser-E2E-Test oder fehlende Browser-/Docker-Voraussetzung |
| ansible-core / ansible-lint | 2.21.4 / 26.8.0 | Lint-, Syntax- oder Ausführungsfehler |
| community.docker | 5.3.0 | Versionierte Collection; zusätzlich transitive Collection 1.1.5 gesperrt |
| pip-audit | 2.10.1 | Jeder bekannte Befund; übersprungene Pakete oder Scannerfehler blockieren ebenfalls |
| Bandit | 1.9.4 | Ab MEDIUM-Schwere und MEDIUM-Konfidenz; Scannerfehler blockieren |
| Gitleaks | 8.30.1 | Jeder Secret-Fund; Ausgabe wird auf Fundort und Regel reduziert |
| Trivy | 0.74.0 | HIGH und CRITICAL, einschliesslich noch nicht behobener Befunde; ausschliesslich die unten dokumentierten PostgreSQL-`gosu`-Befunde sind ausgenommen |
| ZAP | 2.17.0 | MEDIUM und HIGH; Scannerfehler, unvollständiger Scan und Timeout blockieren |
| actionlint | 1.7.12 | Fehler in Workflow, Expressions oder Shell-Aufrufen |

Die Security-Stufe verwendet ausschliesslich Open-Source-Scanner: **Bandit für
SAST**, **ZAP für DAST**, pip-audit für Abhängigkeiten, Gitleaks für Geheimnisse
und Trivy für Container. Bandit, ZAP, pip-audit und Trivy stehen unter Apache-2.0,
Gitleaks unter MIT. Die Prüfungen laufen im CI-Runner beziehungsweise dessen
Containern; sie benötigen keinen kostenpflichtigen Scan-Dienst.
Lizenzquellen:
[Bandit](https://github.com/PyCQA/bandit/blob/main/LICENSE),
[ZAP](https://github.com/zaproxy/zaproxy/blob/main/LICENSE),
[pip-audit](https://github.com/pypa/pip-audit/blob/main/LICENSE),
[Gitleaks](https://github.com/gitleaks/gitleaks/blob/master/LICENSE),
[Trivy](https://github.com/aquasecurity/trivy/blob/main/LICENSE).

Scanner-Binaries werden aus offiziellen Releases geladen, gegen festgelegte
SHA-256-Prüfsummen geprüft und einzeln aus dem Archiv kopiert. Es werden keine
entfernten Installationsskripte ausgeführt. Alle externen Actions sind auf die
vollständigen, beim Hersteller verifizierten Commit-SHAs festgelegt; Versionen
stehen daneben als Kommentar. Prüfsummen und Quellen stehen in
`scripts/ci/install_scanners.py` und im Workflow.

Ein fehlender, ungültiger oder unvollständiger Scannerbericht sowie ein
Nichtnull-Exitcode blockiert. Auch nach einem einzelnen Scanfehler werden die
übrigen Scanner ausgeführt. Roh-Ausgaben von Secret-Scans und gefundene
Quelltextausschnitte gelangen nicht in die Berichtartefakte. Scannerfehler werden
mit Exitcode und einer festen, nicht vertraulichen Fehlerkategorie dokumentiert.
Es gibt keine pauschalen Ausnahmen oder `ignore-unfixed`-Einstellung. Die
ausdrücklich freigegebene Ausnahme für PostgreSQL ist auf den festgelegten
Image-Digest, `gosu` und die einzeln benannten Schwachstellen beschränkt. Sie
läuft am **31.12.2026** aus; dieses technische Prüfdatum ist kein angenommener
Abgabetermin. Andere oder neue Befunde, ein anderer Image-Digest sowie
Scannerfehler bleiben blockierend. Akzeptierte Befunde bleiben im Bericht
sichtbar. Weitere Ausnahmen benötigen einen eigenen begründeten und befristeten
Benutzerentscheid.

Die vollständige CVE-Liste steht in
[`deploy/security/postgres-gosu.trivyignore.yaml`](../deploy/security/postgres-gosu.trivyignore.yaml).
Die nativen Trivy-Regeln verlangen gleichzeitig den Pfad `usr/local/bin/gosu`
und `pkg:golang/stdlib@v1.24.6`; die Pipeline aktiviert diese Datei nur für den
oben festgelegten PostgreSQL-Digest. Für App, Nginx und andere DB-Digests wird
keine Ausnahme geladen. `--show-suppressed` hält akzeptierte Befunde im
Trivy-JSON sichtbar; die Security-Zusammenfassung nennt die angewandte Ausnahme.
Ab **31.12.2026, 00:00 UTC** greift die Ausnahme nicht mehr. Das ist die von
Trivy ausgewertete Prüffrist; eine Verlängerung erfolgt nicht automatisch.
[Quelle: Trivy-Filterregeln](https://trivy.dev/docs/latest/configuration/filtering/#trivyignoreyaml).

Offizielle Grundlagen, geprüft am 18.09.2026:
[GitHub Secure use](https://docs.github.com/en/actions/reference/security/secure-use),
[GitHub Environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments),
[uv in Docker](https://docs.astral.sh/uv/guides/integration/docker/),
[pip-audit](https://github.com/pypa/pip-audit),
[Bandit](https://bandit.readthedocs.io/en/latest/),
[Gitleaks](https://github.com/gitleaks/gitleaks),
[Trivy](https://trivy.dev/docs/v0.74/),
[actionlint](https://github.com/rhysd/actionlint),
[Ansible Compose-Modul](https://docs.ansible.com/projects/ansible/latest/collections/community/docker/docker_compose_v2_module.html).

## Aktiver DAST-Scan mit ZAP

Auf ausdrücklichen Benutzerentscheid läuft ZAP aktiv gegen eine kurzlebige
CI-Instanz. `scripts/ci/dast.py` startet dieselben verifizierten App-, Nginx- und
PostgreSQL-Archive wie der Build-Smoke-Test. Beide verwenden
`scripts/ci/isolated_runtime.py`. Es gibt keine frei konfigurierbare Scan-URL:
das Ziel ist ausschliesslich `https://nginx:8443` im eigenen internen Docker-Netz.
Die Instanz veröffentlicht keine Hostports, enthält eine frische temporäre
Datenbank und verwendet Zufallsgeheimnisse. ZAP erhält weder Docker-Socket noch
Produktionszugänge. Das Testnetz erlaubt keine externe Internetverbindung.

Das offizielle Scanner-Image ist festgelegt auf
`ghcr.io/zaproxy/zaproxy:2.17.0@sha256:781a2bdaea47324e7bab583e2263f21d257b0aee61ed51521a5be45f5f5081ef`.
Die enthaltenen Add-ons werden während des Laufs nicht automatisch aktualisiert.
Ein Update dieses Pins erfordert erneute Prüfung des Plans und der Scanberichte.

Der Automation-Framework-Plan fordert die Startseite, `/health/ready` und
`/static/app.css` ausdrücklich mit erwartetem HTTP 200 an. Anschliessend folgen
Spider, aktiver Scan und das vollständige Abarbeiten der passiven Scan-Warteschlange.
Statistikprüfungen verlangen tatsächlich gefundene URLs sowie einen gestarteten
und abgeschlossenen aktiven Scan ohne vorzeitigen Abbruch. Ein äusseres Limit
von 20 Minuten bricht als Fehler ab; es erzeugt keinen grünen Teilscan.

Die Formularprüfung verwendet sitzungsgebundene CSRF-Aktualisierung und eine
eng begrenzte Normalisierung der zeitabhängigen CSRF-Metadaten für SQL-Vergleiche.
Erfolgreiche POST-Prüfungen aller vier Benutzerformulare sowie tatsächlich
ausgeführte und abgeschlossene DOM-XSS-Browserprüfungen sind verpflichtend.
Firefox erhält einen schreibbaren temporären Cache; ein übersprungener Browser
blockiert auch bei Scanner-Exitcode 0. Ursachen, Grenzen und Regressionstests:
[DAST-Nachweis](dast.md).

MEDIUM- und HIGH-Befunde blockieren unabhängig vom Konfidenzwert; LOW und INFO
bleiben sichtbar. Scanner-Exitcodes, ungültige oder fehlende Berichte, falscher
Zielbereich und Aufräumfehler blockieren ebenfalls. Die native Fehlerauswertung
des Automation Frameworks bleibt erhalten. Der DAST-Schritt läuft nach erfolgreicher
Scanner-/Archivvorbereitung auch dann, wenn ein anderer Security-Scan scheitert;
der Security-Job bleibt in diesem Fall insgesamt fehlgeschlagen.

`reports/security/zap.json` enthält Commit, geprüfte Image-Kombination,
Scanner-Digest und bereinigte Befunde mit Regel-ID, Risikostufe, Konfidenz und
Anzahl. Regeln lassen sich unter `https://www.zaproxy.org/docs/alerts/<Regel-ID>/`
nachlesen. HTTP-Antworten, Angriffspayloads, Cookies und rohe Scannerlogs werden
nicht als Workflow-Artefakte veröffentlicht. Temporäre Scanberichte, Container
und Netze werden nach dem Lauf entfernt, auch bei einem Scanfehler.
Zusätzlich enthält `coverage` die Anzahl der SQL-Testanfragen und den
Abschlussnachweis der DOM-XSS-Regel, ohne vertrauliche Request-/Response-Daten.

Lokal mit bereits gebauten Archiven ausführen:

```bash
uv run --locked python scripts/ci/dast.py --commit "$(git rev-parse HEAD)"
```

T02 prüft damit die öffentlichen Seiten des Grundgerüsts. Mit T05 müssen
Testbenutzer und nachgewiesene authentifizierte Browser-Abdeckung ergänzt werden,
mit T09 die authentifizierte API-Abdeckung. Eigentums- und Fachlogiktests bleiben
zusätzlich erforderlich. Ein automatisierter aktiver DAST-Scan ersetzt keinen
vollständigen manuellen Pentest.

Der erste reale Scan fand fehlende CSP- und Clickjacking-Header (ZAP-Regeln
10038 und 10020). Nginx liefert nun in Entwicklung und Produktion
`X-Frame-Options: DENY` und folgende Content Security Policy, auch auf
Fehlerantworten:

```text
default-src 'none'; style-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'
```

Die bestehende externe CSS-Datei bleibt erlaubt; Inline-Skripte oder
Inline-Styles benötigen keine Ausnahme. Spätere Oberflächenänderungen müssen
mit dieser Policy und dem DAST-Scan geprüft werden.

Grundlagen: [ZAP Automation Framework](https://www.zaproxy.org/docs/automate/automation-framework/),
[aktiver Scan](https://www.zaproxy.org/docs/desktop/addons/automation-framework/job-ascan/),
[Statistiktests](https://www.zaproxy.org/docs/desktop/addons/automation-framework/test-stats/),
[ZAP-Quellcode und Lizenz](https://github.com/zaproxy/zaproxy).

## Architektur und Bereitschaft

Die bestehenden acht Komponenten bleiben getrennt: `app.web`, `app.api`,
`app.services.users`, `devices`, `repairs`, `parts`, `costs` und `app.data`.
`scripts/check_architecture.py` prüft die erlaubten Kanten und negative Tests
belegen unter anderem, dass direkte/relative ORM-Imports, Servicezyklen,
Sammelimporte und technische Umwege abgewiesen werden. Die Fachfunktionen und
ORM-Rückgaben selbst werden erst mit T04–T10 implementiert und geprüft.

Die technische Ausnahme ist eng begrenzt:
`app.web.routes.health` → `app.diagnostics.check_readiness` →
`app.data.health.database_ready`. Nur der Datenzugriff führt SQL aus.
`GET /health/ready` liefert nach erfolgreicher PostgreSQL-Abfrage
`200 {"status":"ready"}`, andernfalls `503 {"status":"unavailable"}` ohne
Verbindungsdaten. Der Start führt keine Schemaänderungen aus. `GET /` zeigt den
aktuellen Grundgerüststand; eine fachliche API ist noch nicht implementiert.

`deploy/capabilities.json` erklärt Schema und authentifizierte API in T02 als
noch nicht vorhanden. Der CI-Test gleicht diese Angaben mit tatsächlichen
Migrationsdateien und registrierten Routen ab. Ab T04 werden Migration einer
leeren Datenbank und Schemaabgleich verpflichtend; ab T09 ist der authentifizierte
API-Smoke-Test verpflichtend. Die Datei ist kein beliebiger Schalter zum
Überspringen bereits vorhandener Funktionen.

## GitHub-Einrichtung

Das Repository ist öffentlich. Die lesende API-Prüfung zeigte am 18.09.2026
keine Environments und keine Rulesets. Klassischer Branchschutz und
Actions-Berechtigungen waren ohne Authentifizierung nicht einsehbar. Das ist
kein Beleg, dass sämtliche Schutzmechanismen fehlen.

Die Konfiguration erfolgt direkt im GitHub-Repository unter **Settings →
Environments → production**:

1. Die Environment `production` anlegen, sofern sie noch fehlt.
2. Unter **Deployment branches and tags → Selected branches and tags** nur die
   verwendeten Release-Tags zulassen; eine vorhandene Branch-Regel `main` entfernen.
   Beispielsweise `*` für einfache Tagnamen
   und bei Bedarf `releases/*` für entsprechende Tags mit Schrägstrich.
   Alle Branches bleiben für Deployments ausgeschlossen. Tag-Erstellung und -Änderung über
   Repository-Regeln auf vertrauenswürdige Verantwortliche begrenzen.
   Keine zusätzliche manuelle Freigabe ist vorgesehen.
3. Die folgenden nicht geheimen Werte unter **Environment variables** eintragen.
4. SSH-Passwort und weitere Zugangsdaten unter **Environment secrets**
   eintragen. Der Deploy-Job liest diese über `vars.*` beziehungsweise `secrets.*` und übergibt
   sie an Ansible. Für den regulären Actions-Lauf ist keine lokale `.env` oder
   manuell erstellte `release.json` nötig.

| Environment variable | Bedeutung / Standard bei fehlendem Eintrag |
| --- | --- |
| `DEPLOY_HOST` | Erforderlich: Hostname oder IP des Produktionshosts |
| `DEPLOY_PORT` | SSH-Port; Standard `22` |
| `DEPLOY_USER` | Erforderlich: vorhandener SSH-Benutzer der VM, dessen Passwort hinterlegt wird |
| `PUBLIC_URL` | `https://lab19.ifalabs.org` (ohne abschliessenden Schrägstrich) |
| `MAIL_SERVER` | SMTP-Host für Bestätigungsmails; erforderlich ab T04 |
| `MAIL_PORT` | SMTP-Port des Anbieters, z.B. `587` |
| `MAIL_DEFAULT_SENDER` | Beim Anbieter freigegebene Absenderadresse |
| `MAIL_USE_TLS` | STARTTLS; Standard `true` |
| `MAIL_USE_SSL` | Implizites TLS; Standard `false`; für Port 465 meist `true` und USE_TLS=false |
| `ACME_EMAIL` | Erforderlich: eigene gültige Kontaktadresse für Let’s Encrypt |
| `POSTGRES_DB` | Datenbankname; Standard `repairhub` |
| `POSTGRES_USER` | Datenbankbenutzer; Standard `repairhub` |

| Environment secret | Inhalt |
| --- | --- |
| `DEPLOY_SSH_PASSWORD` | SSH-Anmeldepasswort des vorhandenen Benutzers aus `DEPLOY_USER` |
| `DEPLOY_SSH_KNOWN_HOSTS` | Vorab geprüfte `known_hosts`-Zeile(n) für den Zielhost; bei abweichendem SSH-Port mit `[host]:port` |
| `MAIL_USERNAME` | SMTP-Anmeldename |
| `MAIL_PASSWORD` | SMTP-Passwort oder App-Passwort des Anbieters |
| `SECRET_KEY` | Langer zufälliger Anwendungsschlüssel |
| `POSTGRES_PASSWORD` | Datenbankpasswort; `DATABASE_URL` wird daraus mit korrekt kodierten Sonderzeichen erzeugt |
| `DEPLOY_BECOME_PASSWORD` | sudo-Passwort des Deployment-Benutzers, falls sudo eines verlangt; bei root oder passwortlosem sudo weglassen |
| `GHCR_READ_USERNAME` | Nur bei privatem App-Image: Benutzer mit Registry-Lesezugriff |
| `GHCR_READ_TOKEN` | Nur bei privatem App-Image: zugehöriger Token mit Leserechten auf die benötigten Pakete |

Zertifikat und privater TLS-Schlüssel entstehen auf dem Host; die bisherigen
Secrets `TLS_CERTIFICATE` und `TLS_PRIVATE_KEY` entfallen.
Das SSH-Passwort unverändert ohne zusätzliche Anführungszeichen eintragen;
Zeilenumbrüche und NUL-Zeichen werden abgewiesen. Geheimnisse gehören in
**Secrets**: GitHub-Variables werden in Ausgaben standardmässig nicht maskiert.
[Quellen: GitHub-Environment einrichten](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments),
[Variables und Secrets](https://docs.github.com/en/actions/concepts/workflows-and-actions/variables).

Die VM verwendet gemäss Benutzerentscheid SSH-Passwortauthentifizierung.
`DEPLOY_SSH_PRIVATE_KEY` wird nicht mehr verwendet. Der Runner schreibt das
Passwort als `ansible_password` in die geschützte temporäre `vars.json` und
übergibt nur deren Pfad an Ansible. Ansible-Core 2.21.4 verwendet dafür den
eingebauten Mechanismus `ssh_askpass`; ein zusätzliches `sshpass`-Paket ist
nicht erforderlich. SSH-Passwörter erscheinen weder als Kommandoargument noch
in der Anwendungs-Konfiguration.
[Quelle: Ansible-SSH-Verbindung](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/ssh_connection.html).

`DEPLOY_SSH_KNOWN_HOSTS` bleibt erforderlich: Der Hostschlüssel identifiziert
den **Server**, während das Passwort den **Benutzer** authentifiziert. Auch bei
Passwortanmeldung prüft SSH die Serveridentität mit `StrictHostKeyChecking=yes`.

Die Pipeline erstellt die geschützten Ansible-Eingaben zur Laufzeit und entfernt
die temporären Dateien auch nach Fehlern. Auf dem Zielhost verwaltet Ansible
die benötigten geschützten Laufzeitdateien. Image-Digests und Commit werden aus
dem geprüften Release übernommen und müssen nicht als Environment-Werte gepflegt
werden. Die Infrastruktur-Pins bleiben in `deploy/infrastructure.json`.

`PUBLIC_URL` ist eine HTTPS-Origin ohne abschliessenden Schrägstrich. Der
Hostschlüssel muss vorab über einen vertrauenswürdigen Kanal geprüft werden;
ein unbestätigtes `ssh-keyscan` während des Deployments genügt nicht.
Der Host erhält nur Registry-Leserechte. Schreibrechte verwendet allein der
Publish-Job über `GITHUB_TOKEN`.

Für `main` sind die Checks **Test**, **Build** und **Security** als erforderlich
zu konfigurieren, mit passenden Regeln gegen unkontrollierte Direkt-Pushes.
GitHub unterstützt Environments und Branchschutz bei öffentlichen Repositorys
auch in den entsprechenden kostenlosen Angeboten; die konkrete Einstellung und
Berechtigung des Eigentümers muss bei Einrichtung geprüft werden. Es wird keine
zusätzliche manuelle Freigabepflicht eingeführt. Die lokale Implementierung
behauptet keine bereits eingerichteten Remote-Regeln.

## TLS automatisch ausstellen und erneuern

Für `lab19.ifalabs.org` besteht gemäss Benutzerangabe noch kein Zertifikat.
Nach `bootstrap.yml` stellt `deploy.yml` das erste öffentlich vertrauenswürdige
Zertifikat über Let’s Encrypt aus, bevor Nginx startet. Voraussetzungen:

- DNS-A und gegebenenfalls AAAA zeigen auf die tatsächlich erreichbare VM.
- TCP 80 ist vom Internet bis zur VM freigegeben und dort nicht durch einen
  anderen Dienst belegt; TCP 443 ist für die Anwendung freigegeben.
- Ausgehendes HTTPS zur ACME-API ist möglich.
- `PUBLIC_URL=https://lab19.ifalabs.org` und eine eigene `ACME_EMAIL` sind im
  GitHub-Environment `production` eingetragen. Die Ausstellung verwendet die
  Let’s-Encrypt-Nutzungsbedingungen (`--agree-tos`).
- Der Deployment-Benutzer darf die ACME-Tasks über sudo ausführen; falls nötig
  liegt dessen sudo-Passwort in `DEPLOY_BECOME_PASSWORD`.

Bootstrap installiert auf Debian 12 `certbot=2.1.0-4`, auf Ubuntu 24.04
`certbot=2.9.0-1` (dort muss Universe verfügbar sein), den Verwaltungshelfer
und `repairhub-acme.timer`.
Certbot nutzt HTTP-01 im Standalone-Modus: Port 80 wird nur während der
Validierung belegt und verarbeitet keine Anmeldungen. Nginx bleibt auf Port 443;
es gibt weiterhin nur drei dauerhafte Compose-Dienste und ein veröffentlichtes
App-Image. Zertifikat, Konto und Schlüssel bleiben auf der VM.
[Certbot Standalone und Erneuerung](https://eff-certbot.readthedocs.io/en/stable/using.html),
[HTTP-01 benötigt Port 80](https://letsencrypt.org/docs/challenge-types/),
[Debian-Paketversion](https://packages.debian.org/bookworm/certbot),
[Ubuntu-Paketversion](https://packages.ubuntu.com/noble/certbot).

Jedes Deployment prüft mit `--keep-until-expiring`, ob Ausstellung oder
Erneuerung nötig ist. Zusätzlich prüft der systemd-Timer zweimal täglich mit
zufälliger Verzögerung; Releases sind für die Erneuerung nicht erforderlich.
Der allgemeine Certbot-Timer wird deaktiviert, damit alle Läufe dieselbe
Deployment-Sperre respektieren. Ein Timerlauf bei belegter Sperre wartet auf
seinen nächsten Termin. Läuft die Erneuerung bereits, schlägt der parallele
Deployment-Sperrerwerb fehl; den Deployment-Lauf anschliessend wiederholen.

Vor der Aktivierung prüft der Helfer Domain, Gültigkeit und Schlüsselpaar.
Er veröffentlicht das Paar gemeinsam über einen atomaren Verzeichnislink,
prüft die Nginx-Konfiguration und lädt einen laufenden Nginx neu. Unveränderte
Zertifikate lösen nach erfolgreicher Aktivierung keinen weiteren Reload aus.
Ein fehlgeschlagener Reload wird beim nächsten Lauf erneut versucht. ACME-
oder Reload-Fehler brechen das Deployment ab beziehungsweise markieren den
systemd-Dienst als fehlgeschlagen. Diagnose: `sudo journalctl -u repairhub-acme`
und geschützte Certbot-Logs unter `/var/log/letsencrypt`.

Zertifikatserneuerungen verändern den Infrastruktur-Fingerprint nicht und
lösen weder DB-Neuerstellung noch App-Rollback aus. ACME-Konfiguration bleibt
Teil des Infrastrukturstands. Nach erfolgreichem Erststart beziehungsweise
Infrastrukturwartung vermerkt Ansible die bereits geladene Zertifikatsgeneration.
Der nächste identische Release oder Timerlauf lädt Nginx deshalb nicht erneut.
Zertifikate werden nicht mit jedem Release zwangsweise neu ausgestellt.
Manuelle Prüfung: `sudo systemctl start repairhub-acme.service`; Timerstatus:
`systemctl list-timers repairhub-acme.timer`.

Nur die isolierte Deployment-Fixture nutzt ausdrücklich
`repairhub_tls_mode: provided` mit ihrer lokalen Test-CA. Ein echtes Deployment
und eine öffentliche ACME-Ausstellung sind bisher nicht nachgewiesen.

## Hostvorbereitung und Ansible-Eingaben

Die Produktions-VM verwendet gemäss Benutzerangabe Debian 12 (Bookworm).
Bootstrap unterstützt Debian 12 sowie Ubuntu 24.04 LTS, jeweils auf amd64.
Ansible prüft die Architektur vor der Installation. Benötigt werden SSH, Python 3
mit `python3-apt`, ein separat geprüfter Hostschlüssel und ein administrativer
Zugang für die Hostvorbereitung. Docker/Compose kommen aus der offiziellen
Docker-Paketquelle; konkrete Versionen stehen in
`roles/docker_host/defaults/main.yml`, der Schlüsselhash in
`roles/docker_host/tasks/main.yml`. Betrieb und CI benötigen Compose
mindestens 2.30.0 wegen `env_file.format: raw`.
[Docker auf Debian](https://docs.docker.com/engine/install/debian/),
[Docker auf Ubuntu](https://docs.docker.com/engine/install/ubuntu/).

`bootstrap.yml` installiert Docker/Compose und erstellt das geschützte
Installationsverzeichnis für den bereits vorhandenen Benutzer aus `DEPLOY_USER`.
Es prüft zuerst, ob dieses Konto existiert, und ergänzt dessen Docker-Gruppe.
Passwort, Passwortsperre, Shell und vorhandene SSH-Schlüssel werden dabei nicht
geändert. Die Docker-Gruppe verleiht weitreichende Hostrechte; sie wird nur
dem dafür vorgesehenen Zugang gegeben. Nur die ACME-Konfiguration und
Zertifikatsverwaltung benötigen beim regulären Deployment `become`; die
Compose-Auslieferung läuft weiterhin als Deployment-Benutzer. Neue Cloud-Server
werden nicht automatisch angelegt.

Das einzige Betriebsinventory ist `inventories/production/hosts.yml`.
Host, SSH-Port und Benutzer stammen
aus `REPAIRHUB_DEPLOY_HOST`, `REPAIRHUB_DEPLOY_PORT` und `REPAIRHUB_DEPLOY_USER`.
Der Workflow setzt diese aus den Variables der Environment `production`.
`tests/deployment/inventory.yml` gehört ausschliesslich zur lokalen Fixture.
Installationspfad und weitere nicht geheime Werte stehen in `group_vars/all.yml`
beziehungsweise den Rollendefaults und können im Inventory überschrieben werden.

Aus dem Repository-Stamm:

```bash
uv sync --locked --group ci
export ANSIBLE_CONFIG="$PWD/deploy/ansible/ansible.cfg"
uv run --locked --group ci python -m scripts.ci.install_collections
uv run --locked --group ci ansible-lint deploy/ansible
uv run --locked --group ci ansible-playbook -i deploy/ansible/inventories/production/hosts.yml deploy/ansible/deploy.yml --syntax-check
```

Die Pipeline erzeugt temporäre Dateien mit 0600 und ein Verzeichnis mit 0700.
Ansible übernimmt das App-Image sowie Infrastruktur-Pins aus der gemeinsamen
Datei, Datenbank-Kompatibilitätsvertrag, Commit,
monotone Release-Sequenz, HTTPS-URL, Laufzeitkonfiguration und ACME-Kontaktadresse.
Für die einmalige Hostvorbereitung mit dem bestehenden VM-Benutzer sind
`REPAIRHUB_DEPLOY_HOST`, `REPAIRHUB_DEPLOY_USER` und gegebenenfalls
`REPAIRHUB_DEPLOY_PORT` lokal zu setzen. `ANSIBLE_SSH_COMMON_ARGS` muss auf eine
vorab geprüfte `known_hosts`-Datei verweisen, beispielsweise mit
`-o StrictHostKeyChecking=yes -o UserKnownHostsFile=/geschuetzt/known_hosts`.
Der folgende Bootstrap-Aufruf fragt das SSH-Passwort und das Passwort für
`sudo` interaktiv ab; sie gelangen dadurch weder ins Repository noch in die
Shell-History. Für `root` oder passwortloses `sudo` kann `--ask-become-pass`
entfallen. Spätere manuelle Releases verwenden dieselben Playbooks mit einer
geschützten JSON-Variablendatei einschliesslich `ansible_password`:

```bash
uv run --locked --group ci ansible-playbook -i deploy/ansible/inventories/production/hosts.yml deploy/ansible/bootstrap.yml --ask-pass --ask-become-pass
uv run --locked --group ci ansible-playbook -i deploy/ansible/inventories/production/hosts.yml deploy/ansible/deploy.yml --extra-vars @/geschuetzt/release.json
# Optionaler reiner Infrastrukturabgleich mit dem laufenden App-Digest:
uv run --locked --group ci ansible-playbook -i deploy/ansible/inventories/production/hosts.yml deploy/ansible/infrastructure.yml --extra-vars @/geschuetzt/release.json
```

Bootstrap benötigt kein Benutzerschlüsselpaar. `repairhub_deploy_user` bezeichnet
das bestehende Konto und folgt dem konfigurierten Deployment-Benutzer. Bei
separatem administrativem SSH-Zugang kann `ansible_user` für den Bootstrap
überschrieben werden, während `repairhub_deploy_user` das Zielkonto bezeichnet.
Release-Variablen heissen
`repairhub_app_image`, `repairhub_release_commit`,
`repairhub_release_sequence`, `repairhub_public_url`, `repairhub_runtime_env`,
`repairhub_database_env` und `repairhub_acme_email`; Produktion verwendet
`repairhub_tls_mode: acme`. Falls sudo ein Passwort verlangt, enthält die
geschützte Datei zusätzlich `ansible_become_password`. Nur die lokale Fixture
verwendet `repairhub_tls_mode: provided` mit `repairhub_tls_certificate` und
`repairhub_tls_private_key`. Infrastrukturwerte werden aus
`repairhub_infrastructure_file` gelesen, standardmässig
`deploy/infrastructure.json` im ausgecheckten Repository. App- und
Datenbank-Umgebungsdateien bleiben getrennt. Der vertrauenswürdige
Test-CA-Pfad kann als `repairhub_smoke_ca_path` angegeben werden; die externe
TLS-Prüfung wird dadurch nicht deaktiviert. Die ausführbaren Aufrufe und deren
konkrete Ergebnisse stehen im separaten T02-Prüfnachweis.

## Auslieferung, Wiederholung und Fehlerbehandlung

Idempotenz bezieht sich auf denselben Image-Digest und dieselbe Konfiguration:
Ein identischer erfolgreicher Release erzeugt keine Konfigurationsänderungen,
keine erneute statische Extraktion und keine Container-Neustarts. Ein neuer
Workflow-Lauf mit höherer Sequenz aktualisiert die Laufmetadaten, ohne App,
Nginx oder PostgreSQL neu zu starten. Bereitschafts- und HTTPS-Prüfungen laufen
weiterhin. Eine tatsächlich fällige Zertifikatserneuerung ist eine beabsichtigte
Änderung und lädt Nginx neu; unveränderte Zertifikate tun dies nicht.

Ein fehlgeschlagener Lauf entfernt seine Hostsperre und temporäre Zugangsdaten.
Nach Korrektur kann derselbe beziehungsweise ein neuerer Lauf wiederholt werden;
ältere Sequenzen werden weiterhin abgewiesen. Vorhandene Datenvolumes werden
nicht gelöscht. Die konkreten Wiederholungs- und Fehlerprüfungen stehen in
[t02-validation.md](t02-validation.md).

Der Deploy-Job führt vor `deploy.yml` automatisch `bootstrap.yml` aus. Dieser
wiederholbare Schritt stellt Docker/Compose, Verzeichnisse, Docker-Gruppenzugang,
Certbot und den Erneuerungstimer bereit. Er nutzt dieselben geschützten SSH-/sudo-
Eingaben und läuft nur im freigegebenen Release-/Tag-Deployment. Bereits
vorhandene Ressourcen werden mit `state: present` beziehungsweise `started`
abgeglichen; kein pauschaler Dienstneustart oder Löschen von Datenvolumes.

Bootstrap prüft die Plattform vor Paketänderungen. Unterstützt ist derzeit
Debian 12 oder Ubuntu 24.04 auf amd64; andere Plattformen werden mit ihrer erkannten Version
abgewiesen, bis passende Paketquellen und Versionen ergänzt sind. Ein fehlendes
sudo-Passwort muss als `DEPLOY_BECOME_PASSWORD` hinterlegt werden, sofern der
Benutzer sudo nicht passwortlos verwenden darf. Scheitert Bootstrap, wird das
App-Deployment nicht ausgeführt und die temporären Eingaben werden entfernt.


Der Deploy-Job verwendet die feste Gruppe `repairhub-deploy-production` mit
`cancel-in-progress: false`. Vor der
Auslieferung muss der Commit weiterhin der Spitze von `main` entsprechen; bei
Tag-Läufen muss auch der Tag weiterhin auf genau diesen Commit zeigen. Zusätzlich
sichert Ansible eine monotone Sequenz in `highwater.json`; ältere wartende Läufe
werden auch nach einem neueren fehlgeschlagenen Deployment abgewiesen.
Eine atomare Hostsperre schützt auch manuelle Playbook-Aufrufe.

Der Host hält ein stabiles Infrastruktur-Verzeichnis für das Compose-Projekt,
Nginx-Konfiguration, TLS und Datenbank-Konfiguration. App-Konfiguration und
statische Dateien sind releasegebunden; `www/current` verweist auf die aktive
statische Version. `current.json` und `previous.json` sichern den erfolgreichen
Stand und seinen Vorgänger. Gleiche Eingaben ergeben denselben Release-Pfad.
Normale Updates ändern den App-Dienst und den Asset-Verweis; unveränderte
Nginx-/Datenbankcontainer bleiben bestehen. Jeder Deploy gleicht auch diese
Dienste und die Konfigurationsdateien mit dem freigegebenen Sollzustand ab.
Die Reihenfolge bleibt Image-Pull → Datenbankbereitschaft → erforderliche
Sicherung/Migration → App/Assets → externe HTTPS-/gegebenenfalls API-Prüfung.

Der Datenbank-Kompatibilitätsvertrag trennt reine Release-Metadatenänderungen
von Änderungen an PostgreSQL-Version, Basis oder Datenlayout. Ein geänderter
Vertrag wird im normalen Deployment abgewiesen und benötigt einen separat
geprüften Datenbank-Wartungsweg. Insbesondere darf ein bestehendes Debian-Volume
nicht ohne geprüfte Übernahme an die Alpine-Basis angehängt werden.

Ab vorhandenem Schema sind eine ausdrückliche Entscheidung
`repairhub_migration_mode=compatible` oder `maintenance` und ein Backupziel
`repairhub_backup_fetch_dir` ausserhalb des Hosts erforderlich. Der neue
App-Container führt die Migration einmalig aus; Alembic verhindert erneutes
fachliches Anwenden vorhandener Revisionen. Ein flüchtiger Actions-Runner allein
ist keine dauerhafte Offhost-Sicherung. Die Aufbewahrung und ihre Grenzen beschreibt die [Betriebsanleitung](operations.md).
Gemäss T11-Benutzerentscheidung wird keine tatsächliche Datenbankwiederherstellung
durchgeführt; sie ist nicht als bestanden anzusehen.

Bei fehlgeschlagener App-Abnahme stellt Ansible das vorherige App-Image samt
App-Konfiguration und statischen Dateien nur bei unveränderter Infrastruktur
und kompatiblem Schema wieder her und prüft sie erneut. Ein fehlgeschlagener
Infrastruktur-Wartungslauf löst kein automatisches Infrastruktur-/DB-Downgrade aus.
Der neue Release bleibt
auch nach erfolgreichem Rollback fehlgeschlagen. Es gibt weder einen automatischen
Datenbank-Downgrade noch ein blindes Restore über neuere Nutzerdaten.
Notfallausführung verwendet dieselbe Wiederherstellungslogik:

```bash
uv run --locked --group ci ansible-playbook -i deploy/ansible/inventories/production/hosts.yml deploy/ansible/rollback.yml --extra-vars @/geschuetzt/rollback.json
```

Dafür sind die geprüfte Bestätigung `repairhub_rollback_schema_compatible=true`
und gegebenenfalls API-Prüfzugänge nötig. Nach einem harten Controllerabbruch
kann eine Hostsperre verbleiben. Erst prüfen, ob kein Deployment mehr läuft und
welcher Stand aktiv ist; anschliessend nur das leere Sperrverzeichnis entfernen
und dasselbe Playbook erneut ausführen. Datenvolumes werden im Regelbetrieb
nicht gelöscht; `down -v` ist kein Betriebsverfahren.


### T04: E-Mail-Verifikation und Schema

Flask-Security übernimmt Registrierung, E-Mail-Bestätigung und Browsersitzungen.
`PUBLIC_URL` wird nun auch in die Anwendung übernommen und bindet externe Links
und zulässige Hostnamen an die Produktions-Origin. SMTP-Werte werden über die
bereits geschützte runtime.env ausgeliefert. Produktion erlaubt nur SMTP mit
STARTTLS oder implizitem TLS und Zertifikatsprüfung; Testpostfächer sind keine
Produktionsoption. `MAIL_USE_TLS` und `MAIL_USE_SSL` dürfen nicht beide aktiv sein.

`deploy/capabilities.json` aktiviert jetzt Migrationen. Der bestehende Ansible-
Ablauf sichert vor der Migration und führt `flask --app app db upgrade` im neuen
Image aus. Die erste Migration ergänzt Identitätstabellen ohne vorhandene Daten
zu verändern. Gleicher Release wird nicht erneut migriert. Ein Downgrade, das
Konten löschen würde, wird ausdrücklich abgewiesen.

SMTP-Zugang und Absenderfreigabe müssen beim Betreiber eingerichtet werden.
Automatisierte Mailtests versenden ausschliesslich an einen isolierten lokalen
Empfänger. Erfolgreicher SMTP-Transfer bestätigt die Annahme, nicht die Zustellung
ins externe Postfach. Für Produktion bleibt ein kontrollierter Test nach Einrichtung
und Release erforderlich. Der SSH-/TLS-/GHCR-Auslieferungsweg bleibt unverändert.

### T04: Migration und verschlüsselte Deployment-Backups

Zusätzlich ist im GitHub-Environment `production` das Secret
`BACKUP_PASSPHRASE` erforderlich: ein eigenständiger, zufälliger Wert mit mindestens
32 Zeichen ohne Zeilenumbrüche. Im Passwortmanager separat aufbewahren; ohne den
zum Backup gehörenden Wert ist keine Wiederherstellung möglich. Nicht mit
`SECRET_KEY` oder SMTP-/Datenbankpasswörtern wiederverwenden.

T04 legt ausschliesslich neue Tabellen an. `deployment_input.py` setzt deshalb
`repairhub_migration_mode=compatible`. Bei künftigen Migrationen muss diese
Kompatibilitätsentscheidung erneut geprüft werden. Ansible sichert vor Migration
mit `pg_dump` auf dem Host und lädt die Datei geschützt auf den Runner. Der Workflow
verschlüsselt vorhandene Kopien auch nach fehlgeschlagenem Deployment mit GnuPG
(AES-256), lädt ausschliesslich `.gpg` als `database-backup-…` hoch und löscht
anschliessend temporäre Klartextdateien und Zugangsdaten. Artefakte bleiben 30 Tage;
für längere Aufbewahrung herunterladen und separat sichern. Ein Runner-Ausfall vor
dem Upload kann diese externe Kopie verhindern; die Hostkopie bleibt erhalten.

Die Passphrase wird über Standard-Eingabe übergeben, nicht als Befehlsargument.
Grundlage: [GnuPG-Batch-Optionen](https://www.gnupg.org/documentation/manuals/gnupg/GPG-Esoteric-Options.html).
Wiederherstellung: Artefakt herunterladen, lokal `gpg --output database.dump --decrypt
BACKUP.dump.gpg` ausführen (Passphrase interaktiv) und das dokumentierte
[Wiederherstellungsverfahren](operations.md) beachten. Niemals ungeprüft über aktuelle Produktionsdaten schreiben.

Der lokale Test prüft Verschlüsselung und Entschlüsselung sowie Ablehnung einer
falschen Passphrase. Eine tatsächliche Datenbankwiederherstellung wurde für T11 bewusst nicht ausgeführt;
sie bleibt ungetestet. Siehe [T11-Nachweis](t11-validation.md).

T04 ändert ausserdem die Nginx-Konfiguration (Bestätigungstokens im Zugriffslog
maskieren und den Host-Port beim Weiterleiten erhalten). Auch auf einer bestehenden
T03-Installation übernimmt der normale Deploy diese Änderungen automatisch.
Die Migration wird erst mit dem neuen, migrationsfähigen App-Image ausgeführt.

### Automatischer, idempotenter Infrastrukturabgleich

Auf Benutzerwunsch übernimmt der normale `deploy.yml`-Aufruf auch Änderungen an
Compose, Nginx, TLS und den geprüften Infrastruktur-Pins. Die früher vorgeschlagene
Variable `INFRASTRUCTURE_MAINTENANCE_TAG` und der vorbereitende Wartungsschritt
entfallen. Falls die Variable bereits angelegt wurde, ist sie wirkungslos und
kann entfernt werden. Es sind keine neuen Variablen oder Secrets erforderlich.

Der gesamte Abgleich läuft unter derselben Hostsperre und der bestehenden
Workflow-Serialisierung. Ansible vergleicht Dateien und Compose-Dienste mit dem
Sollzustand, statt Änderungen lediglich anhand eines gespeicherten Fingerprints
abzuweisen. Damit werden auch manuell veränderte Dateien sowie fehlende oder
gestoppte Dienste korrigiert. Unveränderte Container werden nicht neu erstellt;
Nginx wird nur bei tatsächlich geänderter Konfiguration nach erfolgreichem
`nginx -t` neu geladen.

Die Reihenfolge bleibt kontrolliert: bisherigen Stand sichern, Infrastrukturdateien
abgleichen, gepinnte Images bereitstellen, Datenbankbereitschaft prüfen, bei Bedarf
Backup/Migration im **neuen** App-Image, App und statische Dateien aktivieren,
Nginx abgleichen und externes HTTPS prüfen. Die laufende alte App wird nicht für
Migrationen verwendet. Für den optionalen reinen `infrastructure.yml`-Aufruf mit
dem bisherigen Digest bleiben dessen gespeicherte Fähigkeiten massgeblich und
Migrationen deaktiviert; dieser Aufruf ist für normale Releases nicht nötig.

Identische Eingaben ergeben denselben Release-Pfad. Eine Wiederholung benötigt
weder erneute Migration noch Container-Neustart. Nach einem unterbrochenen
Infrastrukturabgleich kann derselbe normale Deploy erneut ausgeführt werden;
`infrastructure-pending.json` erzwingt keinen manuellen Wartungsmodus mehr.
Die ursprüngliche Infrastruktur-Sicherung bleibt erhalten. Ein fehlgeschlagener
Lauf bleibt fehlgeschlagen; App-Rollback erfolgt weiterhin nur bei kompatiblem
Schema und gleicher Infrastruktur, niemals durch blindes Datenbank-Downgrade.

Geänderte Datenbanknamen, Benutzer, Passwörter oder inkompatible Datenverträge
bleiben vor Hoständerungen gesperrt. Compose kann bestehende Datenbankzugänge
nicht durch Änderung einer Environment-Datei migrieren. Veraltete Release-Sequenzen,
Digest-Vorgaben, SSH-Hostprüfung und Geheimnisschutz bleiben ebenfalls erhalten.

Die Korrektur muss einmalig in `main` übernommen und mit einem neuen Tag/Release
veröffentlicht werden. Danach funktioniert derselbe Ablauf für weitere Releases
ohne manuelle Sonderfreigabe. Ein Retry des alten Tags v0.5 würde weiterhin den
alten Workflow und das alte Playbook verwenden. Bestehende Tags nicht verschieben.

Prüfnachweis: [Automatisches Infrastruktur-Upgrade](infrastructure-upgrade-validation.md).

## Interne Healthchecks mit öffentlichem Hostnamen

Der App-Healthcheck verbindet sich weiterhin ausschliesslich mit
`127.0.0.1:8000`, sendet jedoch den Hostnamen samt optionalem Port aus `PUBLIC_URL`
als HTTP-Host-Header. Andernfalls lehnt Flask bei aktiven `TRUSTED_HOSTS` den
lokalen Check mit HTTP 400 ab und Docker markiert eine gestartete Anwendung als
`unhealthy`. Der Check verwendet keinen Umgebungsproxy und gibt bei Fehlern
keine Konfigurationswerte aus.

Für Nginx schreibt Ansible `REPAIRHUB_HEALTHCHECK_HOST` aus `repairhub_public_url`
in die generierte `compose.env`. Auch dieser Check verbindet sich lokal und
verwendet den öffentlichen Host-Header. Es braucht kein zusätzliches
GitHub-Secret und keine neue manuell gepflegte Variable. Die externe
HTTPS-Abnahme prüft weiterhin die Zertifikatskette; der lokale Nginx-Check
prüft die Bereitschaft ohne Zertifikatsnamensprüfung für die Loopback-Adresse.

Der Build-Smoke-Test setzt nun ausdrücklich eine öffentliche Test-URL, damit
die Hostbeschränkung auch in CI aktiv ist, und führt beide internen Checks aus.
Der Regressionstest `tests/integration/app/test_healthcheck.py` prüft Domain
und Nichtstandardport sowie die fortbestehende Ablehnung fremder Hosts.

Nach einem Abbruch nach erfolgreicher Migration kann derselbe Deployment-Ablauf
mit einem korrigierten Release erneut ausgeführt werden. Alembic erkennt bereits
angewendete Revisionen. Weder Datenvolumes noch Release-Metadaten müssen dafür
manuell gelöscht werden. Eine Wiederholung des alten Tags verwendet hingegen
weiterhin das alte Image mit dem fehlerhaften Healthcheck.

Lokale Prüfung dieses Fixes: 532 Unit-Tests und zwei neue HTTP-Regressionstests
bestanden; Architekturprüfung, Ruff, Bandit für den Healthcheck und Ansible-Lint
bestanden. Produktionsimage gebaut und isoliert mit echtem PostgreSQL sowie
Nginx/TLS geprüft, einschliesslich beider interner Healthchecks mit aktivierter
Hostbeschränkung. Produktions-Compose löst den generierten Host-Header korrekt
auf. Ein vollständiger Ansible-Deployment-Lauf und die Produktionsabnahme wurden
für diesen Fix noch nicht ausgeführt.

## T09: API-Key-Abnahme

Das einzige zusätzliche GitHub-Environment-Secret ist `API_SMOKE_KEY`. Es ist
der zentrale System-Leseschlüssel für alle Reparaturfälle. Ansible übergibt ihn
als gleichnamige geschützte Runtime-Variable und prüft Liste sowie einen dort
gefundenen Fall. Leere Listen sind zulässig. Es gibt kein dediziertes Prüfkonto
und keine feste Fall-ID mehr. Die bisherigen Werte `API_SMOKE_USERNAME`,
`API_SMOKE_REPAIR_ID` und `API_SMOKE_PASSWORD` entfallen.

Schlüsseländerungen fliessen in den Release-Konfigurationsfingerprint ein.
Bei unveränderten Eingaben erfolgen keine unnötigen Neustarts; ein kompatibler
Rollback stellt Runtime und Prüfschlüssel des vorherigen Releases wieder her.
Persönliche Benutzerkeys werden nicht verändert. Details: [API](api.md).

Isolierte Image- und Deployment-Tests nutzen ausschliesslich synthetische Konten,
Beispieldaten und wegwerfbare Schlüssel.


### Vorübergehende Fehler beim Galaxy-Download

Test- und Deploy-Job installieren Collections über `scripts.ci.install_collections`.
Abgebrochene TLS-Verbindungen (z.B. `SSL: UNEXPECTED_EOF_WHILE_READING`) können
bereits während der Abhängigkeitsauflösung auftreten, bevor Anwendungstests starten.
Die Installation wird höchstens dreimal versucht, mit 5 und 15 Sekunden Pause
und maximal 180 Sekunden je Versuch. Gepinnte Versionen und TLS-Zertifikatsprüfung
bleiben erhalten. Nach drei Fehlschlägen bleibt der Job rot; weitere Stufen laufen
nicht. Ein dauerhaft nicht erreichbares Galaxy muss weiterhin behoben werden.


### Doppelte Push-/PR-Prüfungen vermeiden

`Select CI run` prüft bei Branch-Pushes über die GitHub-API, ob der Branch bereits
einen offenen PR im selben Repository besitzt. Dann übernimmt der PR-Lauf die
Merge-Prüfung; im Push-Lauf werden Test, Build und Security übersprungen. Ohne
offenen PR sowie auf `main` laufen die Prüfungen weiterhin. Releases und manuelle
Aufrufe werden nicht unterdrückt; Publish/Deploy bleiben ausschliesslich Releases
vorbehalten. Fork-PRs werden weiterhin geprüft.

GitHub erzeugt für beide Ereignisse weiterhin je einen sichtbaren Workflow-Eintrag.
Der zusätzliche Push-Eintrag führt nur die kurze Vorprüfung aus. Ein API-Fehler
lässt diese Vorprüfung fehlschlagen. Bereits laufende Prüfungen werden nicht
abgebrochen; wird ein PR erst nach der Push-Vorprüfung geöffnet, können einmalig
beide Läufe prüfen. Die Vorprüfung benötigt nur `contents: read` und
`pull-requests: read`, keine Produktions-Secrets oder zusätzlichen Actions.
Grundlagen: [Workflow-Ereignisse](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#using-multiple-events)
und [Pull-Request-Abfrage](https://docs.github.com/en/rest/pulls/pulls#list-pull-requests).


### Bestätigter Gitleaks-Fehlalarm in der Testdokumentation

Der Commit `02c3140391f1075471ab26f609d4f627d427790b` enthält in
`docs/testing.md`, Zeile 240, eine deutsche Aufzählung mit Schrägstrichen.
Die Regel `generic-api-key` deutet diese Prosa fälschlich als Zugangsschlüssel.
Der Treffer wurde geprüft: Er enthält kein Geheimnis. Die aktuelle Formulierung
ist geändert; da CI die gesamte Historie prüft, wird zusätzlich nur der genaue
Fingerprint dieses historischen Fundes in `.gitleaksignore` ausgenommen.
Andere Fundstellen, Dateien und Regeln bleiben vollständig aktiv.

Dies ist eine Korrektur eines bestätigten Fehlalarms, keine akzeptierte
Offenlegung eines Schlüssels. Bei einer späteren Historienumschreibung muss der
Fingerprint erneut geprüft werden; keine pauschale Ausnahme ergänzen.
Mechanismus: [Gitleaks-Fingerprints](https://github.com/gitleaks/gitleaks#gitleaksignore).

## K-T04: Garage und Bildsicherungen

Das Release verwendet zusätzlich das gepinnte offizielle Garage-Image. Nur die App
wird veröffentlicht. Build, isolierte Smoke-/Browser-/DAST-Prüfungen sowie Trivy
berücksichtigen Garage. Der ergänzende Rust-Quellinventar-Scan und seine Grenzen sind
in [Garage](garage.md) dokumentiert. In `production` die Secrets `GARAGE_ACCESS_KEY_ID`,
`GARAGE_SECRET_ACCESS_KEY` und `GARAGE_RPC_SECRET` ergänzen (Formate siehe dort).
Vor Migrationen werden Datenbank und unveränderliche Bildobjekte exportiert;
`.dump` und `.dump.files.tar` werden beide verschlüsselt und ausserhalb des Hosts
aufbewahrt. Wiederholte unveränderte Releases ersetzen keine laufenden Container.
