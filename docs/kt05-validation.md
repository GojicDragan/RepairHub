# K-T05 – lokaler Prüfnachweis

PDF-Download eigener Reparaturfälle mit vollständigen Schritten und Positionen,
Gerätedaten, Status und der gemeinsamen Kostenschätzung implementiert.
Technischer Ablauf und Grenzen: [PDF-Berichte](pdf-reports.md).

## Nachweise

- 710 Unit-Tests bestanden; neue Renderer-Tests prüfen mehrseitige Dokumente,
  lange Fehlertexte, vollständige Positionen, eingebettete deutsche Umlaute,
  wörtliche Markup-Ausgabe und unveränderte übergebene Domain-Kosten.
- 33 Reparatur-Integrationstests mit PostgreSQL bestanden. Anschliessend beide
  PDF-Integrationstests erfolgreich geprüft, einschliesslich des zusätzlich
  ergänzten Falls mit 25 Schritten und 25 Teilen. PDF enthält letzte Positionen
  trotz Browser-Pagination; Gesamtbetrag CHF 349.75 stimmt mit der Oberfläche überein.
- Fremder und unbekannter Fall: 404. Ohne Browsersitzung: Anmeldung. Downloadheader,
  `no-store`, `nosniff`, Deutsch und englischer Fallback geprüft.
- Zwei Chromium-Browserabläufe gegen die endgültige archivierte Produktionsimage-
  Kombination bestanden: tatsächlicher Download mit JavaScript/Deutsch und ohne
  JavaScript/Englisch. PDF-Datei und enthaltene Fehlerbeschreibung geprüft.
- Englische und deutsche Beispielberichte sowie gerenderte Seiten unter
  `reports/kt05/`; erste und letzte englische Seite sowie deutsche erste Seite
  visuell geprüft. Ein dabei gefundener verwaister Schrittlabel-Umbruch ist behoben.
- Der erste Image-Test zeigte, dass der ursprünglich gewählte Modulordner `reports`
  durch die bestehenden Ausschlussregeln nicht ins Image gelangte. Der Renderer
  liegt nun unter `app.web.documents`; abschliessender Image-Downloadtest erfolgreich.
- Architekturprüfskript, 99 Architekturtests, Übersetzungsprüfung, Ruff und
  Formatprüfung bestanden. Keine Domain-Abhängigkeit auf ReportLab, Flask oder ORM.
- Endgültiges App-Image gebaut; Dependency-, Bandit-, Gitleaks- und Trivy-Scans
  einschliesslich Garage-Quellinventar bestanden. Zusätzlich vollständigen
  Arbeitsstand einschliesslich neuer Dateien mit Gitleaks geprüft.
- Lokale Anwendung mit neuem Image aktualisiert; Bereitschaftsprüfung erfolgreich.

## Offene Release-Abnahme

Kein Produktionsdeployment durchgeführt. Vollständiger CI-Lauf einschliesslich
aktiver ZAP-DAST-Wiederholung und tatsächliche Release-Abnahme stehen aus. Der letzte
lokale DAST-Nachweis gehört zum vorherigen K-T04-Stand. Keine neuen Secrets oder
Environment-Variablen, keine Migration. Beliebige Emoji-/CJK-Zeichen sind durch die
gewählte eingebettete Schrift nicht abgedeckt; Deutsch/Englisch sind geprüft.
