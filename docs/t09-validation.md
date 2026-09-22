# T09 – Arbeitsnachweis: persönliche API-Keys

Stand: 22. September 2026. Lokaler Arbeitsstand auf Basis von
`a189e04fffc62ef85953b738fd23342c570dab90`. Die jüngste Benutzerentscheidung ersetzt
die vorherige Token-Ausstellung durch persönliche API-Keys aus dem Frontend.

## Umsetzung

- Generieren, Ersetzen und Widerrufen unter `/account/api-key`, deutsch/englisch,
  im bestehenden Bootstrap-Design und ohne JavaScript benutzbar. Schlüssel nur
  einmal anzeigen, niemals in Session/Flash speichern; CSRF und `no-store`.
- Authentifizierung ausschliesslich über `Authorization: Bearer <api-key>`.
  Keine Benutzername-/Passwortparameter, kein `X-API-Key`, kein Token-Endpunkt.
- `GET /api/repairs` mit begrenzten Seiten und Snapshot sowie
  `GET /api/repairs/{id}` mit vollständigen Schritten, Teilen und CHF-Kosten.
  Vorhandene Reparatur-Anwendungsfälle sichern Eigentum und Kosten gemeinsam
  mit dem Browser. Keine direkten Datenzugriffe in Routen.
- Vier frameworkfreie Benutzer-Slices mit eigenen Ports/DTOs, expliziter Injection
  und technischem Hash-/Zufallsadapter. Die spätere System-Key-Entscheidung
  ersetzt den zunächst vorhandenen Provisionierungs-Slice samt CLI.
- Additive Migration `0005_api_keys`: nullable Hash, Identitätsbindung und Zeitpunkt,
  eindeutiger Hash-Constraint. Keine neue Bibliothek; Hashing nur für zufällige
  256-Bit-Schlüssel. Details und Curl: [API](api.md).

## Prüfungen vor der Erweiterung um den Systemschlüssel

- 593 Unit-Tests, darunter 97 Architekturprüfungen, sowie Architektur-Skript
  bestanden. Fachkern weiterhin unabhängig von Flask und ORM; keine Slice-Imports
  untereinander, API weiterhin nur von Benutzer-/Reparaturdomäne abhängig.
- 278 PostgreSQL-Integrationstests bestanden. Historische Migrationstests legen
  ihre Altbestände jetzt mit den damaligen Spalten statt dem heutigen ORM-Modell
  an; der Datenerhalt bleibt geprüft. Leere Migration und Schemaabgleich ohne
  weitere Upgrade-Operationen bestanden.
- 56 JavaScript-Tests und sechs E2E-Prüfungen bestanden: Teile/Kosten und neue
  API-Key-Verwaltung in Englisch/Deutsch mit/ohne JS, unabhängiger HTTPS-Client,
  Listen-/Detailzugriff, Widerruf und mobile Darstellung ohne horizontalen Überlauf.
- Produktionsimage gebaut; isolierter HTTPS-/PostgreSQL-Smoke-Test mit eigenem
  Key, Liste/Detail, Kosten sowie negativen Zugriffen bestanden.
- Dependency-, Bandit-, Gitleaks- und Container-Scans bestanden. Bestehende
  ausdrücklich freigegebene PostgreSQL-Ausnahmen unverändert.
- Ansible-Lint (Profil production) und Syntaxprüfung bestanden. Erstdeployment
  mit API-Key-Provisionierung und beiden API-Endpunkten: `changed=33`, `failed=0`.

- Identische Ansible-Wiederholung `changed=0`; Schlüsselwechsel `changed=22`,
  anschliessend wiederum `changed=0`. IDs und Startzeiten der laufenden Container
  bleiben bei Wiederholungen erhalten; Infrastruktur auch beim Update unverändert.
- Die ersten abschliessenden Prüfungen wurden durch entfernte Testcontainer
  unterbrochen. Kein Erfolgsnachweis daraus abgeleitet; frische Instanzen verwendet.
