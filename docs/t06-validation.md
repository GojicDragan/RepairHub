# T06 – Geräteverwaltung, AJAX und virtuelle Liste

Stand: 21. September 2026. Bezug: M02, F03, N02–N04, N06 und ausdrücklicher
Benutzerauftrag zu AJAX/virtueller Liste. Umsetzung und Grenzen:
[Geräteverwaltung](devices.md).

## Umsetzung

Vier frameworkfreie Geräte-Slices mit injizierten Ports, passenden Datenadaptern
und gemeinsamem Eigentumsfilter. Name, Hersteller und Modell bestimmen die
nachgelagerte Gerätepersistenz. Migration `0002_devices` ist additiv; vorhandene
Benutzerkonten bleiben erhalten. Keine neuen Fachabhängigkeiten oder Frameworks.

HTML liefert zunächst 20 Geräte. Nach Anbindung der Humble Objects werden
Fenster mit höchstens 60 Zeilen per AJAX geladen und im DOM ersetzt. Erfassung
und Bearbeitung speichern ohne Dokumentnavigation. Validierungs- und Netzfehler
lassen gültige Eingaben stehen. Vor-/Zurück-Buttons bewegen mit JS denselben
Scrollbereich; ohne JS bleiben normale Seitenlinks und POST-Formulare nutzbar.
Die bestehende Werkstattgestaltung und deutsche gettext-Übersetzungen sind integriert.

Die Nginx-CSP benötigt für Fetch `connect-src 'self'`. Diese gezielte Erweiterung
gilt für Development und Produktion; externe AJAX-Ziele werden nicht freigegeben.
Der erste Browserlauf wies die fehlende Freigabe nach. Zusätzlich wurden
mehrdeutige Testselektoren auf den Seiteninhalt begrenzt und die mobile Navigation
für Gerätezugang, Benutzername und Abmeldung erweitert.

## Positive und negative Abnahme

| Bereich | Nachweis |
| --- | --- |
| Frameworkfreie Regeln, injizierte Repository-Ports, kein Zugriff ohne gültige Identität | `tests/unit/domains/devices/test_devices.py` |
| Anlegen, Detail, Liste und Änderung dauerhaft in PostgreSQL | `tests/integration/devices/test_devices.py` |
| Fremde/fehlende IDs identisch 404; manipulierte Eigentümer-IDs ignoriert | Integration mit zwei bestätigten Benutzern |
| Leere, überlange, falsch typisierte Werte und Steuerzeichen abgewiesen | Domain- und Integrationstests |
| Ungültige Änderung erhält Eingaben und bisherige Daten | HTML-/AJAX-Integration und Browser |
| CSRF gilt auch für JSON; nicht angemeldete AJAX-Anfragen erhalten 401 | Integration |
| DB-Constraints und Rollback bei fehlgeschlagenem Commit | PostgreSQL-Integration |
| Upgrade vom bisherigen Benutzerschema erhält Konten | Echte Migration von `0001_register_user` nach `0002_devices` |
| Begrenzte Fenster und obere ID-Grenze bei neuen Geräten | Integration und Node-Tests |
| Alte Antworten überschreiben kein neues Fenster; Rückscrollen und Wiederholung funktionieren | DOM-freie Presenter-Tests und Browser |
| Anfangs-HTML enthält 20 Zeilen; DOM bleibt bei höchstens 60 | Browser mit 240 Geräten je Testkonto |
| AJAX-Speichern ohne Navigation; weitere Speicherung bearbeitet dasselbe Gerät | Browser in Englisch und Deutsch |
| Deutsche/englische Formulare und Pagination ohne JavaScript | Browser |
| Eigene Gerätetexte werden escaped; private Seiten sind nicht indexierbar | Integration und bestehende Katalogtests |

## Prüfungen

- `.venv/bin/pytest tests/unit -q`: 406 bestanden.
- `node --test tests/unit/frontend/*.test.mjs`: 13 bestanden.
- `.qa/t04/run-integration.py` mit eigener kurzlebiger PostgreSQL-Instanz:
  198 Integrationstests bestanden, zusätzlich leere Migration und Modelldrift geprüft.
- Architekturprüfung, Ruff, Formatprüfung und Ansible-Lint bestanden.
- Produktionsimage unter `artifacts/t06-final` gebaut. Der lokale Basiscommit im Manifest
  ist `65f9d9054f60c70a22749af3fc52151f397b5ad5`; Änderungen sind noch nicht committed.
  Das Commit-Label belegt keinen veröffentlichten T06-Release.
- Vier gezielte Geräte-Browsertests nach CSP-Korrektur bestanden; Screenshots bei
  390 px auf Deutsch und Englisch unter `reports/t06/devices-*.png` visuell geprüft.
- Abschliessend `.venv/bin/pytest tests/e2e --image-artifacts artifacts/t06-final
  --junitxml=reports/t06/e2e-final.xml -q`: **33 bestanden**. Die zusätzlichen
  Scroll-Buttons wurden auf reine AJAX-Navigation geprüft; ein weiterer Test
  sichert den leeren Zustand ohne unnötigen Scrollbereich ab.
