# T12 – Gesamtabnahme und Testprotokoll

Prüfdatum: **22. September 2026**, Zeitzone Europe/Zurich. Geprüfter Quellstand:
`4b59e03022a3c669136ebd4499b096fcad3efcdb`. Der Arbeitsstand war vor den Prüfungen sauber.
Die nachfolgenden Dokumentationsänderungen verändern die geprüfte Anwendung nicht.

Dieses Protokoll fasst zwölf ausgewählte Abnahmefälle zusammen. Die Ausführung
ist durch automatisierte Unit-, PostgreSQL-, Browser-, Security- und Deployment-
Prüfungen belegt; sie wird nicht als manuell durchgeführter Benutzertest ausgegeben.
Die Zahl automatisierter Einzeltests ist nicht auf zwölf begrenzt.

## Voraussetzungen und abgegrenzte Umgebungen

- Lokale Testdatenbank: isolierter PostgreSQL-17-Container mit kurzlebigen Zugängen;
  jeder Integrationstest erhält ein getrenntes Schema. Kein SQLite-Ersatz.
- Browser: Chromium gegen die archivierte Produktionsimage-Kombination aus
  Nginx, Gunicorn/App, PostgreSQL und Garage. Eigene Test-CA und Loopback-Port;
  Registrierungsmails werden ausschliesslich im isolierten SMTP-Empfänger abgefangen.
- Konten A/B: von den jeweiligen Fixtures erzeugte getrennte Benutzer. Geräte,
  Fälle, Schlüssel und Bilder der Fixtures gehören nicht zu Produktionsbenutzern.
- Deployment: vorbereiteter isolierter SSH-/Docker-in-Docker-Host; kein Zugriff
  auf den Docker-Socket des Arbeitsplatzes und keine Produktionsänderung.
- Produktion: ausschliesslich lesende HTTPS-/API-Prüfungen auf `lab19.ifalabs.org`.
  Der bereitgestellte Systemschlüssel wird nicht in diesem Protokoll, Testdateien,
  Beispielbefehlen oder Berichten gespeichert. Keine Konten oder Fälle dort erzeugt.

Die neueren Benutzerentscheidungen gelten: persönliche beziehungsweise zentrale
API-Keys im Authorization-Bearer-Header statt des alten Token-Ausstellungsplans;
Passwort-Recovery und E-Mail-Verifikation sind enthalten. Datenbank-Restore wird
nur dokumentiert. Gelöschte Bilder verlieren ihren Datenbankverweis, die privaten
Objekte bleiben für konsistente Sicherungen erhalten.

## A01 – Registrierung, Verifikation und Passwort-Recovery

**Bezug:** M01, F01, N01, N03, N06. **Voraussetzung:** frische Identitätsdatenbank und
isolierter Mail-Empfänger. **Schritte/Testdaten:** gültige Registrierung durchführen;
vor und nach Bestätigung anmelden; doppelte Identität, ungültige E-Mail, kurze bzw.
unterschiedliche Passwörter und fehlendes CSRF senden. Gleiche Passwörter in zwei
Konten speichern. Reset-Link verwenden und Wiederverwendung/Manipulation prüfen.

**Soll:** Anmeldung erst nach Bestätigung; eindeutige Identitäten; gesalzene Hashes,
keine Klartextpasswörter; generische Reset-Antworten; abgelaufene oder bereits
verwendete Links unwirksam. Keine Teilkonten nach SMTP-/Transaktionsfehlern.
**Ist/Status:** **bestanden**. Registrierung, SMTP, Recovery und negative Varianten
im aktuellen Integrationslauf erfolgreich; Bestätigung über eine echte Testmail
zusätzlich im vollständigen Browserablauf nachgewiesen.
**Nachweis:** `tests/integration/users/test_registration.py`, `test_smtp.py`,
`test_password_reset.py`; `tests/e2e/test_registration.py`.

## A02 – Anmeldung, Sitzung und Abmeldung

**Bezug:** M01, F02, N01–N02. **Voraussetzung:** bestätigtes Konto A.
**Schritte/Testdaten:** per Benutzername und E-Mail anmelden; falsches Passwort,
manipulierte Cookies und fehlendes CSRF prüfen; Remember-Sitzung wiederherstellen;
Konto deaktivieren bzw. Passwort zurücksetzen; abmelden und private URL erneut aufrufen.

