# K-T01 – Suche und Statusfilter für Reparaturfälle

## Ergebnis und Architektur

Eigene Reparaturen lassen sich nach Suchbegriff und Status filtern, bei Bedarf
zusätzlich nach eigenem Gerät. Suche umfasst Fehlerbeschreibung, Gerätename,
Hersteller und Modell. Mehrere Teilwörter werden mit UND kombiniert; Gross- und
Kleinschreibung spielt keine Rolle. Einzelheiten: [Reparaturen](repairs.md).

Erweitert wird der bestehende vertikale Slice `list_repairs`: frameworkfreier
Command, Eingabevalidierung und injizierter Repository-Port. Der SQLAlchemy-Adapter
wendet alle Filter innerhalb der Eigentumsabfrage an, auch für Trefferzahl und
Snapshot. Keine neue Migration, Abhängigkeit, Environment-Variable oder Secret.
Webrouten bleiben ohne ORM-Zugriff; die REST-API bleibt unverändert.

Das Bootstrap-GET-Formular funktioniert auf Deutsch und Englisch sowie ohne
JavaScript. Die erste Seite rendert serverseitig 20 Fälle, die vorhandene virtuelle
Liste lädt bis zu 60 Zeilen per AJAX. Filter bleiben beim Nachladen, bei der
Detailnavigation, beim Bearbeiten und beim Rückweg erhalten. Mit JavaScript aktualisiert die Suche nach 300 ms Eingabepause per AJAX;
Statuswechsel und explizites Anwenden reagieren sofort. Ohne JS bleibt GET-Navigation.
Der DOM-freie Filter-Presenter verwendet die gemeinsame virtuelle Listensteuerung.

## Geprüfte Fälle

| Fall | Erwartung und Nachweis |
| --- | --- |
| Suchwörter in mehreren Feldern, Teilwort und Gross-/Kleinschreibung | PostgreSQL-Test findet denselben eigenen Fall, einschliesslich Umlauten |
| Suche und Status kombiniert | Nur passende Fälle; Statuswechsel wird bei erneuter Abfrage berücksichtigt |
| Leere Suche, kein Treffer, Zurücksetzen | Normale Liste beziehungsweise eigener übersetzter Leerzustand; Browserprüfung |
| `%`, `_`, Backslash, SQL-/HTML-Zeichen | Literale Suche, keine Erweiterung der Treffer oder HTML-Ausführung |
| Ungültiger Status, zu langer Text, Steuerzeichen | Domain weist ab; HTML und JSON liefern 400 |
| Fremder Benutzer und fremdes Gerät | Keine Treffer oder Zählinformationen; fremdes und unbekanntes Gerät liefern 404; ohne Sitzung JSON 401 |
| Gefilterte Fenster und neue Fälle | 85 Treffer über getrennte Fenster; Snapshot schliesst später angelegte Fälle aus |
| Virtuelle Liste und Fallback | 100 passende Fälle, maximal 60 DOM-Zeilen mit JS; SSR-Pagination ohne JS |
| Detail und Rücknavigation | Suchbegriff und Status bleiben erhalten; auch nach Bearbeitung |
| Sprache und Mobilansicht | Englisch/Deutsch mit und ohne JS; kein horizontaler Überlauf bei 390 px |

## Prüfergebnisse

- Architektur-Skript und 97 Architekturtests bestanden; Teil der insgesamt
  625 erfolgreichen Unit-Tests.
- Alle 290 Integrationstests mit isolierter PostgreSQL-Datenbank bestanden.
- Alle 25 vorhandenen JavaScript-Tests bestanden; keine JS-Implementierung geändert.
- Ruff, Formatierung, Übersetzungskatalog und Diff-Prüfung bestanden.
- Alle elf ausgewählten Browserprüfungen bestanden: vier neue Filterfälle sowie
  sieben bestehende Reparatur-/Scrollabläufe. Mobile deutsche Ansicht visuell geprüft.
- Image gebaut; Start-/Bereitschaftstest mit PostgreSQL und HTTPS bestanden.
- pip-audit, Bandit, Gitleaks und Trivy für App und Infrastruktur bestanden.
  Bestehende PostgreSQL-Ausnahmen unverändert. Zusätzlich alle geänderten und
  neuen Dateien separat mit Gitleaks geprüft, ohne Befund.

