# T12 – Nachweis der Gesamtabnahme

Prüftag: **22. September 2026**. Quellstand:
`4b59e03022a3c669136ebd4499b096fcad3efcdb`.
Die Abnahme verändert keinen Anwendungscode. Zwölf nachvollziehbare Fälle mit
Voraussetzungen, Testdaten, Soll, Ist und Anforderungsbezug stehen im
[Abnahmeprotokoll](acceptance-test-protocol.md).

## Aktueller Gesamtstand statt historischer Teilnachweise

Dieser Nachweis führt T02–T10 und K-T01–K-T05 für den genannten Commit zusammen.
Ältere Taskberichte beschreiben ihren jeweiligen historischen Stand; dort noch
offene ZAP-/Release-Nachweise sind für diesen Commit durch die unten genannten
neuen Prüfungen ergänzt. T11 bleibt im ausdrücklich vereinbarten Dokumentationsumfang
abgeschlossen. Ein nicht ausgeführter Restore wird dadurch nicht zu einem bestandenen Test.

## Ausgeführte Prüfungen

| Prüfung | Ergebnis | Rohbeleg |
| --- | --- | --- |
| Python Unit | 710 bestanden, 0 fehlgeschlagen/übersprungen | `reports/t12/unit.xml` |
| PostgreSQL-Integration | 326 bestanden, 0 fehlgeschlagen/übersprungen | `reports/t12/integration.xml` |
| Browser-E2E über HTTPS | 65 bestanden, 0 fehlgeschlagen/übersprungen | `reports/t12/e2e.xml` |
| JavaScript: Frontend und ZAP-Skripte | 62 bestanden, 0 fehlgeschlagen | `reports/t12/javascript.xml` |
| Ruff und Format | bestanden | `ruff.json`, `format.log` unter `reports/t12/` |
| Migration/Deployment-Capabilities | frische DB: Upgrade und Modellabgleich bestanden | `reports/t12/capabilities.json` |
| Architektur | bestanden; Domain-Grenzen unverändert | `reports/t12/architecture.log`, Architektur-Unit-Tests |
| Actionlint | bestanden | `reports/t12/actionlint.log` |
| Ansible-Lint und vier Playbook-Syntaxprüfungen | bestanden | `reports/t12/ansible-*.log` |
| Image-Build und Archivverifikation | bestanden | `artifacts/t12/manifest.json`, `reports/t12/build.json` |
| PostgreSQL-/HTTPS-/authentifizierter API-Smoke | bestanden | `reports/build/smoke.json` |
| Dependency, Bandit, Gitleaks, Trivy | bestanden nach bestehender Scanrichtlinie | `reports/t12/security/security-summary.json` |
| Aktiver OWASP ZAP | bestanden, keine blockierenden Befunde | `reports/t12/security/zap.json` |
| PostgreSQL-Container-Neuerstellung | Daten und benanntes Volume erhalten; anschliessend HTTPS/API erfolgreich und Deploy `changed=0` | `reports/t12/persistence.json` |
| Isolierter Deployment-Erstlauf und unveränderte Wiederholung | bestanden; Wiederholung `changed=0` | `reports/t12/deployment.json` |

Alle Teststufen wurden für diese Abnahme neu ausgeführt. Integrationstests verwendeten
PostgreSQL und für Bilder einen echten isolierten Garage-Knoten. Browser, Smoke und
ZAP verwendeten dieselben geprüften Image-Archive. Weder aktive Scanner noch negative
Schreibtests liefen gegen die Produktion. Die Ansible-Fixture wird ausdrücklich als
isolierter vorbereiteter Host behandelt; ihr Alpine-Basissystem ist kein freigegebenes
Produktions-Bootstrap-Ziel. Das Produktions-Bootstrap-Playbook weist es korrekt ab.

Der vollständige isolierte Deployment-Lauf ist abgeschlossen:

| Szenario | Tatsächliches Ergebnis |
| --- | --- |
| Produktions-Bootstrap auf Alpine-Fixture | erwartete Ablehnung der nicht unterstützten Plattform; keine Änderung |
| Erstdeployment auf vorbereiteter Fixture | erfolgreich |
| Identische Wiederholung | `changed=0`, IDs/Startzeiten aller vier Container unverändert |
| App-Konfigurationsupdate | erfolgreich; Infrastrukturcontainer unverändert |
| Absichtlich falscher API-Smoke-Schlüssel nach neuem App-Konfigurationsstand | Abnahme schlägt fehl; kompatibler Vorgänger wiederhergestellt; Gesamtlauf bleibt fehlgeschlagen (`failed=1`, `rescued=1`) |
| Neuer korrekter Lauf oberhalb der Highwater-Marke | erfolgreich |
| Erneute identische Wiederholung | `changed=0`, alle vier Container unverändert |