**Soll:** Nur gültige, aktive Identität wird übernommen; sichere Cookieattribute;
ungültige Sitzung wird nicht als Zugriff anerkannt; Abmeldung beendet den Zugang.
**Ist/Status:** **bestanden**. Sitzungs-, Remember-, CSRF- und Passwortfehlerpfade
wurden ohne Datenpreisgabe abgearbeitet.
**Nachweis:** `tests/integration/users/test_sessions.py`,
`tests/integration/users/test_registration.py`; `tests/e2e/test_workspace_errors.py`.

## A03 – Geräte, Eigentumsprüfung und virtuelle Liste

**Bezug:** M02, F03, N02–N04, N06. **Voraussetzung:** getrennte Konten A/B.
**Schritte/Testdaten:** Gerät mit Name, Hersteller und Modell erfassen und bearbeiten;
leere Werte und manipulierte IDs senden; dasselbe Gerät als B lesen/bearbeiten;
mehrere Listenfenster laden, während weitere Geräte entstehen; Detail öffnen und zurückgehen.

**Soll:** dauerhafte eigene Daten, gleiche 404-Behandlung für fremd/unbekannt;
atomare Fehlerbehandlung; begrenzte Listenfenster und erhaltene Scrollposition.
**Ist/Status:** **bestanden**. Direkte AJAX-Aufrufe bleiben begrenzt; Browserliste,
Formularzustände und Eigentumsfilter bestanden. SQL-Constraints und Rollback geprüft.
**Nachweis:** `tests/integration/devices/test_devices.py`, `tests/e2e/test_devices.py`.

## A04 – Fälle, Fehlerbilder, Schritte und Status

**Bezug:** M02–M03, F04–F07, N02–N03. **Voraussetzung:** eigenes Gerät von A.
**Schritte/Testdaten:** Fall anlegen; Fehlerbeschreibung und Schritte bearbeiten;
Schritte abschliessen; Offen → In Bearbeitung → Abgeschlossen → Wiederaufnahme;
leere Beschreibung, unbekannten Status und fremde Zuordnungen übermitteln.

**Soll:** neuer Fall offen; erlaubte Statuswechsel einschliesslich Wiederaufnahme;
keine leeren Pflichttexte oder Änderungen fremder Objekte; Daten bleiben bei Fehler erhalten.
**Ist/Status:** **bestanden**. Zustandsfolge, Schrittfenster und HTML-/AJAX-Abläufe
bestehen; persistente Beziehungen und fehlgeschlagene Transaktionen sind abgesichert.
**Nachweis:** `tests/integration/repairs/test_repairs.py`, `tests/e2e/test_repairs.py`.

## A05 – Teile, Arbeitswerte und exakte Kosten

**Bezug:** M04–M05, F08–F11, N03, N05. **Voraussetzung:** eigener Reparaturfall.
**Schritte/Testdaten:** 2 Stunden × CHF 80 plus 3 Teile × CHF 15; danach ohne Teile;
separat 3 × CHF 0.10. Werte ändern; Menge 0/1.5, negative Zahlen, NaN, Infinity,
Überläufe und manipulierte Client-Gesamtsumme übermitteln.

**Soll:** CHF **205.00**, **160.00**, **0.30**; gemeinsame Decimal-Berechnung,
ROUND_HALF_UP, keine Übernahme frei gesendeter Gesamtkosten. Ungültige Eingaben
verändern den gespeicherten Zustand nicht.
**Ist/Status:** **bestanden**. Alle Referenzbeträge und Grenzfälle bestanden;
UI, API und PDF beziehen ihre Kosten aus derselben Domänenberechnung.
**Nachweis:** `tests/unit/domains/costs/test_costs.py`,
`tests/integration/parts/test_parts.py`, `tests/integration/repairs/test_report.py`.

## A06 – Persönliche und zentrale API-Schlüssel

**Bezug:** M06, F12–F13 gemäss neuer API-Key-Entscheidung, N01–N02, N07.
**Voraussetzung:** A/B mit getrennten Fällen, persönlicher Schlüssel A und expliziter
System-Lesezugang. **Schritte/Testdaten:** Schlüssel im Frontend erzeugen; einmalige
Klartextanzeige prüfen; mit browserunabhängigem Client Liste/Detail lesen; Schlüssel
ersetzen und widerrufen; Systemschlüssel für systemweite Leseauskunft verwenden.

**Soll:** persönlicher Schlüssel sieht nur eigene Fälle; Hash statt Klartext speichern;
alter Schlüssel verliert Zugriff. Systemschlüssel liest systemweit und erhält keinen Schreibzugang.
**Ist/Status:** **bestanden**. Isolierte API-/Browserprüfungen bestanden. Zusätzlich
Produktion: gültiger Systemschlüssel liefert HTTP 200 und korrektes Listenschema;
Bestand bei Prüfung leer. Daher kein positiver Produktions-Detailabruf behauptet.
**Nachweis:** `tests/integration/test_api.py`, `tests/unit/domains/users/test_api_keys.py`,
`tests/e2e/test_api.py`; `reports/t12/production-api-validation.json`.

