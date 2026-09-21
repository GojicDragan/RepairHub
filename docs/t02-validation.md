# T02 – Umsetzung und Prüfnachweis

Prüfstände: **18. und 21. September 2026**. Bezug: **M07, N03–N05, N07–N10** sowie die
CI/CD- und Ansible-Vorgaben. T02 ist lokal implementiert und geprüft. Der echte
GitHub-Actions-/GHCR-Durchlauf und die Bereitstellung auf dem Produktionshost
bleiben offen. Eine dauerhafte externe Testumgebung entfällt gemäss dem neueren
Benutzerentscheid. T02 ist deshalb noch nicht vollständig
abgenommen.

Die folgenden Abschnitte dokumentieren die aufeinanderfolgenden Prüfstände.
Die ursprüngliche Veröffentlichung aller drei Images wurde durch den späteren
Benutzerentscheid zur Trennung von App- und Infrastruktur-Versionen ersetzt.
Der inzwischen ebenfalls aufgehobene eigene PostgreSQL-Build ist in älteren
Abschnitten noch als damaliger Prüfstand beschrieben; aktuell wird das offizielle
Image direkt verwendet. Die folgenden Nachträge beschreiben die jeweils neueren
Stände. Auch die frühere
Zuordnung `develop` → `test` ist durch `main` → `production` als einziges
Betriebsziel ersetzt. Frühere Digest- und Prüftabellen bleiben als historische
Nachweise erhalten.

## Aktueller Ticketstatus am 21.09.2026

**Teilweise erfüllt: implementiert und lokal geprüft, externe Abnahme offen.**
Die nachfolgenden historischen Nachweise sind keine Aussage über einen bereits
veröffentlichten oder auf der VM betriebenen Release.

| Bestandteil | Aktueller Stand |
| --- | --- |
| Test, Build und Security | Für alle Branch-Pushes sowie Pull Requests eingerichtet; getrennte Unit-/Integrations-/E2E-Prüfungen, Open-Source-Scanner und aktiver isolierter ZAP |
| Veröffentlichung und Deployment | Für main, Tag-Pushes und veröffentlichte GitHub-Releases eingerichtet; Tags müssen auf den aktuellen main-Commit zeigen |
| Images | Nur App wird gebaut/veröffentlicht; Nginx und PostgreSQL aus offiziellen gepinnten Images |
| Produktionszugang | GitHub-Environment production; SSH-Passwort plus geprüfter Hostschlüssel; optionales sudo-Passwort für ACME |
| TLS | Ansible-Erstausstellung für die konfigurierte Domain und Host-Timer zur Erneuerung vorbereitet; lab19.ifalabs.org ist die vereinbarte Domain |
| Einrichtung und Betrieb | Variables, Secrets, Environment-Regeln, Bootstrap, Release, Infrastrukturwartung und Wiederherstellung in [ci-cd.md](ci-cd.md) beschrieben |
| Testkonzept | Teststufen und Aufrufe in [testing.md](testing.md), konkrete Ergebnisse in diesem Dokument |

Für die vollständige Abnahme noch nachzuweisen:

- [ ] GitHub-Environment, Secrets/Variables und Branch-/Tagregeln tatsächlich eingerichtet und geprüft.
- [ ] Vollständiger erfolgreicher Actions-Lauf mit App-Veröffentlichung in GHCR; Run-Link, Commit und Registry-Digest dokumentiert.
- [ ] Bootstrap und Deployment auf der vorgesehenen Produktions-VM erfolgreich.
- [ ] Öffentliche Zertifikatsausstellung und HTTPS-Bereitschaft für lab19.ifalabs.org nachgewiesen; Timer auf dem Zielhost geprüft.
- [ ] Erneute Auslieferung desselben Releases und relevanter Fehlerpfad mit dem endgültigen Stand nachgewiesen.

Aktuell bestehen lokale, noch nicht eingecheckte Änderungen. Die Dateien
`docs/work-log.md` und `docs/decisions.md` bleiben auf früheren Benutzerwunsch
Git-ignoriert. Die wesentlichen T02-Nachweise und Betriebsanweisungen stehen
auch in den nicht ignorierten Dokumenten dieses Ordners; diese sind derzeit
noch unversioniert und müssen mit der Implementierung eingecheckt werden.

## Geprüfter Umfang

Das minimale Flask-Grundgerüst enthält getrennte Web-/API-Pakete, eine
Application Factory, validierte Konfiguration und einen über eine technische
Diagnoseschnittstelle gekapselten PostgreSQL-Bereitschaftstest. Die acht
Komponenten und ihre erlaubten Abhängigkeiten bleiben erhalten. Fachfunktionen,
Modelle, Migrationen und authentifizierte API sind noch nicht implementiert;
entsprechende Funktionstests gehören in T04–T10.

Die Pipeline prüft Test → Build → Security → Publish → Deploy. Der separate
Publish-Job trennt Registry-Schreibrechte von Deployment-Geheimnissen. Alle drei
Images werden einmal gebaut, als geprüfte Archive übertragen, gescannt und per
Digest über Ansible/Compose ausgerollt. `main` ist gemäss Benutzerentscheid der
Produktion und `develop` der Testumgebung zugeordnet.

## Lokale positive und negative Prüfungen

| Prüfung und Bezug | Tatsächliches Ergebnis |
| --- | --- |
| `uv run --locked pytest --junitxml=reports/test/pytest-final.xml -q`; N03, N07, N09–N10 | **103 bestanden, keine übersprungen**; echte PostgreSQL-17.11-Instanz aus dem finalen eigenen DB-Image. Keine SQLite-Ersatzdatenbank. |
| `ruff check .`, `ruff format --check .`; N10 | Erfolgreich; 36 Python-Dateien formatiert. |
| `python scripts/check_architecture.py`; N10 | Keine unerlaubten Imports; negative Tests für direkte/relative ORM-Zugriffe, Servicezyklen, dynamische Imports und technische Umwege bestanden. |
| `python -m scripts.ci.check_capabilities`; N03, N10 | Schema und authentifizierte API fehlen im T02-Grundgerüst tatsächlich. Vorhandene Migrationen/API-Routen bei deaktivierter Prüfung werden durch Tests abgewiesen. |
| `actionlint .github/workflows/ci-cd.yml`; M07, N10 | Erfolgreich. Action-Versionen sind auf vollständige überprüfte Commit-SHAs festgelegt. |
| `ansible-lint deploy/ansible`; M07, N10 | Keine Lintbefunde; Profil `production`. Syntaxprüfung von `bootstrap.yml`, `deploy.yml` und `rollback.yml` erfolgreich. |
| `python scripts/ci/images.py build --commit …`, anschliessend `verify`; M07, N10 | App-, Nginx- und DB-Target gebaut. Archivprüfsummen, Commit-/DB-Vertragslabels und OCI-Kette geprüft. Beschädigte Archive, fremde Commits und abweichende Datenbankverträge werden abgewiesen. |
| `python scripts/ci/smoke_images.py --commit …`; M07, N07, N09 | Finale archivierte Kombination gestartet: PostgreSQL und Gunicorn bereit, Nginx-HTTPS mit vollständiger Test-CA-/Hostnamenprüfung erfolgreich. |
| README-Entwicklungsstart in isolierter Arbeitskopie; M07 | `uv sync --locked --group ci` und Compose `up --build -d --wait` erfolgreich; alle drei Dienste gesund. `/`, `/health/ready` und `/static/app.css` liefern 200. Nur Nginx veröffentlicht einen Loopback-Port. |
| Produktions-Compose, Ausfall und Persistenz; N04, N07, N09 | App läuft als UID 10001; App/DB ohne Hostports. DB-Ausfall ergibt generisches 503-JSON ohne Geheimnisse. Synthetische Prüfdaten im neuen Alpine-Volume überstehen `down` ohne `-v` und anschliessende Container-Neuerstellung. |
| Separater lokaler Registry-Push und Digest-Pull; N10 | Verifiziertes Archiv geladen, mit eigenem Testtag veröffentlicht, per Digest zurückgelesen und gegen die zugehörige OCI-Identität geprüft. Kein GHCR-/GitHub-Nachweis. |

