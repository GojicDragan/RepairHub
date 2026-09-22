# Geräteverwaltung (T06)

Bezug: M02, F03, N02–N04, N06. Benutzerentscheidung: Geräte per AJAX erfassen und
bearbeiten; erste Liste serverseitig rendern, danach virtuell und über AJAX laden.

## Fachliche Anwendungsfälle

`app.domains.devices` enthält die Slices `register_device`, `list_devices`,
`get_device` und `update_device`. Jeder Slice definiert Command, Handler und seinen
benötigten Repository-Port. Gemeinsame Gerätewerte und Validierungsregeln bleiben
frameworkfrei. Der Handler verlangt eine bereits vertrauenswürdig ermittelte
positive Benutzer-ID. Die Webschicht erhält hierfür den injizierten Identitätsport;
Benutzer-/Eigentümer-IDs aus Requestdaten werden nicht übernommen.

Name, Hersteller und Modell sind Pflichtfelder mit höchstens 120 Zeichen, passend
zum fachlichen Entwurf. Führende und nachfolgende Leerzeichen werden entfernt;
reine Leerzeichen, andere Datentypen und Steuerzeichen sind ungültig. Fehlercodes
werden erst in der Webschicht übersetzt. Für fremde und unbekannte Geräte gilt
identisch 404, auch beim Bearbeiten und bei gleichzeitig ungültigen Eingaben.

Die Factory verbindet Slice-Handler und Datenadapter. Adapter unter
`app.data.devices` entsprechen den Anwendungsfällen und verwenden den gemeinsamen
Eigentumsfilter `app.data.queries.ownership.owned_devices`. Einzelne Speicheroperationen
sind atomar und rollen bei Fehlern zurück; dafür ist kein zusätzlicher, vom
Anwendungsfall zu koordinierender Mehrfachschreibvorgang erforderlich. Beim Update
wird der Eigentumsfilter erneut beim gesperrten Lesen angewendet. Rückgaben sind
unveränderliche DTOs ohne ORM-Objekte oder implizite Datenbankabfragen.

Migration `0002_devices` ergänzt ausschliesslich die benötigte Gerätetabelle:
Fremdschlüssel zum Benutzer, Pflichtfelder, Nichtleer-Constraints, Feldlängen und
Index `(owner_id, id)`. Keine Reparaturtabellen auf Vorrat, keine Löschfunktion.
Die additive Migration ist zum bisherigen Image kompatibel; ein automatisches
Datenlöschungs-Downgrade wird weiterhin abgewiesen.

## Web und AJAX

| Pfad | Verhalten |
| --- | --- |
| `GET /devices` | HTML mit 20 eigenen Geräten; mit `Accept: application/json` ein begrenztes Datenfenster |
| `GET /devices/new` | Erfassungsformular |
| `POST /devices/new` | Anlegen; JSON-Antwort 201 oder HTML-Weiterleitung 303 |
| `GET /devices/{id}` | Eigene Gerätedetails |
| `GET /devices/{id}/edit` | Bearbeitungsformular |
| `POST /devices/{id}/edit` | Speichern; JSON-Antwort 200 oder HTML-Weiterleitung 303 |

AJAX gehört zur sitzungsgebundenen Weboberfläche, nicht zur späteren
browserunabhängigen REST-API. Deren vereinbarte Komponenten und lesender Umfang
bleiben unverändert. JSON-Schreibanfragen senden denselben CSRF-Nachweis über
`X-CSRFToken`; unbekannte, fehlende oder fremde Tokens werden abgewiesen.

