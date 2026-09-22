# T07 – Reparaturfälle, Schritte und Status

Stand: 22. September 2026. Bezug: M02–M03, F04–F07, N02–N04, N06.
Umfang und Bedienung: [Reparaturverwaltung](repairs.md).

## Umsetzung und Architektur

Sieben frameworkfreie vertikale Slices mit eigenen Commands und Repository-Ports
unter `app.domains.repairs`. Keine Imports von Flask, ORM, Datenbanktreibern oder
konkreten Adaptern; keine Slice-Querverbindungen. Datenadapter implementieren
Ports, die Composition Root injiziert sie. Webrouten verwenden Handler und
unveränderliche DTOs, keine ORM-Abfragen. Schritte bleiben in der Reparaturdomäne;
Ersatzteile und Kosten werden nicht vorgezogen.

Erfassung, Fehlerbeschreibung, Schritte und Status speichern per AJAX mit
normalem HTML-/POST-Rückfall. Bootstrap und Humble Objects folgen dem bestehenden
Markensystem. Deutsche Texte kommen aus gettext, URLs bleiben Englisch. Listen
und Schrittbereiche sind auf 20 Einträge je Seite begrenzt. Gespeichert wird der
aktuelle Stand, kein zusätzliches Audit-Protokoll.

## Fachliche Abnahme

| Kriterium | Nachweis |
| --- | --- |
| Neuer Fall offen; Beschreibung und Schritte dauerhaft gespeichert | Domain-, PostgreSQL- und Browserablauf |
| Übersicht/Detail stimmen überein; abgeschlossener Fall wieder in Bearbeitung | Integration und E2E |
| Expliziter Erledigungszustand, wiederholtes Speichern dreht ihn nicht um | Domain, Integration, Presenter |
| Leere/überlange/falsch typisierte Texte, Steuerzeichen, ungültige Zustände | Domain und Integration |
| Fremde und unbekannte Geräte/Fälle/Schritte abgewiesen; fremder Schritt auch an eigenem Fall | Eigentumsprüfungen vor Validierung und beim Schreiben, Integration mit zwei Benutzern |
| CSRF auch für JSON; keine anonyme Änderung; Nutzereingaben escaped | PostgreSQL-/HTTP-Integration |
| DB-Constraints und atomarer Rollback | Echte PostgreSQL-Tests |
| Migration erhält vorhandene Benutzer und Geräte | Upgrade ab `0002_devices`, lokale Bestandsmigration |
| Entwürfe bei AJAX-Aktualisierung erhalten, Netzfehler wiederholbar | Presenter und Browser |
| Deutsch/Englisch, JavaScript und HTML-Rückfall, mobile Darstellung | Vier Browservarianten |

## Automatisierte Prüfungen

- `uv run --locked python scripts/check_architecture.py`: bestanden.
- `uv run --locked pytest tests/unit -q`: **524 bestanden**, einschliesslich
  Architektur- und Übersetzungsprüfungen sowie 92 Reparatur-Domaintests.
- `node --test tests/unit/frontend/*.test.mjs tests/unit/ci/*.test.mjs`:
  **56 bestanden**, davon 24 Frontend- und 32 ZAP-Adaptertests.
- `.qa/t04/run-integration.py`: **223 Integrationstests bestanden** gegen
  kurzlebiges PostgreSQL; anschliessend Migration einer leeren Datenbank und
  Modelldriftprüfung erfolgreich. Die alte erwartete Tabellenliste wurde um die
  beiden neuen Tabellen ergänzt. Bestehende Bibliotheks-Deprecation-Warnungen.
- Ruff, Formatprüfung und `git diff --check`: bestanden.
- Finaler Produktionsimage-Browserlauf: 35 bestehende E2E-Fälle bestanden.
  Nach Korrektur der neuen Testmessung alle vier Reparaturvarianten bestanden
  (`tests/e2e/test_repairs.py --image-artifacts artifacts/t07-final`): insgesamt
  **39 Browserfälle erfolgreich geprüft**, Berichte unter `reports/test/`.
  Deutsche und englische mobile Screenshots unter `reports/t07/` visuell geprüft.
