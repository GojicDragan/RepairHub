# T08 – Prüfnachweis Ersatzteile und Kosten

Prüfdatum: 22. September 2026. Lokal bearbeiteter Stand auf Basis von
`4b1e93ece5b217f0a132414f842efe5001698ff3`; kein Nachweis eines veröffentlichten
Commits. Funktion und Grenzen: [Teile und Kosten](parts-and-costs.md).

## Umsetzung

- Zwei frameworkfreie Teile-Slices und ein Arbeitswerte-Slice mit eigenen Ports,
  Commands und konkreter Injection in `app.bootstrap`.
- Kostenberechnung in `costs`, unabhängig von Flask, ORM, DB und anderen Domänen;
  Aufrufe ausschliesslich über Reparatur-/Teiledomäne.
- Additive Migration `0004_parts_and_work`, keine gespeicherten Gesamtbeträge.
- AJAX und HTML-Fallback mit gemeinsamen Server-Anwendungsfällen, CSRF,
  eigentumsgebundenen Abfragen und vollständiger englischer/deutscher Oberfläche.
- Bestehendes Branding und Humble Objects; maximal 20 Teilepositionen im Detail.

## Lokale Prüfungen

- **587 Unit-Tests** bestanden, einschliesslich 97 Architekturtests und 56 neuen
  Kosten-/Teile-/Arbeitswerttests. Architektur-Skript bestanden.
- **56 JavaScript-Tests** bestanden. Ruff, Formatprüfung und Diff-Prüfung bestanden.
- Ansible-Lint bestanden (Profil production).
- **250 PostgreSQL-/Integrationstests** über Gesamtlauf und gezielte Wiederholungen
  abgedeckt: 226 bestehende Tests grün im Gesamtlauf, 24 abschliessend grüne
  Teile-/Migrationstests im gezielten Lauf. Leere Migration und Schemaabgleich
  ohne neue Upgrade-Operationen bestanden.
  Der initiale Test erwartete für Infinity ausschliesslich einen Constraintfehler;
  PostgreSQL lehnt den Wert bereits als Zahlenüberlauf ab. Die Test-Erwartung wurde
  präzisiert und der betroffene Prüfbereich erneut ausgeführt.
- 11 Browserprüfungen bestanden: Reparaturabläufe sowie neue Teile-/Kostenabläufe
  in Englisch und Deutsch, mit AJAX und ohne JavaScript. Mobile Screenshots unter
  `reports/t08/` visuell geprüft; kein horizontaler Überlauf.
- Produktionsimage gebaut und isolierter Start-/HTTPS-Test mit PostgreSQL,
  Nginx und produktiver Hostbeschränkung bestanden.
- Dependency-, Bandit-, Gitleaks- und Container-Scans bestanden. Bestehende,
  ausdrücklich freigegebene PostgreSQL-Ausnahmen bleiben unverändert.
- Isolierter Ansible-Prüfstand mit eigenem Docker-Daemon: Erstdeployment
  `changed=32`, identische Wiederholung `changed=0`; Konfigurationsupdate
  desselben geprüften App-Images `changed=21`, Wiederholung `changed=0`.
  Ungültiger Anwendungsschlüssel führte beim Migrationsstart zum erwarteten Fehler
  (`failed=1`, `rescued=1`); kompatibler Rückweg erfolgreich, Container unverändert.
  Wiederaufnahme mit gültigen Werten erfolgreich, erneute Wiederholung `changed=0`.
  Container-IDs und Startzeiten bei Wiederholungen ausdrücklich verglichen;
  Infrastrukturcontainer auch beim App-Konfigurationsupdate unverändert.
  Externes HTTPS mit Fixture-CA geprüft. Logs unter `.qa/t08-deployment/`;
  wegwerfbarer Testhost anschliessend entfernt.
- Aktiver öffentlicher ZAP bestanden (Exit 0), ausschliesslich informative
  Befunde: 1300 SQL-Injection-Testanfragen, DOM-XSS-Regel vollständig beendet,
  keine fehlgeschlagenen Abdeckungsprüfungen. Bericht: `reports/security/t08/zap.json`.

## Lokale Entwicklungsdaten

Vor Schemaänderung geschützter `pg_dump` unter `.qa/t08-local/before.dump`.
Migration und neues lokales App-Image gestartet; Bereitschaft HTTP 200.
Alle 103 Geräte und 101 Reparaturfälle erhalten, Schema auf `0004_parts_and_work`.
Keine Produktionsverbindung und keine Änderung produktiver Daten.

## Grenzen

Die später mit T09 einzuführende authentifizierte API bleibt nicht anwendbar.
Der öffentliche ZAP-Scan deckt keine authentifizierten Teile-Endpunkte ab;
deren Eigentumsschutz, CSRF und Validierung werden durch Integration und Browser
gesichert. Die vollständige Teilebasis wird für die exakte Summe im Speicher
materialisiert; die Darstellung ist paginiert. Kein Löschen, Lager oder Steuerlogik.
Externe GitHub-Pipeline und Produktionsabnahme nach Commit/Release bleiben offen.

## Nachprüfung der lokalen statischen Dateien

Nach Benutzerhinweis auf übergrosse Darstellung lieferten die lokalen CSS- und
JavaScript-URLs HTTP 404: Der bestehende Nginx-Container sah einen leeren
Static-Bind-Mount, obwohl die Dateien im Workspace vorhanden waren. Der zuvor
geprüfte Bereitschaftsendpunkt erfasst diesen Fehler nicht. Nur den lokalen
Nginx-Container neu erstellt, um den aktuellen Quellpfad erneut einzubinden;
keine Änderung von Datenbank oder Anwendungs-CSS dafür erforderlich.
Anschliessend Startseite und Anmeldung in Chromium geprüft: beide Stylesheets
und JavaScript erfolgreich geladen, Logo 38 px breit, Grundschrift 16 px,
kein horizontaler Überlauf. Screenshots unter `reports/ui-diagnosis/`.