`DeviceFormPresenter` koordiniert Speichern, Doppelabsende-Schutz und Fehlerzustände
ohne DOM. Der Humble-Object-Adapter bindet Fetch, Felder, Fokus und übersetzte
Meldungen an. Feldfehler kommen mit 422; Eingaben bleiben erhalten. Nach erfolgreicher
Erfassung bearbeitet weiteres Speichern dasselbe Gerät. Ein Detail-Link zeigt das
Ergebnis; die erfolgreiche AJAX-Aktion lädt das Dokument nicht neu. Netzfehler
entsperren das Formular für einen erneuten Versuch. Anfragen haben 20 Sekunden
Zeitlimit. Ohne JavaScript funktionieren die gleichen Formulare über normale POSTs.

Private Antworten verwenden `Cache-Control: no-store`, `Referrer-Policy: no-referrer`
und keine Suchmaschinenindexierung. HTML escaped Gerätewerte; dynamische Zeilen
verwenden `textContent`, niemals HTML aus Geräteangaben. Alle Oberflächentexte
verwenden gettext, Deutsch nach Accept-Language und Englisch als Fallback.

## Virtuelle Liste

- Erster HTML-Aufruf: 20 Zeilen; die Datenmenge wächst nicht mit dem Gesamtbestand.
- Nach JS-Anbindung: ein Fenster mit höchstens 60 Zeilen und konstanter Höhe von
  112 px pro Zeile. Leere Abstandselemente bilden die übrige Scrollhöhe ab.
- Scrollen lädt benötigte Fenster nach, auch rückwärts. Es wird weder eine
  unbeschränkte DOM-Liste noch ein wachsender Datencache angelegt.
- Serverseitig sind `limit` auf 1–60 und nichtnegative numerische Positionen
  begrenzt. Das Gesamtergebnis wird nicht als vollständige Objektliste geladen.
- Aufsteigende IDs und eine obere ID-Grenze (`snapshot`) schliessen später
  zugewiesene IDs beim Weiterblättern aus. Die Grenze ist kein offener
  PostgreSQL-Transaktionssnapshot über mehrere HTTP-Anfragen. Neuladen zeigt
  neu erfasste Geräte; Änderungen bestehender Gerätetexte bleiben sichtbar.
- Alte Fetch-Anfragen werden abgebrochen; eine Generationsprüfung verhindert,
  dass verspätete Antworten ein neueres oder wieder erreichtes Fenster ersetzen.
- Ladefehler haben einen Wiederholen-Button. Der fokussierbare Scrollbereich ist
  mit Tastatur bedienbar; Listenpositionen tragen `aria-posinset`/`aria-setsize`.
  Beim Ersetzen wird Fokus soweit möglich erhalten, sonst zum Scrollbereich gesetzt.
- Ohne JS bleiben reguläre Seitenlinks verfügbar. Mit JS erfolgt die Navigation
  ausschliesslich über den auch per Tastatur bedienbaren virtuellen Scrollbereich;
  zusätzliche Vor-/Zurück-Buttons entfallen. Lange Texte werden in der Liste gekürzt;
  die Detailseite enthält die vollständigen Angaben.

Nginx erlaubt Fetch gezielt über `connect-src 'self'`. Für Produktion muss diese
Konfiguration vor dem App-Release über den bestehenden Infrastruktur-Wartungsweg
ausgerollt werden; siehe [T06-Abnahme](t06-validation.md).

Die bestehende CI findet die zusätzlichen Python-/Node-/Browserprüfungen über ihre
Verzeichnis-/Globauswahl automatisch. Migrations- und Modelldriftprüfung bleiben
verbindlich. Keine neue Bibliothek, kein zusätzlicher Dienst, keine neuen Secrets
oder Environment-Variablen nötig. Ergebnisse: [T06-Abnahme](t06-validation.md).

### Vereinfachte Scroll-Navigation (22. September 2026)

Auf Benutzerwunsch entfallen die zusätzlichen Vor-/Zurück-Buttons bei aktivem
JavaScript. Geprüft: fünf Geräte-Browsertests im neu gebauten Produktionsimage
(Englisch/Deutsch, Tastatur-Scrollen, AJAX, DOM-Begrenzung und Seitenlinks ohne JS),
13 Frontend-Unit-Tests sowie Architekturprüfung und 97 Architekturtests bestanden.
Kein erneuter Security-Scan oder Produktionsdeployment für diese UI-Anpassung.