## A07 – API-Fehler und Zugriffsgrenzen

**Bezug:** M06, F13–F14, N02, N07. **Voraussetzung:** Fälle von A/B im isolierten Bestand.
**Schritte/Testdaten:** fehlende, fehlerhafte und widerrufene Schlüssel; fremde/unbekannte
Fall-ID; unzulässige Schreibmethoden; manipulierte Benutzer-/Queryparameter prüfen.

**Soll:** 401 ohne gültigen Schlüssel; 404 für fremd/unbekannt; 405 für nicht erlaubte
Methoden; JSON-Fehler und keine Datenänderung. Benutzerparameter erteilen keine Rechte.
**Ist/Status:** **bestanden**. Isoliert vollständig geprüft. Produktion zusätzlich:
fehlender und ungültiger Schlüssel 401; unbekannte Detail-ID mit gültigem Schlüssel 404.
Keine schreibenden Produktionsrequests ausgeführt.
**Nachweis:** `tests/integration/test_api.py`, `tests/e2e/test_api.py`;
`reports/t12/production-api-validation.json`.

## A08 – Transaktionen, Migration und Datenerhalt

**Bezug:** M02–M04, N03–N04. **Voraussetzung:** PostgreSQL und Testfixtures.
**Schritte/Testdaten:** leere Datenbank migrieren, Upgrade wiederholen, ORM/Schema
abgleichen; fehlende Eltern/ungültige Werte erzwingen; Speicher-/Commitfehler
simulieren; Bilder in Garage speichern und dessen Container neu starten.

**Soll:** wiederholbare Migration ohne Duplikate; DB-Constraints; atomarer Rollback;
Datenerhalt beim Neustart; kein datenlöschendes Downgrade im Regelbetrieb.
**Ist/Status:** **bestanden**. Migration und Modellabgleich erfolgreich, Transaktions-
fehler ohne Teiländerungen. Echte Garage-Bilder bleiben nach Neustart abrufbar.
Zusätzlich wurde der PostgreSQL-Container der Fixture vollständig neu erstellt:
identisches benanntes Volume, unveränderte nichtleere Benutzer-/Geräte-/Fallbestände;
anschliessender HTTPS-/API-Check erfolgreich und Deployment weiterhin `changed=0`.
**Nachweis:** `tests/integration/users/test_registration.py`,
`tests/integration/repairs/test_repairs.py`, `tests/integration/images/test_images.py`.

## A09 – Browser, Sprache, Fehlerseiten und HTTPS

**Bezug:** M07, F15, N06–N07, N09. **Voraussetzung:** archivierte Produktionsimages,
isolierte HTTPS-Umgebung. **Schritte/Testdaten:** vollständigen Ablauf von Registrierung
bis Kostenanzeige mit/ohne JavaScript und Deutsch/Englisch durchführen; mobile
Ansichten, 404, Netzwerkabbruch und abgelaufene Sitzung prüfen.

**Soll:** bedienbare Oberfläche, sichtbare Fehler und erhaltene zulässige Eingaben;
keine internen Fehlerdetails; korrekte Sprachwahl; geprüfte HTTPS-Verbindung.
**Ist/Status:** **bestanden**. 65 Browserfälle im Gesamtlauf erfolgreich. Separater
HTTPS-/API-Smoke-Test bestanden. Produktions-Startseite und `/health/ready` liefern
HTTP 200 mit regulär geprüfter TLS-Verbindung.
**Nachweis:** `tests/e2e/`, `tests/integration/app/`,
`reports/build/smoke.json`, `reports/t12/public-production.json` und spätere API-Wiederholung.

## A10 – Backup, Betrieb und ausdrücklich nicht ausgeführter Restore

**Bezug:** N04, N08–N09; T11-Benutzerentscheidung. **Voraussetzung:** geschützte
Backup-Ziele und vorhandene Betriebsanleitung. **Schritte/Testdaten:** Bildexport
mit Manifest/Prüfsummen und verschlüsselte Datenbank-/Objektarchive prüfen;
richtige/falsche Passphrase sowie unvollständigen Export abdecken; Restore-Anleitung abgleichen.