- Produktionsimage mit `scripts/ci/images.py build --directory artifacts/t07-final
  --commit "$(git rev-parse HEAD)"` gebaut und auf Bereitschaft geprüft.
  Basiscommit: `0901b5f8b724d03fdeb80421c015730a13fa7e7a`; die T07-Änderungen sind
  noch nicht committed. Das Label ist kein Nachweis eines veröffentlichten Releases.
- App-Image: `sha256:559b250ccbd4ea92a70552965f27f78a31597f722de0fc0391895cecf3a4047b`.
- Dependency-, Bandit-, Gitleaks- und alle drei Containerprüfungen bestanden;
  `reports/security/t07-final/security-summary.json`. Bestehende explizite
  PostgreSQL-Ausnahme unverändert, keine zusätzliche Ausnahme. Ein lokaler
  Wiederholungslauf fand zunächst pip-audit/Bandit nicht im PATH; nach Korrektur
  des Werkzeugpfads wurden sämtliche Scanner erfolgreich ausgeführt.
- Aktiver ZAP-Scan auf dem finalen Image: **bestanden**, Exit 0, nur fünf
  Informationskategorien, keine blockierenden Befunde. 1 300 SQL-Injection-Requests,
  DOM-XSS vollständig, keine fehlgeschlagenen Abdeckungsprüfungen. Bericht:
  `reports/security/t07-final/zap.json`. Auch der erste T07-Image-Stand bestand.

Der erste Browserlauf ergab 37 erfolgreiche Tests und zwei Fehler, weil der neue
Test unmittelbar nach dem AJAX-Klick neu lud und damit die Speicheranfrage
abbrechen konnte. Er wartet jetzt auf den aktualisierten serverseitigen Wert.
Ein früher gezielter Wiederholungslauf bestand; dabei konnte die Erkennung
der JavaScript-Variante noch auf HTML-Rückfall ausweichen. Die endgültige Prüfung erwartet
JavaScript ausdrücklich aus der Testkonfiguration, wartet auf die Anbindung und
prüft zusätzlich den Erhalt eines vorübergehend geleerten Entwurfs. Ein weiterer
Testfehler war die Interpretation von Playwrights `framenavigated`: Auch
`history.replaceState` meldet dieses Ereignis. Die AJAX-Prüfung zählt jetzt
tatsächliche Dokumentanfragen, ohne URL-Änderungen im selben Dokument zu verbieten.

## Deployment und Datenbestand

Isolierter Docker-in-Docker-Testhost aus `scripts.prepare_deployment_test`, eigenes
SSH-Schlüsselpaar, lokale Registry und Test-CA; keine Produktionszugänge. Tatsächlich
aufgerufen mit dem lokalen Inventory und den generierten Controller-Einstellungen:

```bash
ansible-playbook -i tests/deployment/inventory.yml deploy/ansible/deploy.yml \
  --extra-vars @.qa/t07-deployment/release.json
```

- Erstlauf: `ok=77`, `changed=32`, `failed=0`.
- Identische Wiederholung: `ok=46`, **`changed=0`**, `failed=0`.
- Finales App-Image in die isolierte Registry übernommen und über dasselbe
  Playbook aktualisiert: `ok=67`, `changed=21`, `failed=0`. Anschliessend CA-geprüftes HTTPS und authentifizierte
  Browser-Anlage eines Falls mit Schritt und Statusänderung erfolgreich;
  Neuladen bestätigt die Persistenz.
- Wiederholung des finalen Releases: `ok=46`, **`changed=0`**, `failed=0`.
  Der zuvor erfasste abgeschlossene Testfall blieb erhalten.