### Scrollposition bei Rückkehr aus den Details

Die Liste merkt sich ihre Scrollposition in `sessionStorage`, getrennt nach
Benutzer, Browser-Tab und Listen-URL. Browser-Zurück und der Listenlink in der
Detailansicht stellen diese Position wieder her und laden das passende begrenzte
Datenfenster nach. Gespeichert wird nur die Pixelposition, keine Gerätedaten.
Der DOM-freie Presenter validiert und begrenzt die Position auf die aktuelle
Listengrösse; der DOM-Adapter kapselt Speicher und Scrollzugriff. Falls der Browser
den Speicher sperrt, bleibt die Liste nutzbar, ohne persistierte Wiederherstellung.

Prüfung am 22. September 2026: fünf Geräte-Browsertests im frisch gebauten
Produktionsimage bestanden, einschliesslich beider Rückwege mit genauer
Scrollposition in Englisch/Deutsch. 14 Frontend-Unit-Tests, 97 Architekturtests,
Architekturprüfung und Ruff bestanden. Kein erneuter Security-Scan oder
Produktionsdeployment für diese Anpassung.

## Eigene Gerätewerte als Autocomplete

Benutzerentscheidung vom 22. September 2026: kein externer Produktkatalog. Beim
Erfassen und Bearbeiten werden Gerätename, Hersteller und Modell aus den bereits
erfolgreich gespeicherten **eigenen** Geräten vorgeschlagen. Freie Eingaben bleiben
immer möglich. Persönliche Gerätenamen und Modelle anderer Konten werden nicht
weitergegeben. Neue Werte erscheinen nach erfolgreichem Speichern automatisch;
es gibt keine zusätzliche globale oder historische Stammdatenliste. Wird ein Wert
in allen eigenen Geräten ersetzt, entfällt entsprechend sein Vorschlag.

Der vertikale Slice `suggest_device_values` prüft die vertrauenswürdige Identität,
das Feld und die Eingabelängen. Sein Repository-Port wird in `app.bootstrap` mit
dem PostgreSQL-Adapter verdrahtet. `GET /devices/suggestions` ist ein authentifizierter
Browser-AJAX-Endpunkt mit `field`, `term` und optional `manufacturer`; die separate
Reparatur-REST-API wird nicht erweitert. Die Antwort enthält nur `items` als Liste
von Textwerten und wird nicht gecacht. SQL-Wildcards werden als Text behandelt.

Ab zwei Zeichen werden höchstens zehn alphabetisch sortierte Teilworttreffer
geliefert, ohne Beachtung der Gross-/Kleinschreibung. Mehrere durch Leerzeichen
getrennte Suchteile müssen alle im jeweiligen Feld vorkommen; Position und
Reihenfolge sind beliebig. So findet `radio küche` auch `Küche – grosses Radio`. Gleich geschriebene Werte mit
abweichender Gross-/Kleinschreibung werden zusammengefasst. Bei ausgefülltem
Herstellerfeld sind Modellvorschläge auf diesen Hersteller beschränkt. Es gibt
keine automatische Korrektur, Umlautumschreibung oder unscharfe Produkterkennung.

DOM-freier `DeviceSuggestionsPresenter` steuert Verzögerung, veraltete Antworten,
Auswahl und Tastaturbedienung. Der Humble-Object-Adapter kapselt Fetch und die
markeneigene Combobox. Pfeiltasten wählen einen Vorschlag, Enter übernimmt ihn,
Escape schliesst die Liste. Mausklick ist ebenfalls möglich. Der Input behält den
Fokus; `aria-expanded`, `aria-controls`, `aria-activedescendant` und Live-Meldungen
stellen den Zustand bereit. Herstellerwechsel verwirft geladene Modellvorschläge.