Tests verwenden Zufallsgeheimnisse in geschützten temporären Dateien. Die
PostgreSQL-Verbindung wurde über `TEST_DATABASE_URL` übergeben; Werte werden
nicht dokumentiert. Ohne diese Variable wird die Integration lokal sichtbar
übersprungen, in CI dagegen als Fehler behandelt. Das erfolgreiche Ergebnis
oben enthält die tatsächlich ausgeführte Datenbankintegration.

## Security

Ausgeführt mit den gesperrten CI-Abhängigkeiten und geprüften Scanner-Binaries:

```bash
uv run --locked --group ci python scripts/ci/security.py --binaries /tmp/repairhub-t02-scanners
```

| Scanner | Ergebnis für den finalen Stand |
| --- | --- |
| pip-audit 2.10.1, alle gesperrten Abhängigkeiten | Exit 0, kein blockierender Befund |
| Bandit 1.9.4, Python-Code | Exit 0, kein Befund ab MEDIUM-Schwere und MEDIUM-Konfidenz |
| Gitleaks 8.30.1, Git-Historie | Exit 0, kein Secret-Fund |
| Zusätzlicher Gitleaks-Scan aller versionierten und neuen, nicht ignorierten Arbeitsbaumdateien | Exit 0, kein Secret-Fund |
| Trivy 0.74.0, App-/Nginx-/DB-Archive | Alle drei Exit 0, keine HIGH-/CRITICAL-Befunde; noch nicht behobene Befunde werden nicht ausgeblendet |

Der vollständige Bericht liegt lokal in `reports/security/security-summary.json`.
Ein erster echter Scan blockierte die ursprünglichen Debian-Images und die
nicht benötigten gebündelten Werkzeuge. Nach Wechsel auf die dokumentierten
Alpine-Basen und Entfernung/Ersetzung der betroffenen Laufzeitwerkzeuge bestand
die finale Kombination. Keine Befundausnahme und keine abgeschwächte Grenze
wurde verwendet. Die technische Entscheidung steht in [ci-cd.md](ci-cd.md).

Kontrollierte Tests starten Scanner-Ersatzprozesse mit synthetischen Berichten:
blockierende Befunde trotz Exit 0, Exitcodes 1/2/127 trotz sauberem Bericht,
fehlende Programme und fehlende/ungültige/unvollständige Berichte blockieren
jeweils. Berichtbereinigung entfernt Quelltextausschnitte und Trefferwerte;
Scannerfehler enthalten nur feste Fehlerkategorien. Diese lokalen Negativtests
ersetzen keinen ausgeführten fehlgeschlagenen GitHub-Workflow.

## Ansible auf isolierten Docker-/SSH-Testhosts

Die realen Playbooks wurden über SSH mit separatem Deployment-Konto und streng
geprüftem Hostschlüssel auf einem isolierten Docker-in-Docker-System ausgeführt.
Kein Docker-Socket des Arbeitsplatzes war eingebunden. TLS wurde gegen eine
frisch erzeugte lokale Test-CA geprüft. Eine zusätzliche Serie verwendete genau
Compose **2.40.3**, wie im Ubuntu-Bootstrap vorgesehen, mit Docker 29.6.1.

| Szenario | Nachgewiesenes Verhalten |
| --- | --- |
| Erstlauf | Erfolgreiche Bereitstellung und HTTPS-Bereitschaft |
| Identische Wiederholung | `changed=0`; alle Container-IDs und `State.StartedAt` unverändert |
| Konfigurationsupdate | Neuer Stand erfolgreich bereitgestellt |
| Absichtlich ungültige Nginx-Konfiguration und falsche neue HTTPS-URL | Vorherige kompatible Kombination aus allen drei Images und alter URL wiederhergestellt und geprüft; neuer Release bleibt Exit 2, `failed=1`, `rescued=1` |
| Explizites `rollback.yml` | Erfolgreiche Wiederherstellung; keine zweite Deploymentlogik |
| Veraltete Release-Sequenz | Abgewiesen ohne Konfigurationsänderung |
| Geänderter Datenbank-Kompatibilitätsvertrag | Abgewiesen ohne Konfigurationsänderung |
| Falscher SSH-Hostschlüssel | Verbindung abgewiesen, Exit 4 |
| Geheimnisse und Dateirechte | Tatsächliche Testgeheimnisse und private Schlüssel nicht in den 17 geprüften Logs; private Dateien 0600, Installationsverzeichnis 0700 |

Die erste Fehlerpfadserie verwendete noch eine isolierte frühere
PostgreSQL-Bookworm-Fixture. Sie belegt die Playbook-Fehlerbehandlung, aber keine
Übernahme bestehender Debian-Daten in die finale Alpine-Basis. Anschliessend
wurde die finale Kombination auf einem separaten frischen System mit eigenem
Datenbestand und Compose 2.40.3 geprüft:

- Erstlauf: `ok=29`, `changed=8`, `failed=0`.
- Identische Wiederholung: `ok=31`, `changed=0`, `failed=0`; sämtliche IDs und
  Startzeiten unverändert.
- Konfigurationsupdate: `ok=32`, `changed=8`, `failed=0`.
- Absichtlich fehlerhafter Rollout: vorherige drei Images, Konfiguration und
  HTTPS-URL wiederhergestellt; `failed=1`, `rescued=1`, Exit 2 wie gefordert.
- Laufende Image-IDs, lokale Registry-Digests, Commitlabels, Archivprüfsummen
  und Datenbank-Kompatibilitätsvertrag stimmen mit dem finalen Manifest überein.
  Auch diese Logs enthalten keine verwendeten Geheimniswerte.