- Dependency-, Bandit-, Secret- und alle drei Containerprüfungen auf dem finalen
  Image bestanden; Berichte unter `reports/security/t06-final`. Bestehende explizite
  PostgreSQL-Ausnahme unverändert, keine weitere Ausnahme ergänzt.
- Finales App-Image: `sha256:b7bd2da8f7ae54b83319ab534df2c0ca6924759d7851d01e8e76cbc2cf176d9c`.
- `git diff --check`: bestanden.

## Bereitstellung

Die neue CSP ist eine Infrastrukturkonfiguration. Vor dem T06-App-Release muss
`deploy/ansible/infrastructure.yml` mit dem bislang laufenden App-Digest und der
neuen Nginx-Konfiguration ausgeführt werden. Anschliessend stellt `deploy.yml`
den neuen App-Digest bereit und führt die kontrollierte Migration aus.
Ein normaler App-Release weist eine ungeplante Infrastrukturänderung absichtlich ab.
Neue Environment-Variablen oder Secrets sind nicht erforderlich.

Die lokalen Ansible-Prüfungen verwenden ausschliesslich den kurzlebigen
Docker-in-Docker-SSH-Testhost aus `scripts/prepare_deployment_test.py`, eigene
Registry, Testschlüssel und Test-CA. Die Produktions-VM wurde nicht verändert.

Tatsächlich ausgeführt (Inventory und SSH-Parameter aus der geschützten lokalen
`controller.env`):

1. `ansible-playbook deploy/ansible/deploy.yml --extra-vars @.qa/t06-deploy/release.json`:
   Erstlauf erfolgreich, `changed=32`, `failed=0`.
2. `ansible-playbook deploy/ansible/infrastructure.yml --extra-vars @.qa/t06-deploy/release.json`:
   CSP-Infrastrukturänderung mit dem laufenden App-Digest erfolgreich,
   `changed=28`, `failed=0`.
3. `deploy.yml` mit finalem App-Digest: erfolgreich, `changed=21`, `failed=0`.
4. Identische Wiederholung von `deploy.yml`: **`changed=0`, `failed=0`**.

Zusätzlich auf dem Ansible-Testhost mit eigenem Prüfkonto über CA-geprüftes HTTPS
angemeldet, ein Gerät per JSON/CSRF erfasst (201) und die Detailansicht geprüft.
Das erfasste Gerät blieb auch nach dem finalen Update und der Wiederholung erhalten.
Die Entwicklung auf dem Arbeitsplatz wurde ebenfalls aktualisiert: vorher ein
PostgreSQL-Backup mit Dateimodus 0600 unter `.qa/t06-development.dump`, Migration,
Neuerstellung ausschliesslich des App-Containers aus dem geprüften Image und
geprüftes Nachladen der lokalen Nginx-Konfiguration. Bestehende Daten bleiben erhalten.

## Offene Freigaben

Die anschliessende Klärung der ZAP-Formularbefunde und des Browserfehlers ist im
[DAST-Nachweis](dast.md) dokumentiert. Der bestehende aktive Scanner verwendet
keinen angemeldeten Benutzer; seine Ergebnisse belegen
keine authentifizierte DAST-Abdeckung der neuen Geräteoberfläche. Die Berechtigungs-
und Eingabeprüfungen der Gerätefunktionen sind durch Integration und Browser
belegt. Kein Scannerbefund wurde unterdrückt und keine vollständige Sicherheits-
oder Produktionsfreigabe behauptet. GitHub-Actions-Abnahme und produktiver Release
bleiben nach dem Commit auszuführen.


## Ursprüngliches ZAP-Ergebnis und Abschluss

Der aktive Lauf nach CSP-Korrektur auf `artifacts/t06` endete mit
`blocking_findings`. Sanitisierter Bericht: `reports/security/t06/zap.json`.
Regel 40018: 6 Instanzen, Risiko 3, Konfidenz 2.

Die anschliessende rein darstellungsbezogene Anpassung für leere/kurze Listen
liegt in `artifacts/t06-final`. Auf diesem finalen Image wurden Browser-, statische
Security-, Container- und Ansible-Prüfungen erneut durchgeführt; der aktive ZAP-Lauf
wurde für diese letzte Darstellungsanpassung nicht nochmals wiederholt. Er ist
somit ausdrücklich kein vollständiger DAST-Nachweis für den finalen Image-Digest.
Zum damaligen Abschluss blieben die SQL-Injection-Verdachtsfälle ungeklärt;
positive Integrationsprüfungen ersetzten diese Klärung nicht. Die spätere
Untersuchung und der erfolgreiche aktive Nachlauf stehen in [docs/dast.md](dast.md).

Alle selbst angelegten kurzlebigen Integrations-, Browser-, DAST- und
Ansible-Testcontainer wurden nach Abschluss entfernt. Die normale lokale
Entwicklungsumgebung bleibt verfügbar. Es wurden keine Änderungen gestaged,
committed, gepusht oder in Produktion ausgerollt.
