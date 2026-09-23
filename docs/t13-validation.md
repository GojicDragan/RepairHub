# T13 – Benutzeranleitung und Abgabevorbereitung

Stand: 22. September 2026. Die technische Vorbereitung ist vorhanden; persönliche
Ergänzungen, Prüfzugang und der tatsächliche vierwöchige Betrieb bleiben offen.
T13 ist deshalb insgesamt **noch nicht abgeschlossen**.

## Erstellte Unterlagen

- [Benutzeranleitung](user-guide/README.md): zwölf Themenbereiche, 34 echte
  Playwright-Aufnahmen und eine gerenderte Vorschau des heruntergeladenen PDFs.
- [Architekturdiagramme](diagrams/README.md): sieben aktuelle PlantUML-Quellen und
  PNGs für Verantwortlichkeiten, Komponenten, Datenmodell, Ablauf, Deployment und API.
- [Abgabe-/Übergabeblatt](submission/README.md) mit realer URL, Port, Repository,
  Lieferobjekten und ausdrücklich offenen Angaben.
- Technisch überarbeitete Word-/PDF-Arbeitsfassung auf Basis des lokalen Entwurfs.
  Inhalts-, Abbildungs- und Tabellenverzeichnis wurden mit LibreOffice aktualisiert.
  Der Export umfasst 31 Seiten insgesamt; Titel, Summary, Verzeichnisse und
  Erklärung sind darin enthalten. Der redaktionelle Teil liegt innerhalb von
  8–30 Seiten. Persönliche Ergänzungen erfordern eine erneute Umfangsprüfung.
- README aktualisiert; Betriebsplan für die Korrekturphase und ein leeres
  Störungsprotokoll ergänzt. Keine Betriebsdauer oder Restore-Ausführung erfunden.
- Reproduzierbares [ZIP-Skript](../scripts/documentation/package_source.py) für
  Quellcode und öffentliche Unterlagen mit SHA-256-Dateimanifest.

## Tatsächlich ausgeführter Browserablauf

Geprüft wurde das archivierte Produktionsimage zu
`4b59e03022a3c669136ebd4499b096fcad3efcdb` aus `artifacts/t12`.
Zwischen diesem Stand und dem zu Beginn sauberen HEAD
`74aad83` liegen ausschliesslich T12-Dokumentationsänderungen; App, Adapter,
Migrationen und Frontend sind gleich. Es wurde kein neues App-Image behauptet.

Der Ablauf verwendet eine wegwerfbare HTTPS-Instanz mit PostgreSQL, Garage und
SMTP-Senke. Das Konto `Anleitung` und alle Beispieldaten entstehen nur darin.
Registrierung, Erfassung und Bearbeitung erfolgen durch sichtbare Browserformulare.
Ausschliesslich die zusätzlichen 100 Geräte und 100 Fälle für die Scrollansichten
werden als gekennzeichnete Fixture direkt in dieser isolierten Datenbank angelegt.
Nach der Durchführung räumt der vorhandene Runtime-Helper die Instanz wieder auf.

| Bereich / Anwendungsfälle | Tatsächliche Kontrolle |
| --- | --- |
| Registrierung, Bestätigung erneut senden, E-Mail bestätigen | Formular abgesendet; echte abgefangene Bestätigungsmail gelesen; Link im Browser geöffnet; Anmeldung erfolgreich. |
| Anmelden, abmelden, Passwort anfordern und zurücksetzen | Anmeldung mit E-Mail, später mit Benutzername und neuem Passwort; geschützte Geräte-URL nach Abmeldung führt zur Anmeldung. |
| Gerät erfassen, lesen und bearbeiten | Name/Hersteller/Modell gespeichert; geändertes Modell nach Öffnen nachgewiesen. |
| Eigene Vorschläge und Gerätesuche | Hersteller-Teilbegriff ausgewählt; gemischte Gross-/Kleinschreibung über mehrere Felder liefert den erwarteten Treffer. |
| Reparatur erstellen, lesen und Beschreibung ändern | Neuer Fall mit CHF 0.00; Beschreibung gespeichert und zurückgelesen. |
| Schritte hinzufügen und bearbeiten | Zwei Schritte angelegt; Beschreibung geändert und erster Schritt als erledigt gespeichert. |
| Status ändern / Wiederaufnahme | Offen → In Bearbeitung → Abgeschlossen → In Bearbeitung geprüft. |
| Arbeitswerte, Teile hinzufügen und bearbeiten | 2 × 80 = CHF 160.00; plus 3 × 15 = CHF 205.00; Teilebezeichnung geändert. |
| Geräte- und Fallbilder hochladen, auflisten, lesen, löschen | Je drei gültige Bilder; geladene Vorschaubilder; Originalabruf 200; nach Bestätigung zwei Bilder und gelöschter Abruf 404. |
| Reparatursuche, Filter und Statusübersicht | Trefferzahl 1; nicht passender Suchbegriff 0; Zurücksetzen stellt Treffer wieder her. |
| Virtuelle Geräte- und Falllisten | Je 101 Datensätze; Scrollen und Detail-Rückweg; höchstens 60 DOM-Zeilen, Scrollposition wiederhergestellt. |
| PDF-Download | Browserdownload ausgeführt, PDF geparst und CHF 205.00 nachgewiesen; Beispieldokument abgelegt. |
| API-Key generieren, anzeigen, ersetzen, widerrufen | Klartext nur in Erzeugungsantwort; Liste und Detail über Bearer-Key; alter/widerrufener Key 401. |
| Mobilansicht und Fehlerseite | 390-Pixel-Ansicht ohne horizontalen Überlauf; unbekannte Route mit Rückweg aufgenommen. |