Die wiederholbaren Aufrufe stehen in
[tests/deployment/README.md](../tests/deployment/README.md); vertrauliche
`release.json`-Eingaben werden nicht versioniert. Die erzeugten isolierten
SSH-/Docker-Testhosts und die separate Testdatenbank wurden anschliessend
gezielt entfernt. Fremde Container wurden nicht verändert; die benannten
Volumes der vorherigen Compose-Persistenztests bleiben als lokale QA-Daten
erhalten.

## Image-Zuordnung vor der DAST-Erweiterung und Aussagegrenzen

Lokale Prüfarbeitsbasis war der uncommittete Arbeitsbaum auf
`f19b7949e9fa4296f6b77f164fa9404547ab78ea`. Dieser Commit steht als technisches
Label in den lokalen Images; er enthält die neuen Dateien noch nicht. Die
lokalen Images sind deshalb **kein aus diesem Commit veröffentlichter Release**.
Erst der externe Workflow aus dem eingecheckten Stand belegt den endgültigen
Commit-/GHCR-Digest-Zusammenhang.

Die tatsächlich gescannten und für die finale lokale Bereitstellung verwendeten
Archive besitzen folgende SHA-256-Werte:

| Archiv | SHA-256 |
| --- | --- |
| `app.tar` | `b6699d04638efce7256a0cbf89ce911c7267617e2c8383858934116a3bf909ee` |
| `nginx.tar` | `f87a9b68299466f3642e831ccceeb2b33358ef437515645ed3a278a710015592` |
| `db.tar` | `53c7a561cd086dea06c1d6b9b4fd7842b636fac0fe387542c2227e641e040aff` |

Die lokale Fixture-Registry lieferte für dieselbe Kombination die folgenden
Digests, die Ansible tatsächlich verwendete; dies sind keine GHCR-Releases:

| Image | Lokaler Registry-Digest |
| --- | --- |
| App | `sha256:fd9b306e5fefe45850bb2428eb850dbf8568801e0b8380ba4252147b5c496f06` |
| Nginx | `sha256:8f3327d95a2fac526c316363ead27700f278e670af3a35e78c65ff0160076c0d` |
| PostgreSQL | `sha256:2db878318144f82acf157a63c5e3ad0cf45a542044fe2f371134a53b19242e68` |

Archive, Scan-/Testberichte, Testschlüssel und Laufzeitdaten bleiben lokal
ignoriert. In GitHub Actions werden bereinigte Berichte mit Commit-/Run-Bezug
als Artefakte aufbewahrt. Bestehende Word-/PDF-Dokumente und Diagramme wurden
nicht verändert.

## Offene externe Abnahme

- Die einzige GitHub-Environment `production` für `main` und erforderliche
  Branchprüfungen konfigurieren; konkrete Regeln und Berechtigungen nachweisen.
- Den eingecheckten Stand auf GitHub Actions durch Test, Build und Security
  führen und dieselben Archive in GHCR veröffentlichen. PRs dürfen weder
  veröffentlichen noch deployen; Fehler müssen Folgejobs sperren.
- Die Produktionshostangaben, geprüften SSH-Hostschlüssel, Zugang,
  HTTPS-Identität und Environment-Variables/-Secrets bereitstellen. Den Ubuntu-24.04-
  Bootstrap auf der tatsächlichen Zielplattform ausführen und prüfen.
- Auslieferung und Wiederholung über den echten Actions-/Ansible-Weg mit
  Commit, freigegebenen Digests und externer HTTPS-Abnahme belegen.

Nicht Gegenstand einer bereits bestandenen T02-Abnahme sind fachliche
Migrationen, Datenintegritäts-/Kostentests, authentifizierte API-Abnahme,
langfristige Offhost-Backups mit Restore, Produktion und vierwöchige
Verfügbarkeit. Diese Nachweise bleiben den zugehörigen Folgetasks zugeordnet.

## Nachtrag: Open-Source-SAST und aktiver ZAP-Scan

Ebenfalls am **18. September 2026**, auf ausdrücklichen Benutzerentscheid,
ergänzt: aktiver DAST-Scan gegen eine isolierte CI-Instanz. Die vorhandenen
Open-Source-Scanner bleiben erhalten, insbesondere Bandit für SAST. ZAP 2.17.0
ist auf den in [ci-cd.md](ci-cd.md) dokumentierten Image-Digest festgelegt.

| Prüfung | Tatsächliches Ergebnis |
| --- | --- |
| Erster echter aktiver ZAP-Lauf | Scanner vollständig abgeschlossen, Exit 0; die zusätzliche Befundprüfung blockiert korrekt bei zwei MEDIUM-Regeln: 10038 (fehlende CSP) und 10020 (Clickjacking-Schutz). |
| Korrektur und Neubuild | CSP und `X-Frame-Options: DENY` in beiden Nginx-Konfigurationen ergänzt; alle drei Archive neu erzeugt und verifiziert. Keine Scan-Ausnahme. |
| `python scripts/ci/dast.py --commit …` gegen neue Archive | Bestanden, nativer Scanner-Exit 0; keine HIGH-/MEDIUM-/LOW-Befunde. Ein informativer Befund (Regel 10015, drei Instanzen) bleibt im bereinigten Bericht sichtbar. |
| Scan-Abdeckung | Erwartete HTTP-200-Antworten für `/`, `/health/ready` und `/static/app.css`; Spider findet URLs; aktive Scan-Statistiken bestätigen Start, bearbeitete URLs, Abschluss und keinen vorzeitigen Stopp; passive Warteschlange abgearbeitet. |
| Laufende Instanz mit Docker inspiziert | Genau vier Container im internen Netz, keine veröffentlichten Ports, kein eingebundener Docker-Socket. Frische PostgreSQL-Testdaten; nach Scan keine zugehörigen Container oder Netze übrig. |
| `pytest --junitxml=reports/test/pytest-zap.xml -q` mit finalem PostgreSQL-Image | **216 bestanden, keine übersprungen**, davon 113 neue DAST-Prüffälle mit synthetischen Daten. |
| Negative DAST-Tests | MEDIUM/HIGH trotz Exit 0, fehlerhafte Ziel-/Versions-/Berichtsangaben, fehlende Berichte, Scannerfehler, Timeout und fehlgeschlagene Bereinigung blockieren. Vertrauliche synthetische Inhalte gelangen nicht in den Ergebnisbericht. |
| Ruff, Format und actionlint | Erfolgreich, 40 Python-Dateien geprüft. |
| Erneuter vollständiger Security-Lauf | pip-audit, Bandit, Gitleaks und Trivy für alle drei neuen Archive jeweils bestanden. ZAP und Trivy verwenden nachweislich dieselben Archivprüfsummen. |
| Zusätzlicher Arbeitsbaum-Secret-Scan | Alle versionierten und neuen, nicht ignorierten Dateien geprüft; Exit 0, keine Funde. Ein Fehlalarm in synthetischen Testargumenten wurde durch eindeutige mehrzeilige Formatierung behoben, ohne Scan-Ausnahme. |