Der Fehler wurde ausschliesslich durch einen synthetischen Schlüssel in der Fixture
provoziert. Die ursprüngliche Produktionskonfiguration wurde nicht verändert.
Der Prüfstand verwendet SSH-Schlüssel, während Produktion gemäss Konfiguration
Passwort-SSH verwendet; diese Transportvariante wird hier nicht gleichgesetzt.
Das reale Produktions-Bootstrap und Deployment sind zusätzlich durch den erfolgreichen
GitHub-Release-Lauf belegt.

## Image- und Release-Zuordnung

- Lokales geprüftes App-Image: `repairhub-app:4b59e03022a3c669136ebd4499b096fcad3efcdb`.
- Lokale Image-ID: `sha256:e0176dfa37507ee224d1a3680a1665af5fa4a132adc63f6a55189b521147699b`.
- Erfolgreicher Produktionsrelease: [v0.9](https://github.com/GojicDragan/RepairHub/releases/tag/v0.9).
- [GitHub-Release-Lauf 35771339154](https://github.com/GojicDragan/RepairHub/actions/runs/35771339154)
  gehört zu exakt demselben Commit. **Test, Build, Security, Publish und Deploy erfolgreich**;
  Jobstatus und Schritte wurden über die GitHub-API gelesen.
- Öffentlich abgefragter veröffentlichter App-Digest:
  `ghcr.io/gojicdragan/repairhub/app@sha256:ec67c16839c29906ad014ad98f718b97c9e4323453ac182893d8ce56da3fa046`.

Lokaler Build und GitHub-Build sind getrennte Builds desselben Quellstands; ihre
Image-IDs werden nicht gleichgesetzt. Der Registry-Digest wurde am Commit-Tag gelesen.
Eine unabhängige SSH-Inspektion des laufenden Produktionscontainers erfolgte nicht;
der Produktionsbezug beruht auf erfolgreichem Release-Workflow plus den folgenden
Live-Prüfungen. Für den endgültigen Auslieferungsweg prüft der Workflow selbst den
veröffentlichten Digest und übergibt ihn an Ansible.

## Lesende Produktionsabnahme

Ziel: `https://lab19.ifalabs.org`. Die öffentliche Startseite und `/health/ready`
antworteten mit HTTP 200 bei regulärer Zertifikatsprüfung. Bei der ersten Prüfung
vor dem neuen Release antwortete `/api/repairs` noch mit 404. Dieser Befund wurde
nicht als bestanden gewertet. Die Wiederholung nach `v0.9` ergab:

| Request | Tatsächliches Ergebnis |
| --- | --- |
| Liste mit bereitgestelltem Systemschlüssel | 200, korrektes JSON-Listenschema, leerer Bestand (`total=0`) |
| Liste ohne Authorization | 401 |
| Liste mit ungültigem Schlüssel | 401 |
| Unbekannte Detail-ID mit gültigem Schlüssel | 404 |
| Bereitschaftscheck | 200 |

Beleg: `reports/t12/production-api-validation.json`, Prüfuhrzeit ca. **21:50 MESZ**.
Der Schlüssel selbst und private Reparaturdaten werden nicht aufbewahrt. Weil der
Produktionsbestand leer war, gibt es keinen positiven Live-Detailabruf. Positive
Details, Kosten und Trennung zweier Benutzer sind in den isolierten Integration-/
Browserprüfungen mit echten Daten geprüft. Externe E-Mail-Zustellung und ein vollständiger
Browserablauf mit einem Produktionskonto wurden in T12 nicht neu durchgeführt;
SMTP-Annahme und Mailabläufe sind isoliert geprüft.

## Security-Ergebnis und Grenzen

ZAP 2.17.0 führte den aktiven Scan ausschliesslich im isolierten internen Testnetz aus.
Alle verpflichtenden Scannerprüfungen bestanden; fünf Hinweisgruppen mit Risikostufe 0
wurden gemeldet (Regeln 10058, 10015, 10112, 10104, 10031), keine Medium-/High-Befunde.
ZAP ersetzt keine Vollständigkeitsgarantie für alle angemeldeten Fachabläufe; diese
werden zusätzlich mit Eigentums-, CSRF-, Browser- und API-Negativtests geprüft.

Trivy meldet für das offizielle PostgreSQL-Image weiterhin **22 bereits ausdrücklich
akzeptierte `gosu`-Befunde**. Die Freigabe ist eng an Image, Paket, Pfad und einzelne
CVE-IDs gebunden und läuft am **31.12.2026, 00:00 UTC** ab. Es wurde keine neue
Ausnahme eingerichtet. «Bestanden» bedeutet Einhaltung dieser dokumentierten
Richtlinie, nicht Abwesenheit sämtlicher Schwachstellen. Siehe
[Ausnahmedatei](../deploy/security/postgres-gosu.trivyignore.yaml).

Das offizielle Garage-Scratch-Image hat kein eingebettetes Rust-Inventar. Der
zusätzliche geprüfte Source-Lockfile-Scan ist an Digest und Upstream-Commit gebunden;
seine Aussagegrenzen stehen in [Garage](garage.md). Der Bericht behauptet keine
reproduzierte eigene Binary-Übersetzung. Vorhandene DeprecationWarnings von
Flask-Security wurden im Rohbericht erhalten; sie waren keine fehlgeschlagenen Tests.

## Reproduzierbarkeit und Aufbewahrung

Die regulären Befehle stehen in [Teststufen](testing.md) und
[CI/CD](ci-cd.md). Dieser Lauf verwendete die gesperrte `.venv` aus `uv.lock` und
getrennte Verzeichnisse `artifacts/t12` / `reports/t12`. Beispiel:

```bash
uv run --locked pytest tests/unit --junitxml=reports/t12/unit.xml
# TEST_DATABASE_URL ausschliesslich auf eine isolierte PostgreSQL-Testdatenbank setzen.
uv run --locked pytest tests/integration --junitxml=reports/t12/integration.xml
node --test --test-reporter=junit tests/unit/frontend/*.test.mjs tests/unit/ci/*.test.mjs
uv run --locked python scripts/check_architecture.py
uv run --locked python scripts/ci/images.py build --directory artifacts/t12 --commit "$(git rev-parse HEAD)"
uv run --locked --group e2e pytest tests/e2e --image-artifacts artifacts/t12
uv run --locked python scripts/ci/smoke_images.py --directory artifacts/t12 --commit "$(git rev-parse HEAD)"
```

Security benötigt die versionierten Scanner; Ansible die gesperrten Collections.
Geschützte Fixture-Eingaben und Rohbackups unter `.qa/t12` gehören nicht in die Abgabe.
Sanitisierte Ergebnissummen werden zusätzlich unter `docs/validation/` versioniert;
grosse Archive und Rohberichte bleiben ausserhalb von Git. GitHub-Berichte laufen
nach ihrer konfigurierten Aufbewahrungszeit ab und müssen für eine spätere Abgabe
rechtzeitig separat gesichert werden.

## Bewusst nicht als ausgeführt ausgewiesen

- Tatsächlicher Datenbank-/Gesamtrestore: auf Benutzerwunsch nicht durchgeführt.
- Vierwöchige Betriebsverfügbarkeit: erst nach Ablauf des tatsächlichen Zeitraums belegbar.
- Neuer produktiver Testdatensatz oder aktive Produktions-Penetrationstests: nicht durchgeführt.
- Physische Löschung privater Garage-Objekte: nicht implementiert; Verweise werden entfernt.

T13 übernimmt die finale Bedienungs-/Abgabedokumentation und den Nachweis des
Betriebszeitraums. Diese Grenzen bleiben dort sichtbar.

Zur Wiederholung des isolierten Deployment-Grundablaufs mit denselben Werkzeugen:

```bash
uv run --locked python -m scripts.prepare_deployment_test \
  --directory .qa/t12-new/host --artifacts artifacts/t12 --commit "$(git rev-parse HEAD)"
source .qa/t12-new/host/controller.env
uv run --locked --group ci ansible-playbook deploy/ansible/deploy.yml \
  --extra-vars @.qa/t12-new/host/release.json
uv run --locked --group ci ansible-playbook deploy/ansible/deploy.yml \
  --extra-vars @.qa/t12-new/host/release.json
```

Die Fixture bereitet den Docker-Host bereits vor. `bootstrap.yml` darf dort keine
Debian-/Ubuntu-Installation vortäuschen. Beim zusätzlichen Fehlerpfad wurde nur in
einer neuen privaten Fixture-Eingabedatei die Release-Sequenz erhöht, eine harmlose
App-Environment-Markierung geändert und der API-Smoke-Schlüssel durch einen unabhängig
generierten falschen Wert ersetzt. Die echte Laufzeit behielt ihren bisherigen
Schlüssel. Nach dem erwarteten Fehler wurde die vorige aktive Release-Sequenz
kontrolliert und ein neuer korrekter Lauf oberhalb der Highwater-Marke ausgeführt.
Alle Fixture-Eingaben bleiben unter `.qa/` und gehören nicht ins Repository.


## Abschluss

**T12 ist im vereinbarten Umfang abgeschlossen.** Alle **1’163 automatisierten
Einzeltests** (710 Python-Unit, 326 Integration, 65 Browser, 62 JavaScript), die
zusätzlichen Prüfwerkzeuge, aktiver ZAP sowie die beschriebenen Deployment-/
Persistenzszenarien bestanden ihre jeweiligen Erwartungen. Erwartete Fehlerpfade
sind als solche ausgewiesen. Zusätzlich bestand der Secret-Scan des vollständigen
aktuellen Arbeitsstands einschliesslich der neuen Dokumentation.

Die bereinigte, versionierte Evidenz steht in [validation/t12.json](validation/t12.json):
Testzahlen und SHA-256 der JUnit-Berichte, Image-Manifest, Scannerergebnisse,
Deployment-/Persistenzergebnisse sowie öffentliche Release-/API-Nachweise.
Historische offene Release-Vermerke im lokalen Taskplan sind damit für den geprüften
Stand abgeglichen. Die ausdrücklich ausgenommenen beziehungsweise erst später
belegbaren Punkte im Abschnitt «Bewusst nicht als ausgeführt ausgewiesen» bleiben offen.