**Soll:** geschützte vollständige Artefakte, kein Klartext in veröffentlichten
Backups, keine Überschreibung vorhandener Sicherungen. Datenbank-Restore nur als
Verfahren dokumentieren; seine Ausführung ausdrücklich ausweisen.
**Ist/Status:** **vereinbarter Dokumentationsumfang erfüllt**; Export und
Verschlüsselungsprüfungen bestanden. **Datenbank-/Gesamtrestore nicht durchgeführt**
(auf ausdrücklichen Benutzerwunsch). Kein Nachweis einer praktisch erfolgreichen
Datenbankwiederherstellung und kein vorzeitig bestätigter Vierwochenbetrieb.
**Nachweis:** `tests/unit/ci/test_backup_encryption.py`,
`tests/integration/images/test_images.py`, [Betrieb](operations.md), [Garage](garage.md).

## A11 – CI/CD, Security und idempotentes Deployment

**Bezug:** T02, N03–N05, N07–N10. **Voraussetzung:** geprüfte Image-Archive und isolierter
vorbereiteter Deployment-Host. **Schritte/Testdaten:** Test/Build/Security ausführen;
Scannerfehler und blockierende Befunde prüfen; ersten Deploy und Wiederholung;
App-Konfigurationsupdate und gezielt falschen API-Smoke-Schlüssel in der Fixture
verwenden; kompatible Rückkehr und erneute unveränderte Ausführung prüfen.

**Soll:** Scanner-/Abnahmefehler blockieren; nur geprüfte Images; unveränderte
Wiederholung ohne Container-Neustarts; fehlgeschlagener Release bleibt fehlgeschlagen,
auch wenn die vorige kompatible Anwendung wiederhergestellt wird. Kein DB-Downgrade.
**Ist/Status:** **bestanden**. Erstlauf, Wiederholung, Konfigurationsupdate,
gezielter Smoke-Fehler mit erfolgreichem kompatiblem App-Rollback sowie anschliessende
Wiederherstellung und Wiederholung bestanden. Beide unveränderten Wiederholungen
melden `changed=0`; IDs und Startzeiten aller vier Container bleiben dabei gleich.
Unit-/Prozessprüfungen, Security einschliesslich aktiver ZAP-Prüfung bestanden.
Release `v0.9` mit demselben Commit: Test, Build, Security, Publish und Deploy erfolgreich.
**Nachweis:** `tests/integration/ci/test_security_process.py`, `tests/unit/ci/`,
`reports/t12/deployment.json`, [Release-Lauf](https://github.com/GojicDragan/RepairHub/actions/runs/35771339154).

## A12 – Optionale Funktionen: Suche, Übersicht, Bilder und PDF

**Bezug:** K01–K04, F16–F19, N02, N05–N06.
**Voraussetzung:** getrennte Konten und eigene Geräte/Fälle mit verschiedenen Statuswerten.
**Schritte/Testdaten:** Geräte-/Fallsuche mit Teilwörtern, Wildcards und Statusfilter;
Statusübersicht und leeren Bestand prüfen. JPEG/PNG/WebP hochladen, falsche Inhalte,
Übergrösse und fremden Zugriff prüfen; eigenes Bild mit Bestätigung löschen.
PDF mit 25 Schritten und 25 Teilen herunterladen; Kosten und Seitengrenzen vergleichen.

**Soll:** eigene gefilterte Treffer, begrenzter DOM und Debounce; korrekte Statuszahlen;
private validierte Bilder im Mosaik; gelöschte Verweise nicht abrufbar. Vollständiger,
mehrseitiger Deutsch-/Englisch-PDF-Bericht mit gleichen Kosten und Eigentumsprüfung.
**Ist/Status:** **bestanden**. Suche, Statistik, Bild- und PDF-Tests einschliesslich
Browserabläufen erfolgreich. PDF enthält die 25. Position trotz Browser-Pagination;
Beispieltotal **CHF 349.75** stimmt überein. Bildlöschung bedeutet derzeit keine
physische Bereinigung der privaten Garage-Objekte; dies ist dokumentiert.
**Nachweis:** `tests/integration/devices/test_search.py`,
`tests/integration/repairs/test_filters.py`, `test_status_overview.py`, `test_report.py`,
`tests/integration/images/`, `tests/e2e/test_images.py`, `test_report.py`.

## Gesamtbewertung und Evidenz

Die zahlenmässigen Ergebnisse, Release-/Image-Zuordnung, tatsächlichen Befunde und
verbleibenden Grenzen stehen im [T12-Prüfnachweis](t12-validation.md).
Die öffentlichen Produktionsprüfungen ersetzen weder die isolierten Negativtests
noch einen tatsächlich ausgeführten Restore. Es wurden keine Produktionsdaten
für die Abnahme verändert.