ZAP-Befundbericht: `reports/security/zap.json`; übrige Scanergebnisse:
`reports/security/security-summary.json`. Rohberichte, HTTP-Antworten und
Angriffspayloads werden nicht veröffentlicht. Die temporäre Scaninstanz wird
auch bei Fehlern entfernt. Die beiden Änderungen am Nginx-Headerverhalten
erlauben weiterhin die vorhandene CSS-Datei und benötigen keine Inline-Ausnahme.

Dieser Nachtrag verwendet folgende Archive und ersetzt für den aktuellen
Scanstand die weiter oben dokumentierte frühere Image-Kombination:

| Archiv | SHA-256 |
| --- | --- |
| `app.tar` | `e98711e6200d52f9e2201b3ab6c1c7d6565660b776e0dd5775179f7d7eb213cf` |
| `nginx.tar` | `be703cd93205ca2176995554c072286514e4dcf89243fe487c8ad81c095ee925` |
| `db.tar` | `5aedec774484ccd83c867845e4d9fb2ff8c71e32f0d13d3d9d2fff7b037323e2` |

Auch diese Images stammen aus dem uncommitteten Arbeitsbaum auf dem oben
genannten HEAD. Der externe Actions-/GHCR-/Testhostnachweis bleibt offen.
Geprüft ist das öffentliche T02-Grundgerüst; authentifizierte Abdeckung folgt
mit T05/T09. Ein vollständiger manueller Pentest wird damit nicht behauptet.

## Nachtrag: Unit, Integration und End-to-End

Am **18. September 2026** auf Benutzerwunsch umgesetzt. Bezug: **T02, M07,
N03–N05 und N07–N10**. Die Einordnung, Voraussetzungen und Pipeline-Schritte
sind in [testing.md](testing.md) beschrieben. Die bisherigen 216 Prüffälle
bleiben erhalten; drei zusätzliche Factory-Prüfungen und drei echte
Browserprüfungen ergeben insgesamt **222 bestandene Tests ohne Skips**.

| Stufe | Tatsächlich ausgeführter Befehl | Ergebnis |
| --- | --- | --- |
| Unit | `.venv/bin/pytest tests/unit --junitxml=reports/test/unit.xml -q` | **178 bestanden**: 16 Anwendungskonfiguration, 162 CI-/Architekturprüfungen; keine laufende DB erforderlich. |
| Integration | `.venv/bin/pytest tests/integration --junitxml=reports/test/integration.xml -q` mit `CI=true` und `TEST_DATABASE_URL` | **41 bestanden**: 12 Anwendung/Factory/Routen, 29 echte Scanner-Prozessprüfungen. Der DB-Fall verwendete eine temporäre PostgreSQL-Instanz aus dem geprüften Image. |
| End-to-End | `.venv/bin/pytest tests/e2e --junitxml=reports/e2e/pytest.xml -q` | **3 bestanden** mit Playwright 1.63.0 und Chromium Headless Shell 153.0.8010.12, Revision 1243. HTTPS-Startseite samt CSS, Bereitschaft sowie Datenbankausfall mit HTTP 503 und anschliessender Wiederherstellung geprüft. |

Die eigentlichen Anwendungstests umfassen damit **16 Unit-, 12 Integrations-
und 3 E2E-Fälle** des minimalen T02-Gerüsts. Die übrigen Tests prüfen die
CI-/Security-Werkzeuge und Komponentengrenzen; sie sind kein Nachweis für noch
nicht implementierte Fachfunktionen.

Weitere tatsächliche Prüfungen:

- `pytest --collect-only -q -m unit`, `-m integration` und `-m e2e` wählen
  jeweils genau 178, 41 und 3 von 222 Tests aus.
- Ein E2E-Aufruf mit leerem `--image-artifacts`-Verzeichnis scheitert mit
  Exit 1 und verständlichem Setup-Fehler; er wird nicht übersprungen.
- Die erste Browserausführung zeigte, dass Docker auf einem internen Netz
  keine Hostports veröffentlicht. Die E2E-Fixture verwendet deshalb ein
  eigenes normales Bridge-Netz und bindet nur Nginx an einen zufälligen
  Loopback-Port. Docker-Inspektion bestätigt: App und DB haben keine
  Hostport-Bindungen. Die TLS-Verbindung wurde vor dem Browser mit Test-CA und
  vollständiger Hostnamenprüfung erfolgreich geprüft.
- Ein anfänglicher Fehler beim Registrieren eines eingebauten Python-Callbacks
  in Playwright wurde durch einen normalen Callback behoben. Der anschliessende
  vollständige Browserlauf bestand alle drei Fälle in 24,58 Sekunden.
- Ruff, Formatprüfung, actionlint und `uv lock --check` bestanden;
  46 Python-Dateien und ein Lockfile mit 85 Paketen geprüft.
- Nach Ergänzung der separaten E2E-Abhängigkeitsgruppe alle drei Image-Archive
  neu gebaut und verifiziert. pip-audit, Bandit, Gitleaks sowie Trivy für App,
  Nginx und PostgreSQL bestanden. Playwright gehört nicht ins produktive Image.
- Den aktiven ZAP-Scan mit `python scripts/ci/dast.py --commit
  f19b7949e9fa4296f6b77f164fa9404547ab78ea` erneut gegen genau diese Archive
  ausgeführt: bestanden, nativer Exit 0; keine HIGH-/MEDIUM-/LOW-Befunde,
  nur die informative Regel 10015 mit drei Instanzen. Image-Metadaten im
  ZAP-Bericht, übrigen Security-Bericht und Manifest stimmen vollständig überein.
  Docker-Inspektion während des Scans bestätigt weiterhin vier Container im
  internen Netz, ohne Hostports oder Docker-Socket. Nach Abschluss sind alle
  zugehörigen Testcontainer und Netze entfernt.
- Zusätzlicher Gitleaks-Arbeitsbaumscan über 81 versionierte und neue,
  nicht ignorierte Dateien: keine Funde. Unabhängiger Workflow-Review bestätigt
  getrennte Berichte und die Sperre nachfolgender Stufen bei Testfehlern.

Diese Prüfung verwendet folgende Archive; der Vorbehalt zum uncommitteten
Arbeitsbaum und die offene externe Actions-/GHCR-/Testhostabnahme gelten weiter:

| Archiv | SHA-256 |
| --- | --- |
| `app.tar` | `2e34e7cc0d28c3182766f2057c2d97eb9c98d5615451b8ea7f89043dfc6ab74d` |
| `nginx.tar` | `b567c6a046af65e3646439be9ba4fc4a425cf22413fd03b10c6abc91b24f2e5e` |
| `db.tar` | `fc9e17f1d2083a2b5d3239438d8a4c94cfc6f8b6a7e8b5dd10010c541acbc622` |