Anfragen starten nach 250 ms Eingabepause; alte Anfragen werden abgebrochen. Fehler
oder fehlende Treffer verhindern weder Freitext noch Speichern. Ohne JavaScript
bleiben die bisherigen Formulare bedienbar. Hinweise sind über gettext auf Deutsch
und Englisch verfügbar. Keine zusätzlichen Abhängigkeiten, Migrationen,
Environment-Variablen, Secrets oder externen Netzwerkanfragen erforderlich.

### Prüfung der Autocomplete-Erweiterung

Am 22. September 2026 bestanden: 431 Python-Unit-Tests, darin 97 Architekturtests,
201 PostgreSQL-Integrationstests sowie 18 Frontend-Unit-Tests. Die explizite
Architekturprüfung meldet keine unerlaubten Imports. Sieben Geräte-Browsertests
gegen das neu gebaute Produktionsimage prüfen Deutsch/Englisch, Tastatur-/Mausauswahl,
Freitext, Wiederverwendung neuer Werte, Netzfehler, Scrollposition und Formulare
mit/ohne JavaScript. Deutsche Dropdown-Darstellung anhand des Screenshots geprüft.

Leere PostgreSQL-Datenbank erfolgreich migriert; Alembic meldet keine fehlende
Migration. Dependency-, Bandit-, Gitleaks- und alle drei Trivy-Image-Scans bestanden
(`reports/security/device-suggestions/`). Build: `artifacts/device-suggestions`;
Screenshots: `reports/device-suggestions`. Der erste Browserlauf deckte eine falsche
Bindung der Browser-Timer auf; der korrigierte Lauf ist vollständig grün.
Kein neuer ZAP-Lauf und kein Produktionsdeployment. Die bestehende ZAP-Abdeckung
umfasst weiterhin keine authentifizierten Geräteendpunkte; deren Berechtigungs-,
SQL-Eingabe- und Fehlerprüfungen sind hier durch Integration/E2E nachgewiesen.

Nachtrag zur Suchsemantik (22. September 2026): Gross-/Kleinschreibung,
Wortreihenfolge und Position sind für jeden Suchteil beliebig. Alle Teile müssen
innerhalb des gesuchten Feldwerts vorkommen (UND-Verknüpfung), auch innerhalb eines
Wortes. Der Domain-Handler normalisiert und zerlegt die Eingabe; der Adapter setzt
die eigentumsgebundene, parametrisierte Suche um. Für alle drei Felder einschliesslich
Umlauten und fehlenden Suchteilen geprüft: 162 Domain-/Architekturtests und 204
PostgreSQL-Integrationstests bestanden. Kein erneuter Build, Browser- oder
Security-Lauf für diese ausschliesslich serverseitige Suchanpassung.

### Speichern erst bei vollständiger Eingabe

Der Geräte-Speichern-Button bleibt mit JavaScript deaktiviert, solange Gerätename,
Hersteller oder Modell leer sind oder nur Leerzeichen enthalten. Das gilt auch
beim Bearbeiten und erneuten Leeren eines Felds. Die DOM-freie Vollständigkeitsprüfung
liegt im Formular-Presenter; der Adapter aktualisiert den Zustand bei Eingabe,
Autocomplete-Auswahl, Fokus, Formular-Reset und Seitenwiederherstellung. Während
laufender Speicherung bleibt der Button unabhängig von Eingabeereignissen gesperrt.
Ohne JavaScript bleiben native Pflichtfelder und serverseitige Validierung aktiv.

Prüfung am 22. September 2026: 19 Frontend-Unit-Tests, Architekturprüfung mit
97 Architekturtests sowie sieben Geräte-Browsertests im neu gebauten Image
bestanden. Leere Felder, Leerzeichen, erneutes Leeren, vollständige Eingabe und
Autocomplete in Deutsch/Englisch geprüft. Kein neuer Security- oder Deployment-Lauf.