Lokale Entwicklung: Vor der Migration ein PostgreSQL-Custom-Backup unter
`.qa/t07/development-before.dump` mit Modus 0600 erstellt. Migration mit dem neuen
App-Image explizit ausgeführt: `0003_repairs`. Anschliessend **2 Benutzer und
103 Geräte unverändert vorhanden**, neue Fall-/Schritttabellen zunächst leer.
Nur der App-Container wurde erneuert und Nginx nachgeladen.
Der lokale Bereitschaftscheck antwortet erfolgreich. Keine neuen
Environment-Variablen oder Secrets erforderlich.

Die eigens erzeugten Integrationstest-, Browser-, DAST- und Ansible-Testcontainer
wurden nach Abschluss entfernt; die lokale Entwicklungsumgebung läuft weiter.

## Grenzen der Prüfung

ZAP prüft aktiv die öffentliche, nicht angemeldete Oberfläche der isolierten
CI-Instanz. Das ist keine authentifizierte DAST-Abdeckung der Reparaturseiten;
deren Zugriffs-, CSRF-, Validierungs- und Escaping-Regeln sind durch automatisierte
Integrations- und Browserprüfungen abgesichert. Keine Scannerregeln abgeschwächt.

Das Produktionsdeployment und der GitHub-Actions-Lauf aus dem eingecheckten
Release sind nicht Bestandteil des lokalen Nachweises. Ein Tag/Release muss die
bestehende Pipeline mit dem endgültigen Commit durchlaufen. T08 (Teile,
Arbeitswerte und Kosten) und T09 (fachliche REST-API) bleiben offen.

## Ergänzung: konsistente virtuelle Reparaturliste

Auf Benutzerwunsch verwendet die Reparaturliste jetzt dieselbe Scrollsteuerung
wie die Geräteliste: 20 Zeilen serverseitig, maximal 60 im virtuellen AJAX-Fenster,
112 px Zeilenhöhe, gleiche Marken-Scrollbar und erhaltene Scrollposition bei
Rückkehr aus Details. Seitenlinks bleiben nur als Rückfall ohne JavaScript.
Gerätefilter bleiben bei Fensterwechsel und Detail-Rückkehr erhalten.
Die Datenadapter begrenzen jedes Fenster nach Eigentümer, Gerätefilter und oberer
Fall-ID; Neuanlagen verschieben eine geöffnete Liste nicht. Keine neue Migration,
Abhängigkeit oder Environment-Variable.

Prüfungen des ergänzten Stands:

- 532 Python-Unit-Tests, darunter 100 Reparatur-Domain- und 97 Architekturtests.
- 224 PostgreSQL-Integrationstests, leere Migration und Modelldriftprüfung bestanden.
- 56 JavaScript-Tests einschliesslich gemeinsamem Presenter und Scanner-Adapter.
- 14 gezielte Geräte-/Reparatur-Browsertests bestanden: SSR, begrenzter DOM,
  Vor-/Zurückscrollen, Netzfehler/Wiederholung, Detail-Rückkehr, Filter, Englisch/
  Deutsch und HTML-Fallback. Mobile Screenshots unter `reports/repair-scroll`
  visuell geprüft.
- Produktionsimage unter `artifacts/repair-scroll` gebaut und auf Bereitschaft
  geprüft; Dependency-, Bandit-, Gitleaks- und drei Containerprüfungen bestanden
  (`reports/security/repair-scroll`). Ruff, Architektur-Skript und Diff-Prüfung
  ebenfalls bestanden. ZAP und Ansible wurden für diese Ergänzung nicht erneut
  ausgeführt; die früheren Nachweise gelten für den damaligen Image-Stand.

Die lokale App wurde aktualisiert; die 101 Fälle von `example` bleiben erhalten.
Der gemeinsame JS-Code ersetzt die bisherige gerätespezifische Fenstersteuerung;
DOM-Renderer bleiben pro Liste getrennt. Fachlogik bleibt in den jeweiligen
frameworkfreien Python-Slices, nicht im Browser.
