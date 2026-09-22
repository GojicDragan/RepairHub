# K-T03 – Statusübersicht

## Ergebnis

Die Reparaturliste zeigt offene, laufende und abgeschlossene eigene Fälle in drei
responsiven Karten. Der Überblick gilt ausdrücklich über alle eigenen Geräte
hinweg und ist von Suchtext, Status-/Gerätefilter, Snapshot und Listenfenster
unabhängig. Fehlende Statusgruppen erscheinen als null; ein neuer HTML-Aufruf
liest aktuelle Zahlen einschliesslich Abschluss und Wiederaufnahme.

Der vertikale Slice `get_status_overview` besitzt Command, Ergebnis-DTO,
Repository-Port und Handler. Die Identität wird geprüft, der Adapter explizit in
`app.bootstrap` injiziert. Der Adapter verwendet die gemeinsame Eigentumsabfrage
für eine gruppierte PostgreSQL-Aggregation. Keine Flask-/ORM-Abhängigkeit im
Fachkern, keine direkten Datenbankzugriffe aus Routen und keine Slice-Imports
untereinander. Die globale API-Berechtigung ist in diesem Browseranwendungsfall
ausdrücklich ungültig.

Englische und deutsche Texte über gettext, semantische Definitionslisten,
Statusbeschriftungen zusätzlich zur Farbe und responsive Bootstrap-Spalten.
Die Anzeige benötigt kein JavaScript. Keine neue Migration, Bibliothek,
Environment-Variable oder Secrets.

## Abnahmefälle

| Fall | Nachweis |
| --- | --- |
| Ungültige Benutzeridentität | Domain weist fehlende, ungültige und globale API-Identität vor dem Repository-Aufruf ab |
| Leerer Bestand / fehlende Gruppe | Domain und PostgreSQL liefern explizite Nullwerte |
| Mehr als ein Listenfenster | 65 offene Fälle auf einem Gerät plus abgeschlossener Fall auf anderem Gerät werden vollständig gezählt |
| Filter und Snapshot | Nicht passende Suche, Geräte-/Statusfilter, Offset und Snapshot verändern den Überblick nicht |
| Eigentumsgrenzen | Zweites bestätigtes Konto sieht nur eigene Zähler; ohne Anmeldung Weiterleitung |
| Aktualisierung | Wechsel zu laufend, Wiederaufnahme und Abschluss erscheinen beim nächsten Aufruf |
| Browserdarstellung | Englisch mit JS und Deutsch ohne JS; 1280 und 390 Pixel, kein horizontaler Überlauf |

## Prüfstand

639 Unit-Tests bestanden; nach Ergänzung der Ablehnung globaler API-Identitäten
alle 9 Slice- und 97 Architekturtests nochmals bestanden (insgesamt 640 Unit-Fälle).
Architekturskript ohne unerlaubte Imports; 27 JavaScript-Tests und alle 300
PostgreSQL-Integrationstests bestanden. Ruff, Formatierung, Katalog- und Diff-Prüfung
bestanden. Desktop-/Mobilansicht visuell geprüft.

Produktionsimage gebaut und isoliert mit PostgreSQL/HTTPS auf Bereitschaft geprüft.
pip-audit, Bandit, Gitleaks und Trivy bestanden; bestehende Scan-Ausnahmen bleiben
unverändert. Neue und geänderte Dateien zusätzlich separat mit Gitleaks geprüft.
Alle 13 ausgewählten Browserfälle bestanden: zwei neue Überblicksprüfungen sowie
bestehende Reparatur- und Filterabläufe. Isolierter Ansible-Erstlauf inklusive
HTTPS-/API-Prüfung bestanden (`changed=33`); identische Wiederholung bestanden
(`changed=0`). Container-IDs und Startzeiten unverändert. Testhost anschliessend
entfernt. Aktiver ZAP-Scan bestanden: 1300 SQL-Injection-Prüfanfragen,
DOM-XSS vollständig abgeschlossen, keine blockierenden Befunde und keine
fehlgeschlagenen Abdeckungsprüfungen.

Der lokale ZAP-Steuerprozess wurde vorzeitig beendet, der isolierte Scan-Container
lief weiter bis zum erfolgreichen Abschluss. Der Bericht wurde danach mit dem
unveränderten Bewertungsverfahren aus `scripts/ci/dast.py` ausgewertet: identischer
Automationsplan, Scanner-Exitcode, Befunde, Statistiktests und vollständige
SQL-/DOM-XSS-Abdeckung geprüft. Diese Übernahme ist im bereinigten Bericht vermerkt;
sie ist kein erfolgreicher Durchlauf des unterbrochenen Steuerprozesses. Die
isolierte Scan-Umgebung wurde anschliessend entfernt.

Geprüft wird der Arbeitsstand auf Basis von
`d8e404c983b9e8cbd2e408997a8f6347c689292c` einschliesslich uncommitteter K-T03-Änderungen.
App-Image-ID: `sha256:a5133e16f74bae1037fb44b528ef1821196fe24c031d264b5a7fd355743f5390`.
Archive: `artifacts/kt03/`; Scanberichte: `reports/security/kt03/`;
Screenshots: `reports/kt03/`; geschützte Deployment-Protokolle: `.qa/kt03/`.
Keine Produktionsauslieferung durchgeführt. Der bestehende ZAP-Plan ersetzt
keine fachlichen Eigentumsprüfungen des authentifizierten Überblicks.