Isolierter Ansible-Erstlauf samt HTTPS- und API-Prüfung bestanden (`changed=33`).
Identische Wiederholung bestanden (`changed=0`); Container-IDs und Startzeiten
unverändert. Isolierter Testhost danach entfernt. Aktiver ZAP-Lauf bestanden:
1’300 SQL-Injection-Prüfanfragen, DOM-XSS vollständig abgeschlossen, keine
blockierenden Befunde und keine fehlgeschlagenen Abdeckungsprüfungen. Prüfungen verwenden
den Arbeitsstand auf Basis von Commit `00bf8379c18d65c8e27edf2140da08bdc8602b1f`
einschliesslich der uncommitteten K-T01-Änderungen. App-Image-ID:
`sha256:ba5c42a8b366d920107209bc16009b3a8766cf4361a4883996ddb92778fa5472`.
Archive: `artifacts/kt01/`; Scanberichte: `reports/security/kt01/`;
Screenshots: `reports/kt01/`; geschützte Deployment-Protokolle: `.qa/kt01/`.
ZAP verwendet den bestehenden Scanplan der isolierten CI-Instanz. Die
authentifizierte Filtersuche und ihre Eigentumsgrenzen werden durch die oben
genannten Integrations- und Browserfälle belegt; der Scan ersetzt diese nicht.
Keine Produktionsauslieferung durchgeführt.


## Ergänzung: Suche mit Eingabepause

Auf weiteren Benutzerwunsch aktualisiert das Suchfeld ohne zusätzlichen Klick und
Dokumentneuladen. Die Browserfälle prüfen eine einzige Suchanfrage nach mehreren
schnellen Eingaben, erhaltenen Fokus und dasselbe Dokument. Presenter-Tests prüfen
Timer-Neustart, explizites Anwenden, Abbruch, Entwertung alter Antworten bereits
während der Eingabepause und erneute Suche nach leerem Ergebnis.

Die oben genannten vollständigen Security-/Deployment-Nachweise beziehen sich auf
den Stand vor dieser Frontend-Ergänzung. Ergänzend bestanden: 27 JavaScript-Tests,
sechs PostgreSQL-Filtertests, 97 Architekturtests und der Übersetzungskatalogtest.
Das aktualisierte Image liegt unter `artifacts/kt01-debounce/`, App-Image-ID:
`sha256:27aa6c33350116b99ec4b9d24a4316d09da3aa174f72dc901e1c6fdb23bc0cc7`.
Alle 18 ausgewählten Browserprüfungen gegen dieses Image bestanden, einschliesslich
Geräte- und Reparaturregressionen sowie Englisch/Deutsch mit und ohne JavaScript.
Ruff und Diff-Prüfung bestanden. Keine neue Produktionsauslieferung.
Ein vorläufiger Browserlauf wurde nach einem Fehler im Übersetzungsplatzhalter
abgebrochen; nur die Ergebnisse gegen das korrigierte Image gelten.


### Korrektur der lokalen Entwicklungskonfiguration

Im laufenden lokalen Development-Container war Jinja-Auto-Reload deaktiviert,
während neue JS-Dateien bereits direkt vom Quellcode-Mount ausgeliefert wurden.
Development lädt Templates nun automatisch nach und revalidiert statische Dateien.
Die lokale Nginx-Konfiguration wurde geprüft und neu geladen, Gunicorn sanft neu
geladen. Zwei Regressionstests prüfen tatsächliche Templateänderungen mit derselben
App-Instanz: Development übernimmt die Änderung, Produktion behält den Cache.
Factory- und Architekturtests: 106 bestanden. Debug bleibt deaktiviert.


### Statusauswahl ohne Anwenden-Button

Bei aktiviertem JavaScript ist der Anwenden-Button entfernt; die vorhandene
Change-Anbindung wendet die Statusauswahl sofort an. Ohne JavaScript bleibt der
Button innerhalb von `noscript` für das GET-Formular erhalten. Alle vier Filter-
Browserfälle gegen `artifacts/kt01-auto-filter/` bestanden (Englisch/Deutsch,
mit/ohne JavaScript), einschliesslich Statuswechsel ohne nachfolgenden Klick.
Der Test wartet nach der Detailnavigation auf die erneute JS-Anbindung, bevor
er die Auswahl betätigt. Katalogtest, Ruff und Diff-Prüfung bestanden.

### Ausrichtung der Filterleiste

Suchfeld und Statusauswahl sind ab 768 px oben bündig im Verhältnis 8:4 angeordnet
und gleich hoch (46 px). Der mehrzeilige Suchhinweis verschiebt den Status nicht
mehr. Zurücksetzen und der No-JS-Fallback liegen darunter; die frühere leere
Button-Spalte entfällt. Unter 768 px stehen die Felder untereinander.

Gerenderte deutsche Vorlage mit lokalem Bootstrap-/App-CSS im Browser bei
1440, 768, 390 und 320 px geprüft: bündige Oberkanten am Desktop, gleiche Feldhöhen,
mobile Stapelung und kein horizontaler Überlauf. Desktop- und Mobil-Screenshot
visuell geprüft (`reports/kt01-layout/`). Dies war eine Layoutprüfung ohne
Ausführung der JS-Module, kein neuer fachlicher E2E-Lauf. Katalogtest und
Diff-Prüfung bestanden; keine Fachlogik geändert.