Der finale Ablauf bestand vollständig, ohne JavaScript-Seitenfehler.
[Capture-Manifest](user-guide/capture.json) enthält Quellstand und Bildnamen.
Die API-Leseaufrufe erfolgen über Playwrights HTTP-Client. Die Bildinhalte werden
zusätzlich per HTTP geprüft. Diese dokumentierende Tour ersetzt nicht die
umfangreichere negative, mehrsprachige und JavaScript-freie T12-Abnahme.

Passwörter und generierte API-Schlüssel werden nur im Prozess verwendet und in
Screenshots maskiert. Die HTML-Mail ist echt; ihr privater Link wird vor der
Bildaufnahme entfernt. Es wurden weder Produktionsdaten angelegt noch echte
Nachrichten ins Internet versendet. Die lokalen bestehenden Benutzer bleiben unberührt.

## Reproduktion

Voraussetzungen: Docker, die im Lockfile festgelegten Entwicklungs-/E2E-Abhängigkeiten,
Chromium und zuvor gebaute, passende Image-Artefakte.

```bash
uv sync --locked --group e2e
uv run --locked --group e2e playwright install --with-deps --only-shell chromium
uv run --locked --group e2e python -m scripts.documentation.capture_user_guide \
  --artifacts artifacts/t12 \
  --commit 4b59e03022a3c669136ebd4499b096fcad3efcdb
```

Für spätere App-Stände zuerst neue Images bauen und Artefaktpfad/Commit entsprechend
ersetzen. Der Helper prüft das Image-Manifest vor der Ausführung. Er akzeptiert keine
Produktions-URL als Ziel. Die PDF-Vorschau kann mit Poppler separat erzeugt werden:

```bash
pdftoppm -f 1 -l 1 -scale-to 1400 -png -singlefile \
  docs/user-guide/example-repair.pdf docs/user-guide/images/18-pdf-preview
```

Die Word-Arbeitsfassung wurde aus dem vorhandenen DOCX abgeglichen, mit den aktuellen
Diagrammen ergänzt und mit LibreOffice 7.4.7.2 exportiert. Verzeichnisse wurden über
die Office-Schnittstelle aktualisiert. Originalentwurf und Aufgaben-PDFs bleiben
lokal erhalten; sie werden nicht durch das Quellcode-ZIP öffentlich gemacht.

## Technische Prüfungen und Grenzen

Ruff, Formatierung, Architekturprüfung und die 99 Architekturtests bestanden.
Die neue Tour prüft den Dokumentationsablauf tatsächlich; Tests und Architekturregeln
wurden nicht abgeschwächt. Am App-Code, Datenbankschema und Deployment wurde nichts
geändert. Die letzte vollständige Test-/Security-/Deployment-Abnahme bleibt T12.
Markdown-Dateiverweise, alle 34 Capture-Bilder und PDF-Inhalte wurden geprüft.
Compose-Konfiguration, lokaler Bereitschaftscheck und Alembic-Stand
`0006_images (head)` sind geprüft. Das erzeugte ZIP wurde vollständig gelesen und
jeder Eintrag mit dem SHA-256-Dateimanifest verglichen (565 Dateien). Gitleaks
prüfte den entpackten Abgabestand ohne Befund; Bericht lokal unter
`reports/t13/source-secrets.json`. Die erste Manifestdarstellung erzeugte
Fehlalarme durch API-Key-Dateinamen neben Dateihashes; getrennte Felder `path`
und `sha256` beseitigen die Mehrdeutigkeit ohne Scanner-Ausnahmen.

Beim Dokumentieren aufgefallen: Nach der AJAX-Neuanlage eines Reparaturfalls fehlt
zunächst der Bildbereich, da er ausserhalb des ersetzten Arbeitsbereichs liegt.
Nach Öffnen derselben Detail-URL ist er vorhanden. Die Anleitung benennt diesen
Schritt ausdrücklich; die Tour führt ihn vor dem Fallbild-Upload aus.
Das ist eine verbleibende UI-Einschränkung, kein korrigierter App-Fehler.

## Noch vom Verfasser zu ergänzen

- Tatsächlicher Abgabetermin, Betriebsverantwortung und Prüfzugangsverfahren.
- Persönliche Titelblattangaben, Management Summary und kritische/persönliche
  Reflexion gemäss lokalem Leitfaden 1.4.6; keine erfundenen Erfahrungsberichte.
- Abschliessende Quellenprüfung, Prüfung der KI-Deklaration und unterschriebene
  Eigenständigkeitserklärung.
- Finaler Commit/Upload der Unterlagen und anschliessende Neupaketierung des ZIPs.
- Tatsächlicher mindestens vierwöchiger Betrieb ab Abgabe.

Die auf Benutzerentscheid ausgesetzte praktische DB-Wiederherstellung wird weiterhin
als **nicht ausgeführt** dokumentiert. Keine Produktionsauslieferung oder Abgabe an
Dritte wurde durch diese Dokumentationsarbeit vorgenommen.