## Nachtrag: getrennte App- und Infrastruktur-Releases

Am **18. September 2026** auf ausdrücklichen Benutzerentscheid umgesetzt.
Bezug: **T02, M07, N03–N05 und N07–N10**. Der normale Workflow baut und
veröffentlicht nur die App. Nginx wird als offizielles Image verwendet;
PostgreSQL besitzt ein eigenes, unabhängig versioniertes Infrastruktur-Rezept
und einen separaten manuellen Build-/Security-/Publish-Workflow. Ansible liest
die Infrastruktur-Pins aus einer gemeinsamen Datei. Die Betriebsregeln stehen
in [ci-cd.md](ci-cd.md).

### Test-, Build- und Security-Nachweise

| Prüfung | Tatsächliches Ergebnis |
| --- | --- |
| `pytest tests/unit --junitxml=reports/test/unit.xml -q` | **209 bestanden**. Insbesondere: normale Veröffentlichung nur der App, fehlende/manipulierte Infrastruktur-Pins, Archividentitäten, unveränderliche Infrastruktur-Versionen, Registry-/Scannerfehler. |
| `pytest tests/integration --junitxml=reports/test/integration.xml -q` | **41 bestanden, keine Skips**, mit echter temporärer PostgreSQL-Datenbank. Die betroffenen Scanner-Prozessfälle wurden nach dem abschliessenden Refactoring zusätzlich gezielt geprüft. |
| `pytest tests/e2e --junitxml=reports/e2e/pytest.xml -q` | **3 bestanden** gegen App, offizielles Nginx und die getrennte DB-Version. Startseite, CSS, HTTPS, Bereitschaft, Datenbankausfall und Wiederanlauf. |
| Normaler `scripts/ci/images.py build --commit …` mit lokaler Pin-Datei | App gebaut; Nginx und DB per festem Digest bezogen, alle drei archiviert und verifiziert. Kein Nginx-/DB-Build im normalen Ablauf. |
| Upstream-Multiarch-Archiv | Der reale Nginx-Index erforderte eine Erweiterung der OCI-Prüfung: genau das Linux-amd64-Manifest und seine Konfiguration werden kryptographisch mit dem Registry-Index verbunden. Nicht heruntergeladene andere Plattformen sind keine akzeptierten Laufzeitidentitäten; doppelte amd64-Deskriptoren werden abgewiesen. |
| Normaler Security-Lauf | pip-audit, Bandit, Gitleaks und Trivy für App/Nginx/DB bestanden. Ein Bandit-Befund zum fest codierten temporären Pfad wurde ohne Ausnahme durch die System-Tempverzeichnisfunktion behoben und erneut geprüft. |
| `scripts/ci/dast.py --commit …` | Aktiver ZAP-Scan bestanden, Exit 0; keine HIGH-/MEDIUM-/LOW-Befunde. Informative Regel 10015 mit drei Instanzen. Der Bericht verweist auf dieselben Archive wie die übrigen Scans. |
| `scripts/ci/infrastructure.py build`, `verify`, `smoke`, `scan` | Separates DB-Rezept gebaut und archiviert; echte Bereitschaft und `SELECT 1` im isolierten Container geprüft; pip-audit, Bandit, Gitleaks und Trivy bestanden. Keine GHCR-Veröffentlichung ausgeführt. |
| Ansible-Lint und Syntax | Lint mit Profil `production` bestanden; Bootstrap-, App-Deploy-, Infrastruktur- und Rollback-Playbooks syntaktisch geprüft. |
| Ruff, Formatprüfung und actionlint | Bestanden; beide Workflows geprüft. Zusätzlicher Arbeitsbaum-Gitleaks-Scan einschliesslich neuer Dateien ohne Funde. |
| README-Entwicklungsstart | Separate App-/DB-Builds, offizielles Nginx ohne eigenen Build; alle Dienste bereit; `/`, `/health/ready` und `/static/app.css` liefern 200. Nur Nginx veröffentlicht einen zufälligen Loopback-Port. `down` erhält das eigene Testvolume. |

Damit bestehen insgesamt **253 Tests**, davon weiterhin 16 Unit-, 12
Integrations- und 3 Browserfälle für das minimale Anwendungsgerüst. Die übrigen
Fälle prüfen CI-/Security-Werkzeuge und die Architektur. Fachfunktionen werden
dadurch nicht als implementiert oder abgenommen dargestellt.

### Tatsächlicher Ansible-Lebenszyklus

Die aktualisierte Fixture aus `scripts/prepare_deployment_test.py` startete
einen eigenen SSH-Host mit isoliertem Docker-Daemon und lokaler Registry.
Die Playbooks verwendeten geprüfte Hostschlüssel, einen separaten Zugang und
vollständige TLS-/Hostnamenprüfung. Die Registry-Fixture stellt alle drei
Prüfimages lokal bereit; der normale GHCR-Publisher veröffentlicht nur die App.

| Ablauf | Tatsächliches Ergebnis |
| --- | --- |
| Erstinstallation über `deploy.yml` | PostgreSQL, App und Nginx erfolgreich bereitgestellt. Statische Dateien aus dem App-Image extrahiert. |
| Gleicher App-Release erneut | Exit 0, **changed=0**; Container-IDs und Startzeiten aller drei Dienste unverändert. |
| Neues App-Image mit geändertem CSS | App ersetzt und neues CSS über Nginx nachgewiesen; **IDs und Startzeiten von Nginx und DB unverändert**. |
| Absichtlich nicht startfähiges neues App-Image | Release bleibt Exit 2; vorherige App und passende statische Dateien erfolgreich wiederhergestellt. Nginx und DB bleiben unverändert. |
| Nginx-Konfigurationsänderung über normales `deploy.yml` | Vor Auslieferung abgewiesen, Exit 2. |
| Dieselbe Änderung über `infrastructure.yml` | Erfolgreich angewendet; neuer HTTP-Prüfheader nach Nginx-Reload sichtbar, Infrastrukturcontainer nicht ersetzt. |
| Wiederholung nach Infrastrukturwartung | Exit 0, **changed=0**. |
| Expliziter App-Rollback über eine Infrastrukturgrenze | Exit 2 vor Änderungen; Container unverändert. |
| Geheimnisprüfung | Keine erzeugten Anwendungsschlüssel, DB-Passwörter oder Verbindungs-URLs in den Testlogs gefunden. |

Der Erstlauf deckte einen Fehler in der quotierten Docker-Label-Abfrage auf;
die Abfrage verwendet nun JSON-Labels. Der unabhängige Review korrigierte
ausserdem den Static-Quellpfad, den Erhalt der ursprünglichen Wartungssicherung
bei Wiederholungsversuchen sowie den Schutz bereits initialisierter Datenbanken
nach fehlgeschlagener Erstinstallation. Die Nginx-Vorprüfung verlangt seinen
Digest und laufenden Zustand; ein Ausfall der alten App darf ein reparierendes
App-Deployment nicht über deren indirekten Readiness-Status blockieren.