Beim Bearbeiten bleibt der Button zusätzlich gesperrt, solange die drei Werte dem
zuletzt gespeicherten Stand entsprechen. Führende und nachfolgende Leerzeichen
werden wie beim serverseitigen Speichern ignoriert. Zurückändern auf den Ausgangswert
sperrt den Button erneut. Erst ein erfolgreicher AJAX-Speichervorgang übernimmt die
vom Server normalisierten Werte als neue Vergleichsbasis; Fehler lassen Änderungen
weiterhin speicherbar. Der Presenter hält diesen Zustand unabhängig vom DOM.

Änderungsvergleich geprüft am 22. September 2026: 21 Frontend-Unit-Tests,
97 Architekturtests und Architekturprüfung sowie sieben Geräte-Browsertests
bestanden. Der Browserlauf prüft unveränderte Bearbeitung, echte Änderungen,
Zurückändern, Leerzeichen und die neue Vergleichsbasis nach AJAX-Erfolg auf
Deutsch/Englisch. Keine erneuten Security-Scans oder Produktionsbereitstellung.

## K-T02: Suche in der Geräteliste

`GET /devices?q=radio+maker` durchsucht ausschliesslich eigene Geräte nach
Bezeichnung, Hersteller und Modell. Die Suchsemantik entspricht der Reparatursuche:
Teilwörter an beliebiger Position, ohne Beachtung der Gross-/Kleinschreibung;
alle durch Leerraum getrennten Begriffe müssen in mindestens einem der drei
Felder vorkommen. Die Felder dürfen sich pro Begriff unterscheiden. Umlaute bleiben
erhalten (`ü` wird nicht zu `ue`, `ß` nicht zu `ss`). Keine Stammbildung oder
Relevanzsortierung; Reihenfolge weiterhin nach aufsteigender Geräte-ID.

Eine leere Suche zeigt die normale Liste. Maximal 200 Zeichen, keine Steuerzeichen;
ungültige Eingaben liefern HTTP 400. SQL-Wildcards wie `%` und `_` sowie Backslash
werden als Literalzeichen behandelt. Parameter werden gebunden, nicht als SQL
zusammengesetzt. Eigentumsfilter und Suche gelten für Maximum, Trefferzahl und
jedes Fenster. Die obere ID schliesst später angelegte Geräte aus; Änderungen an
Gerätetexten können Treffer verändern. Dies ist kein Datenbank-Transaktionssnapshot.

Die Erweiterung gehört zum vorhandenen Slice `list_devices`. Command und Port
bleiben frameworkfrei, die Suchabfrage liegt im SQLAlchemy-Adapter. Keine neue
Domain-Abhängigkeit, Bibliothek oder Migration. Für den Praxisarbeitsumfang wird
keine zusätzliche Suchmaschine oder Indexmigration eingeführt.

Die erste Seite rendert 20 Treffer serverseitig. Mit JavaScript aktualisiert die
Suche nach 300 ms Eingabepause per AJAX, erhält den Eingabefokus und setzt
Scrollposition und Snapshot zurück. Die gemeinsame virtuelle Liste hält maximal
60 Zeilen im DOM. Antworten älterer Suchen werden bereits bei neuer Eingabe entwertet;
der bestehende Wiederholen-Button behandelt Ladefehler. Ohne JavaScript funktioniert
das GET-Formular mit Suchbutton und Seitenlinks. Deutsch und Englisch über gettext.

Gerätedetails, Bearbeitung und Rückweg erhalten `q`, ebenso die URLs nach dem
Speichern. Die URL-gebundene Scrollspeicherung trennt verschiedene Suchlisten.
Beim Wechsel in Reparaturfunktionen wird die Gerätesuche nicht als Reparatursuche
übernommen. Autocomplete bleibt der separate Anwendungsfall für Geräteeingaben.

Nachweis: [K-T02-Abnahme](kt02-validation.md).