- Auf dem neuen Testhost führt ein gültiger neuer Schlüssel mit absichtlich
  falscher Prüffall-ID zu `failed=1`, `rescued=1`, `unreachable=0`. Der Rollback
  stellt Anwendung und vorherigen Prüfschlüssel erfolgreich wieder her. Separater
  HTTPS-Aufruf bestätigt mit dem alten Key erhaltene Falldaten und CHF 205.00.
  Logs: `.qa/t09-keys-deployment/` und `.qa/t09-keys-retry/`.

- Wiederanlauf nach Rollback erfolgreich (`changed=2` für Metadaten), danach
  erneut `changed=0` mit unveränderten Container-IDs und Startzeiten. Den
  abgeschlossenen Deployment-Testhost entfernt.

- Aktiver öffentlicher ZAP auf frischer Instanz bestanden (Exit 0): 1300
  SQL-Injection-Testanfragen, DOM-XSS vollständig abgeschlossen, keine
  fehlgeschlagenen Abdeckungsprüfungen. Bericht:
  `reports/security/t09-keys-retry/zap.json`. Keine Scannerregeln abgeschwächt.

## Externe Abnahme

Alle oben beschriebenen lokalen Prüfungen sind abgeschlossen. GitHub-/Produktionsabnahme bleibt nach
Commit/Release offen; neue Prüfeingaben siehe [api.md](api.md).

## Lokale Entwicklungsdaten

Vor Migration geschütztes Backup unter `.qa/t09-keys-local/before.dump`.
Revision 0005 über einen einmaligen Compose-Migrationslauf angewendet und das
geprüfte Image lokal gestartet. Alle 103 Geräte und 101 Reparaturfälle erhalten;
Schema auf 0005, Startseite sowie eingebundene CSS-/JavaScript-Dateien HTTP 200. Keine
Produktionsverbindung oder Änderung produktiver Daten. Die öffentliche DAST-
Prüfung ergänzt die gezielten authentifizierten API-Tests, ersetzt sie aber nicht.
Die Detailantwort materialisiert weiterhin alle Positionen eines Falls.

## Erweiterung: zentraler System-Leseschlüssel

`API_SMOKE_KEY` liest nun Liste und Details aller Benutzer. Persönliche Keys
bleiben eigentumsgebunden. Kein Prüfkonto, keine feste Fall-ID oder CLI-
Provisionierung mehr; der Systemschlüssel wird über die geschützte Runtime
konfiguriert. Keine zusätzliche Migration.

Erneut geprüft: 599 Unit-Tests (darunter 97 Architekturtests), Architektur-Skript,
280 PostgreSQL-Integrationstests, Migration einer leeren Datenbank und
Schemaabgleich, Ruff sowie Ansible-Lint bestanden. Produktionsimage gebaut und
isoliert mit PostgreSQL und HTTPS geprüft. pip-audit, Bandit, Gitleaks und Trivy
bestanden; bestehende dokumentierte PostgreSQL-Ausnahmen unverändert.

Isoliertes Ansible-Deployment: Erstlauf erfolgreich; Wiederholung `changed=0`
mit unveränderten Container-IDs und Startzeiten. Schlüsselrotation erfolgreich,
alter Schlüssel danach 401, neuer Schlüssel gültig; erneute Wiederholung
`changed=0`. Ein absichtlich falscher Prüfschlüssel löste den erwarteten
Fehlerpfad aus (`failed=1`, `rescued=1`); der vorherige Systemschlüssel und
der unveränderte Fallbetrag CHF 205.00 wurden nach dem Rollback bestätigt.
Wiederanlauf erfolgreich; anschliessende Wiederholung erneut `changed=0`
mit unveränderten Containern. Testhost danach entfernt.
Browser-E2E und ZAP wurden für diese rein serverseitige Erweiterung nicht erneut
ausgeführt; ihre oben genannten Ergebnisse gelten für den vorherigen Stand.
Produktionsauslieferung und GitHub-Secrets wurden nicht verändert.