Die App-Update-/Fehlerimages waren ausdrücklich lokale Prüfvarianten des
getesteten App-Images. Sie wurden nicht als Releases veröffentlicht. Im ersten
Wartungsprüfskript lag der zusätzliche HTTP-Prüfheader im falschen
Nginx-Vererbungskontext; der abschliessende Test setzte ihn im Serverkontext
und wies die aktive Konfiguration nach. Die Produktkonfiguration benötigte
hierfür keine Änderung.

### Image-Zuordnung und verbleibende Einrichtung

| Archiv | SHA-256 |
| --- | --- |
| `app.tar` | `2fff1edb331891e87f41184462eeed25995e2df7a5dc5707589f5c8eee0cae33` |
| `nginx.tar` | `3aec3efcd242bc89dc09be5415a9c38e3150db0ba8f4182c1ac6b3b2704d1568` |
| `db.tar` | `beaa2f777532e3a3c392fbd66834c3ef625edcae98a65887e3fbb41e61cb46d2` |

Die Prüfungen verwendeten eine lokale Infrastruktur-Pin-Datei und eine echte
lokale Registry. Die Dateien im Arbeitsbaum sind weiterhin nicht eingecheckt;
das HEAD-Label ist kein Nachweis eines daraus veröffentlichten Releases.
Die erste echte GHCR-Veröffentlichung des separaten PostgreSQL-Pakets und die
Übernahme ihres tatsächlichen Digests in `deploy/infrastructure.json` bleiben
offen. Bis dahin blockiert der bewusst leere `postgres_image`-Pin den normalen
Build. Registry-Fehler werden nicht als Erlaubnis zum Überschreiben einer
Infrastruktur-Version behandelt; das tatsächliche GHCR-Verhalten ist noch
nicht live geprüft.

Temporäre Testcontainer, Netze und eigene Fixture-Volumes wurden gezielt
entfernt. Private Testschlüssel und geschützte Variablendateien wurden bereinigt;
die nicht geheimen Prüfnachweise bleiben lokal ignoriert. Externer Actions-Lauf,
Zielhost-Bootstrap, tatsächliche Test-/Produktionsauslieferung und spätere
Schema-/API-Abnahme bleiben wie zuvor offen.
## Nachtrag: einzige Betriebsumgebung `production`

**18. September 2026**, neuerer Benutzerentscheid; Bezug **T02, M07, N07–N10**.
Für die Praxisarbeit deployt nur `main` in die GitHub-Environment `production`.
`develop` und eine dauerhafte Environment `test` sind keine Voraussetzungen mehr.
Die bisherigen lokalen Testnachweise bleiben gültige Nachweise ihrer damaligen
Prüfstände. Unit, Integration, E2E und aktiver ZAP bleiben in isolierten Instanzen;
es wurde kein Sicherheitsscan gegen Produktion ausgeführt.

