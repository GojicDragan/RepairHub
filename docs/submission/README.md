# Abgabe und Prüfzugang

Stand: 22. September 2026. Dieses Blatt bündelt die technischen Lieferobjekte.
Persönliche Angaben, Prüfzugang und der tatsächliche Betriebszeitraum sind vor der
Abgabe zu vervollständigen; T13 wird deshalb noch nicht insgesamt als erledigt markiert.

## Zugang zur Anwendung

| Angabe | Wert / Zustand |
| --- | --- |
| Browser | <https://lab19.ifalabs.org> |
| Port | HTTPS 443; HTTP 80 nur für Weiterleitung und Zertifikatsvalidierung |
| API-Liste | `GET https://lab19.ifalabs.org/api/repairs?limit=20&offset=0` |
| API-Detail | `GET https://lab19.ifalabs.org/api/repairs/{id}` |
| API-Authentifizierung | `Authorization: Bearer <api-key>` |
| Repository | <https://github.com/GojicDragan/RepairHub> |
| Lesender Repository-Zugang | Am 22.09.2026 öffentlich ohne Anmeldung abrufbar. |
| Fachlicher Prüfstand | Commit `4b59e03022a3c669136ebd4499b096fcad3efcdb`, T12 und Release v0.9. |
| Prüfkonto | **Offen:** eigene Registrierung des Examinators oder separat übergebenes bestätigtes Konto festlegen. |
| Browseranleitung | [Schritt für Schritt mit Screenshots](../user-guide/README.md) |
| API-Beispiele | [API-Vertrag und Curl-Aufrufe](../api.md) |

Ein Prüfkonto benötigt eine bestätigte E-Mail-Adresse und sollte nachvollziehbare
Beispielgeräte und Reparaturen enthalten. Ein persönlicher API-Key wird einmal im
Frontend generiert; der anschliessende API-Aufruf benötigt keinen Browser.
Der Systemschlüssel ist für eine normale Benutzerabnahme nicht erforderlich.
Zugangsdaten und Schlüssel ausschliesslich über einen getrennten, geschützten
Übergabekanal bereitstellen. Im Repository und ZIP stehen keine echten Zugangsdaten.

## Lieferobjekte

- [Bebilderte Benutzeranleitung](../user-guide/README.md), inklusive lokal gespeicherter PNGs.
- [Aktuelle Architekturdiagramme](../diagrams/README.md), PNG und bearbeitbares PlantUML.
- [Testprotokoll](../acceptance-test-protocol.md), [T12-Nachweis](../t12-validation.md)
  und [bereinigte Prüfdaten](../validation/t12.json).
- [Betrieb, Backup und Wiederherstellungsweg](../operations.md).
- [Technisch abgeglichene Word-Arbeitsfassung](RepairHub-Projektdokumentation-Arbeitsfassung.docx).
- [PDF derselben Arbeitsfassung](RepairHub-Projektdokumentation-Arbeitsfassung.pdf).
- Quellcode-ZIP unter `artifacts/submission/RepairHub-source.zip` mit Dateihashes
  in `artifacts/submission/source-manifest.json`. Diese lokalen Ausgaben werden
  nicht in Git versioniert; siehe den reproduzierbaren Aufruf unten.

Die ursprüngliche lokale Word-Datei bleibt als Entwurf erhalten. Die Arbeitsfassung
übernimmt ihre fachlichen Grundlagen und ergänzt den tatsächlichen technischen Stand.
Sie ist ausdrücklich **noch keine fertige schriftliche Abgabe**: Management Summary,
persönliche Reflexion, Titelblattangaben, Eigenständigkeitserklärung und Unterschrift
sind vom Verfasser zu ergänzen. Der lokale «LeitfadenSchriftlicheArbeiten_V2.1_abS2604 (1).pdf», Abschnitt 1.4.6,
verlangt diese Eigenleistung; er gehört nicht zum öffentlichen Quellcode-ZIP.
Die KI-Unterstützung ist in der Arbeitsfassung ausgewiesen. Die bestehenden
Literaturangaben stammen aus dem Entwurf; vor Einreichung persönlich nachprüfen.

Nach Änderungen in Word Inhalts-, Abbildungs- und Tabellenverzeichnis aktualisieren,
PDF neu exportieren und Seitenumfang prüfen: 8–30 Seiten ohne Management Summary
und Anhang. Die persönliche Ergänzung kann die aktuelle Paginierung verändern.

## Quellcode-ZIP reproduzieren

Nach Prüfung aller gewünschten Änderungen im Repository ausführen:

```bash
uv run --locked python scripts/documentation/package_source.py
```

Das Skript verwendet versionierte Dateien sowie die ausdrücklich vorgesehenen
neuen T13-Dokumentationspfade. Es nimmt keine ignorierten Laufzeitdateien, Schlüssel,
Backups, `.git`, `.venv`, privaten QA-Daten oder Image-Archive auf. Der Manifest nennt
Basis-Commit, Zustand und SHA-256 jeder enthaltenen Datei. Ein Archiv vor dem Commit
wird als Arbeitsstand gekennzeichnet; für die definitive Abgabe nach dem Commit neu
erstellen und die auf GitHub vorhandene Revision kontrollieren.

## Vierwöchiger Betrieb

| Festzulegende Angabe | Zustand |
| --- | --- |
| Tatsächlicher Abgabetermin | Noch nicht mitgeteilt. |
| Fristende | Abgabetermin + mindestens 28 Kalendertage. |
| Verbindliche Betriebsverantwortung | Noch zu bestätigen. |
| Kontakt bei Ausfall | Separat an den Examinator übergeben. |
| Kontrolle und Störungsprotokoll | [Betriebsanleitung](../operations.md#korrekturphase-und-störungsprotokoll) |

Eine einzelne HTTPS-Prüfung belegt diese Frist nicht. Den Zeitraum nach tatsächlicher
Abgabe dokumentieren und den Host einschliesslich Domain, SMTP und Sicherungen bis
zum Fristende betreiben. Die praktische Datenbankwiederherstellung bleibt gemäss
Benutzerentscheidung nicht ausgeführt.

## Vor der tatsächlichen Einreichung

1. Persönliche Teile der schriftlichen Arbeit und Angaben im Übergabeblatt ergänzen.
2. Prüfzugang über einen getrennten Kanal bereitstellen und mit dem Examinator klären.
3. Finalen Commit veröffentlichen; danach Quellcode-ZIP neu erstellen.
4. DOCX-Verzeichnisse aktualisieren, PDF prüfen und PDF sowie ZIP auf Complesis abgeben.
5. Abgabetermin und Betriebsfrist eintragen; tatsächliche Erreichbarkeit protokollieren.

Diese Vorbereitung veröffentlicht nichts und übermittelt keine Nachricht an Dritte.