Der Workflow verwendet das Produktionsinventory und die feste Deployment-Gruppe
`repairhub-deploy-production`. Host/URL/Datenbanknamen kommen aus dessen
Environment-Variables, SSH-/Anwendungs-/DB-/TLS-Geheimnisse aus dessen Secrets.
Die lokale Ansible-Fixture besitzt ihr eigenes Inventory unter
`tests/deployment/inventory.yml`, mit festem Loopback-Ziel und eigenem Fixture-Port.
Die genaue Einrichtungsliste steht in [ci-cd.md](ci-cd.md#github-einrichtung).

Für diese Anpassung tatsächlich geprüft:

| Prüfung | Ergebnis |
| --- | --- |
| `actionlint .github/workflows/ci-cd.yml .github/workflows/infrastructure.yml` | Beide Workflows gültig; keine Befunde. Publish nur für Nicht-PR-Läufe auf `main`, Deploy hängt von erfolgreichem Publish ab. |
| `pytest tests/unit/ci/test_ci_deployment.py -q --junitxml=reports/test/production-deployment-inputs.xml` | **3 bestanden**: geschützte Dateien/Sonderzeichen, Abweisung von Zeilenumbruch-Injektion und keine Infrastrukturüberschreibung durch Deployment-Eingaben. |
| `ansible-lint deploy/ansible tests/deployment/inventory.yml` | **0 Fehler, 0 Warnungen**, Profil `production`. |
| `ansible-playbook -i deploy/ansible/inventories/production/hosts.yml deploy/ansible/<playbook>.yml --syntax-check` | Für `bootstrap`, `infrastructure`, `deploy` und `rollback` erfolgreich; keine Hostverbindung. |
| Fixture-Inventory auflösen und Deploy-Syntax prüfen | Loopback/Fixture-Port korrekt; produktive Host-/Portvariablen ändern das Fixture-Ziel nicht; fehlender Fixture-Port ergibt den ungültigen Port `0`. |
| `ruff check .`, `ruff format --check .`, `git diff --check` | Erfolgreich; 48 Python-Dateien bereits formatiert. |

Für diese reine Workflow-/Inventaranpassung wurden Image-Build, DB-/Browser-/
DAST-Läufe und vollständiger Ansible-Lebenszyklus nicht erneut ausgeführt.
GitHub-Einstellungen und Secrets wurden nicht remote angelegt; weder
Produktionsdeployment noch echte Actions-/GHCR-Abnahme sind damit nachgewiesen.

## Nachtrag: SSH-Passwortauthentifizierung

**18. September 2026**, Benutzerentscheid; Bezug **T02, M07, N07–N10**.
Die VM-Anmeldung erfolgt über einen bestehenden Benutzer und dessen Passwort.
`DEPLOY_USER` ist nun verpflichtend; das Environment-Secret
`DEPLOY_SSH_PASSWORD` ersetzt `DEPLOY_SSH_PRIVATE_KEY`. Der Workflow verwendet
Ansible-Core 2.21.4 mit `ssh_askpass`, die Passwortübergabe in einer temporären
0600-JSON-Datei und weiterhin strikte Prüfung der bekannten Server-Hostschlüssel.
Bootstrap setzt ein vorhandenes Konto voraus und ergänzt dessen Docker-Gruppe;
es verwaltet keine Benutzerpasswörter oder Benutzer-Schlüsseldateien mehr.

| Prüfung | Tatsächliches Ergebnis |
| --- | --- |
| `pytest tests/unit/ci/test_ci_deployment.py -q --junitxml=reports/test/ssh-password-inputs.xml` | **13 bestanden**; Passwort mit Sonderzeichen, Unicode und Leerzeichen unverändert, keine SSH-Passwortausgabe, geschützte Dateien, fehlende Angaben sowie CR/LF/NUL abgewiesen. |
| `actionlint .github/workflows/ci-cd.yml .github/workflows/infrastructure.yml` | Beide Workflows ohne Befunde. |
| `ruff check .`, `ruff format --check .`, `git diff --check` | Erfolgreich; 48 Python-Dateien bereits formatiert. |
| `ansible-lint deploy/ansible` und Bootstrap-`--syntax-check` mit Produktionsinventory | Erfolgreich, Profil `production`. |
| Lesende Ausführung der Bootstrap-Vorprüfung mit `assert`, `getent` und `set_fact` | Vorhandenes Konto über Deployment-Variable und expliziten Ansible-Benutzer korrekt aufgelöst, primäre GID übernommen. Fehlender oder unbekannter Benutzer blockiert vor Änderungen. |
| Produktionsinventory ohne Hostverbindung auflösen | Expliziter SSH-Benutzer korrekt; fehlender oder leerer Benutzer wird abgewiesen, kein Rückfall auf den Controller-Benutzer. |
| Echter SSH-Test: `ansible ... -m ansible.builtin.ping --extra-vars @<geschützte vars.json>` | Passwortanmeldung mit Quotes, Dollarzeichen, Leerzeichen und Umlauten erfolgreich: **Exit 0 / pong**. |
| Derselbe SSH-Test mit falschem Passwort | **Exit 4**, Zugriff abgewiesen. |
| Derselbe SSH-Test mit falschem Server-Hostschlüssel | **Exit 2 / FAILED**, Hostschlüsselprüfung blockiert den Zugriff. |

Die echten SSH-Prüfungen verwendeten einen wegwerfbaren lokalen Container,
`scripts/ci/deployment_input.py`, das Produktionsinventory mit explizitem
Loopback-Ziel, die gemeinsame `ansible.cfg` und die SSH-Optionen des Workflows.
Jeder Fall hatte einen eigenen ControlPath; eine bestehende Verbindung konnte
die negativen Fälle nicht umgehen. Eingabeverzeichnis 0700 und Dateien 0600
wurden geprüft. Helper-Ausgaben sowie Ansible-/sshd-Logs wurden vor Aufbewahrung
auf die zufälligen Testgeheimnisse geprüft. Der bereinigte lokale Bericht liegt
unter `/tmp/repairhub-t02-ssh-password-validation/summary.json`; Testcontainer,
Netzwerk und temporäre Geheimnisse wurden entfernt.

Der erste lokale Prüflauf erwartete beim falschen Hostschlüssel zu eng den
Status `UNREACHABLE`; Ansible meldete korrekt `FAILED`. Nach Korrektur dieser
Testannahme bestand der vollständige SSH-Prüflauf. Eine echte VM-Verbindung,
vollständige Ubuntu-Hostinstallation, Kontenänderung oder erneute
App-/Image-/DAST-Abnahme wurde für diese Anpassung nicht ausgeführt.

## Nachtrag: offizielles PostgreSQL ohne eigenen Build

**18. September 2026**, neuerer Benutzerentscheid; Bezug **T02, M07,
N03–N05 und N07–N10**. PostgreSQL wird wie Nginx direkt als offizielles,
fest gepinntes Image bezogen. Eigener DB-Dockerfile, separater GitHub-Release-
Workflow und DB-Build-/Publish-Funktionen sind entfernt. `postgres_image` ist
vollständig gesetzt; die frühere offene Voraussetzung einer eigenen
GHCR-Datenbankveröffentlichung entfällt. Nur die App wird gebaut und publiziert.

Die freigegebene Ausnahme in
[`deploy/security/postgres-gosu.trivyignore.yaml`](../deploy/security/postgres-gosu.trivyignore.yaml)
gilt ausschliesslich für den offiziellen PostgreSQL-Digest, den Pfad
`usr/local/bin/gosu`, Go-stdlib `v1.24.6` und die 22 benannten CVEs. Der aktuelle
Rohscan bestätigt **21 HIGH und 1 CRITICAL**. Diese Befunde sind akzeptiert,
nicht behoben; sie bleiben im Trivy-Bericht sichtbar. Ab 31.12.2026, 00:00 UTC
ist die Ausnahme ungültig. Andere Images und Scanner erhalten keine Ausnahme.

| Prüfung | Tatsächliches Ergebnis |
| --- | --- |
| `pytest tests/unit tests/integration/ci -q --junitxml=reports/test/official-postgres-tools.xml` | **226 Unit- und 40 CI-Prozessintegrationstests bestanden**. Darunter Archiv-/Digest-/DB-Versionsprüfung und Begrenzung der Ausnahme auf das richtige Image. |
| `pytest tests/integration/app -q --junitxml=reports/test/official-postgres-integration.xml` mit eigener PostgreSQL-Instanz | **12 bestanden**, echte Verbindung zum offiziellen PostgreSQL 17.11, keine Skips. |
| `scripts/ci/images.py build --directory artifacts/official-postgres --commit <HEAD>` | Nur App gebaut; offizielle Nginx-/PostgreSQL-Pins bezogen, vollständige Kombination archiviert. Keine eigene Infrastruktur-Pin-Datei nötig. |
| `scripts/ci/smoke_images.py --directory artifacts/official-postgres --commit <HEAD>` | Verifikation, DB-/App-Bereitschaft und HTTPS mit geprüfter CA erfolgreich; internes Netz ohne Hostports. |
| `pytest tests/e2e --image-artifacts artifacts/official-postgres --junitxml=reports/e2e/official-postgres.xml -q` | **3 Chromium-E2E-Tests bestanden**; insgesamt 281 Tests erfolgreich. |
| `scripts/ci/security.py --artifacts artifacts/official-postgres --reports reports/official-postgres --binaries /tmp/repairhub-t02-scanners` | pip-audit, Bandit, Gitleaks und Trivy für alle drei Archive bestanden; DB mit genau 22 sichtbaren akzeptierten Befunden, App/Nginx ohne Ausnahmen. |
| Echte Trivy-Proben mit temporären Policy-Kopien | Gültige Ausnahme: Exit 0, 22 akzeptiert. Abgelaufen, falscher Pfad oder andere Paketversion: jeweils Exit 1, 22 aktiv. Eine CVE aus der Liste entfernt: Exit 1, 1 aktiv und 21 akzeptiert. |
| `scripts/ci/dast.py --artifacts artifacts/official-postgres --reports reports/official-postgres --commit <HEAD>` | Aktiver ZAP erfolgreich; keine HIGH/MEDIUM/LOW-Befunde, nur Regel 10015 mit drei Info-Instanzen. |
| Tatsächliche Ansible-DB-Identitätsaufgaben plus eigener flüchtiger DB-Container | Offizieller Digest und Version 17.11 akzeptiert; absichtlich falsche Version 17.12 abgewiesen. PostgreSQL-UID 70, Datenverzeichnis und `SELECT 1` geprüft, ohne Ports oder Datenvolume. |
| Development-Compose rendern | Nur App besitzt `build`; Nginx/DB verwenden die offiziellen Pins. |
| Ruff/Format, Architekturprüfung, Actionlint, Ansible-Lint und Syntax aller vier Playbooks | Erfolgreich. Zusätzlich Gitleaks über alle nicht ignorierten Arbeitsbaumdateien: Exit 0. |

Python-Prüfungen verwendeten die gesperrte virtuelle Umgebung. Die
Anwendungsintegration wurde über `.qa/official-postgres/run-integration.py`
mit einer eigenen PostgreSQL-Instanz und zufälligen geschützten Zugangsdaten
ausgeführt. Die Ansible-/DB-Identitätsprüfung ist durch
`/tmp/repairhub-official-postgres-check.py` dokumentiert; die nativen
Ausnahme-Grenzfälle durch
`/tmp/repairhub-t02-gosu-exception-validation/summary.json`.

Die geprüften Archive liegen unter `artifacts/official-postgres`:

| Archiv | SHA-256 |
| --- | --- |
| `app.tar` | `56cef5615a7dd7fc45a6d49242cd7af7b4051d6939abb35e5cf354389eac6d1b` |
| `nginx.tar` | `3aec3efcd242bc89dc09be5415a9c38e3150db0ba8f4182c1ac6b3b2704d1568` |
| `db.tar` | `ff181b16a32ed6c3b08a2d3c0ca4a9014e996a5f0d6001680ba28b52f6ae6b46` |

Der Arbeitsbaum ist weiterhin nicht eingecheckt; das HEAD-Label bezeichnet
keinen daraus veröffentlichten Release. Eigene Prüfcontainer, Netze und
temporäre Geheimnisse sind entfernt, bestehende Benutzerdaten wurden nicht
migriert. Der vollständige Ansible-App-Lebenszyklus wurde für diese Umstellung
nicht erneut ausgeführt; geprüft wurden die tatsächlich geänderten DB-Aufgaben.
Echter GitHub-Actions-/App-GHCR-Durchlauf, Produktionshost-Bootstrap und
Produktionsauslieferung bleiben offen.


## Nachtrag 18.09.2026: TLS-Ausstellung durch Ansible

Bezug: T02, M07, N03–N05, N07–N10. Keine fachlichen Komponenten verändert.

Ausgeführt und bestanden:

- `.venv/bin/pytest tests/unit tests/integration/test_acme_certificate.py -q --junitxml=reports/test/acme.xml`: 235 Tests, davon 233 Unit und 2 Integration mit echtem OpenSSL.
- `.venv/bin/pytest tests/integration/ci -q --junitxml=reports/test/acme-ci-integration.xml`: 40 Integrationsprüfungen.
- `.venv/bin/ruff check .` und `.venv/bin/ruff format --check .`.
- `PATH="$PWD/.venv/bin:$PATH" ANSIBLE_CONFIG="$PWD/deploy/ansible/ansible.cfg" .venv/bin/ansible-lint deploy/ansible`: keine Fehler/Warnungen.
- `ansible-playbook -i deploy/ansible/inventories/production/hosts.yml deploy/ansible/<playbook>.yml --syntax-check` mit obigem PATH/ANSIBLE_CONFIG und REPAIRHUB_DEPLOY_USER=repairhub-deploy: bootstrap, infrastructure, deploy und rollback bestanden.
- `/tmp/repairhub-t02-scanners/actionlint .github/workflows/ci-cd.yml`.
- `.venv/bin/bandit -r app scripts deploy/ansible/roles/docker_host/files --severity-level medium --confidence-level medium -q`: keine blockierenden Befunde.
- `DOCKER_CONFIG=/tmp/repairhub-t02-public-docker .venv/bin/python .qa/check_acme_nginx.py`: reale HTTPS-Auslieferung vor und nach Zertifikatswechsel, identische Nginx-Container-ID, Wiederholung ohne Reload. Ergebnis in `reports/test/acme-nginx.json`; Certbot wurde dabei durch lokal erzeugte OpenSSL-Zertifikate ersetzt. Container, Netzwerk und temporäre Schlüssel entfernt.

Negativfälle: Ausstellung scheitert, falscher Hostname, falsches Schlüsselpaar,
fehlgeschlagener Reload, belegte/fehlende Hostsperre. Fehler führen nicht zu einer
falschen Aktivierungsmarkierung; ein fehlgeschlagener Reload wird erneut versucht.
Die reale OpenSSL-Prüfung deckte auf, dass `x509 -checkend` die Hostnamenprüfung
im selben Aufruf verdrängt; beide Prüfungen erfolgen deshalb getrennt.

Offen: Paketinstallation und Timerlauf auf Ubuntu 24.04, DNS-/Port-80-Erreichbarkeit
der VM, echte HTTP-01-Ausstellung, automatische öffentliche Erneuerung und
GitHub-/Produktionsdeployment. App-Image, PostgreSQL, E2E und ZAP wurden für diesen
reinen TLS-/Deployment-Nachtrag nicht erneut gebaut beziehungsweise ausgeführt;
deren vorheriger Nachweis bleibt separat dokumentiert.


## Nachtrag 21.09.2026: Branches und Release-Tags

Bezug T02, M07, N03–N05/N07–N10. Push-Filter auf alle Branches und Tags
erweitert; zusätzlich release.published. Publish und Deploy folgen weiterhin
nur nach erfolgreichen Prüfungen, auf main oder Release-Tags. Die Zuordnung
zum aktuellen main-Commit und die unveränderte Tag-Zuordnung werden vor beiden
Stufen geprüft. Annotierte und einfache Tags werden über die Commit-API
aufgelöst. GitHub-Environment muss die verwendeten Tagmuster zulassen.

Ausgeführt und bestanden:

- `.venv/bin/pytest tests/unit/ci/test_release_ref.py -q`: 16 Tests zu zulässigen Ereignissen, fremden Branches/PRs, veralteten Commits, verschobenen Tags und API-Aufruf.
- `.venv/bin/pytest tests/unit/ci -q --junitxml=reports/test/branch-tag-ci.xml`: 203 Tests bestanden.
- Ruff-Prüfung und Formatprüfung für `scripts/ci/check_release_ref.py` und `tests/unit/ci/test_release_ref.py`.
- `/tmp/repairhub-t02-scanners/actionlint .github/workflows/ci-cd.yml`: erfolgreich.
- `.venv/bin/bandit scripts/ci/check_release_ref.py --severity-level medium --confidence-level medium -q`: keine blockierenden Befunde.

GitHub-Ereignisse, Tagauflösung gegen die echte Registry-/Repository-Konfiguration
und produktive Environment-Tagregeln wurden nicht live abgenommen. Der frühere
Build-/E2E-/Security-Nachweis wurde für diese Auslöseränderung nicht wiederholt.
