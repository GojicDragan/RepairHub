# Reparaturfälle, Schritte und Status (T07)

Ein angemeldeter Benutzer legt über die Detailseite eines eigenen Geräts einen
Reparaturfall an. Die Fehlerbeschreibung ist erforderlich. Neue Fälle starten
mit «Offen». `/repairs` zeigt eigene Fälle, optional mit `?device_id=…` auf ein
eigenes Gerät eingeschränkt. `/repairs/<id>` zeigt den Fall und seine Schritte.

## Fachliche Regeln

- Fehlerbeschreibung: nach Entfernen äusserer Leerzeichen 1–10 000 Zeichen.
- Schrittbeschreibung: 1–2 000 Zeichen; Zeilenumbrüche und Tabs sind erlaubt,
  sonstige Steuerzeichen nicht.
- Status: `open`, `in_progress`, `completed`, übersetzt als «Offen»,
  «In Bearbeitung», «Abgeschlossen». Jeder Wechsel einschliesslich Wiederaufnahme
  ist erlaubt. Unerledigte Schritte verhindern den Abschluss nicht.
- Neue Schritte sind unerledigt. Beschreibung und Erledigungszustand können
  gemeinsam geändert werden. Die Speicherung setzt einen ausdrücklichen booleschen
  Zielzustand; wiederholtes Speichern schaltet ihn nicht zurück.
- Eigentümerschaft wird über Gerät → Fall → Schritt abgeleitet. Vom Browser
  gelieferte Eigentümerangaben werden nicht übernommen. Fremde und unbekannte
  Objekte ergeben dieselbe 404-Antwort, auch bei Änderungen und fremden Zuordnungen.

## Architektur und Persistenz

`app.domains.repairs` enthält unter anderem die vertikalen Slices `create_repair`,
`list_repairs`, `get_repair`, `update_description`, `change_status`, `add_step`,
`update_step` und `get_status_overview`. Jeder besitzt eigene Commands, Ports und Handler. Gemeinsame
DTOs und Regeln importieren keine Slices. Der Erstellungszeitpunkt stammt aus
einer injizierten Uhr. Der Fachkern kennt weder Flask noch SQLAlchemy.

Passende Adapter unter `app.data.repairs` implementieren die Ports und verwenden
die gemeinsamen Eigentumsabfragen. Schreibvorgänge sind atomar und prüfen den
Eigentümer nochmals beim gesperrten Datenbankzugriff. `app.bootstrap` verdrahtet
Handler und Adapter. Die Webkomponente ruft diese Handler auf; sie greift nicht
auf ORM-Modelle oder Datenbank-Sessions zu.

Migration `0003_repairs` ergänzt ausschliesslich `repairs` und `repair_steps` mit
Fremdschlüsseln, Pflichtfeldern, Längen-/Statusprüfungen und Abfrageindizes.
Bestehende Benutzer und Geräte werden nicht verändert. Die normale explizite
Deployment-Migration genügt; neue Environment-Variablen, Secrets und Bibliotheken
sind nicht erforderlich.

## Browserablauf

Erfassung und Änderungen speichern mit JavaScript über AJAX. Leere sowie
unveränderte Formulare bleiben deaktiviert; während des Speicherns sind weitere
Speicheraktionen gesperrt. Validierungs- und Netzwerkfehler erhalten Eingaben.
Die Antwort enthält serverseitig mit Jinja escaptes HTML. Andere Formularentwürfe
bleiben bei einer Aktualisierung erhalten, auch wenn sie vorübergehend leer sind.

`RepairFormPresenter` enthält das DOM-freie Zustandsverhalten;
`repair-form-view.mjs` übernimmt DOM-Ereignisse und Fetch. Ohne JavaScript bleiben
GET-Seiten und CSRF-geschützte POST-Formulare mit Weiterleitung nutzbar. Auch die
JSON-Schreibanfragen benötigen CSRF und eine bestätigte Browsersitzung; sie sind
keine zusätzliche öffentliche REST-API.

Die Reparaturliste startet wie die Geräteliste mit 20 serverseitig gerenderten
Zeilen. Mit JavaScript lädt dieselbe gemeinsame virtuelle Listensteuerung per
AJAX Fenster von höchstens 60 Zeilen und ersetzt das bisherige Fenster. Zeilenhöhe,
Marken-Scrollbar, Tastaturbedienung, Lade-/Fehlerzustand und Wiederholung sind für
beide Listen gleich. Scrollpositionen bleiben im jeweiligen Tab pro Benutzer und
Listen-URL erhalten, auch nach Detailansicht und Zurücknavigation. Ein Gerätefilter
bleibt beim Nachladen und beim Listenlink der Detailansicht erhalten.

`GET /repairs` liefert bei `Accept: application/json` ein eigentumsgeprüftes Fenster
mit `offset`, `limit` (1–60), `snapshot` (obere Fall-ID), `total` und `items`.
Die obere ID verhindert verschobene Fenster durch neue Fälle während einer
Listenansicht; es ist kein Datenbank-Transaktionssnapshot. Status-/Textänderungen
bleiben sichtbar, die Reihenfolge ist absteigend nach Fall-ID. JSON enthält nur
die für die Zeilen benötigten Daten und übersetzten Status-/Fallbezeichnungen.
Filter und Snapshot erlauben keinen Zugriff auf fremde Daten.

Ohne JavaScript bleiben Seitenlinks für jeweils 20 Fälle verfügbar; mit JavaScript
werden sie ausgeblendet. Reparaturschritte bleiben bei 20 Einträgen je Seite.
Englisch ist Fallback, Deutsch wird über Browser-Sprache und
gettext gewählt; URLs bleiben Englisch. Private Antworten werden nicht gecacht.

## Abgrenzung

Gespeichert werden die aktuelle Fehlerbeschreibung, der aktuelle Status und die
Schritte samt Erledigungszustand; ein unveränderliches Änderungsprotokoll ist nicht
Teil dieses Tasks. Ersatzteile, Arbeitswerte und Kosten sind mit [T08](parts-and-costs.md) ergänzt;
der lesende API-Zugang folgt in T09. Such- und Statusfilter bleiben den geplanten Erweiterungen
vorbehalten. Prüfergebnisse: [T07-Abnahme](t07-validation.md).

## K-T01: Suche und Statusfilter

`GET /repairs?q=radio+warm&status=open` kombiniert Suche und Statusfilter.
`device_id` kann die Liste zusätzlich auf ein eigenes Gerät einschränken.
Erlaubte Statuswerte: leer (alle), `open`, `in_progress`, `completed`.
Unbekannte Werte liefern HTTP 400. Der Suchtext ist auf 200 Zeichen begrenzt;
Steuerzeichen sind unzulässig. Leere beziehungsweise reine Leerzeicheneingaben
schränken die Liste nicht ein.

Die Suche berücksichtigt Fehlerbeschreibung, Gerätename, Hersteller und Modell.
Alle durch Leerraum getrennten Begriffe müssen vorkommen, dürfen aber verschiedene
Felder treffen. Teilwörter und beliebige Positionen sind erlaubt, Gross-/Kleinschreibung
wird ignoriert. PostgreSQL übernimmt die Zeichenbehandlung; Umlaute bleiben erhalten,
`ü` wird nicht zu `ue` und `ß` nicht zu `ss` umgeschrieben. Es gibt keine linguistische
Stammbildung oder Relevanzsortierung. `%`, `_`, Backslash und SQL-Syntax gelten als
Suchtext, nicht als Wildcards oder Befehle. Sortierung bleibt neueste Fall-ID zuerst.

Der bestehende Slice `list_repairs` validiert die Eingaben und übergibt sie über
seinen Repository-Port. SQL-Suchtechnik bleibt im Adapter. Eigentumsbindung,
Gerätefilter, Suche und Status gelten gemeinsam für Maximum, Trefferzahl und jedes
Datenfenster. Keine zusätzliche Domain-Abhängigkeit, Bibliothek oder Migration.
Die lesende REST-API erhält durch diese Browserfunktion keine neuen Filterparameter.

Das gebrandete GET-Formular funktioniert mit und ohne JavaScript. Anwenden beginnt
ohne den alten Offset oder Snapshot; Zurücksetzen erhält gegebenenfalls den Gerätefilter.
Die erste Seite rendert höchstens 20 Fälle serverseitig. Die vorhandene virtuelle
Liste lädt danach per AJAX mit denselben Filtern höchstens 60 Zeilen; ohne JavaScript
stehen Seitenlinks bereit. Mit JavaScript aktualisiert die Suche nach 300 ms Eingabepause die Treffer per
AJAX. Statuswechsel und Enter wenden sofort an. Der Anwenden-Button erscheint nur
ohne JavaScript als Fallback. Der DOM-freie
`ListFilterPresenter` koordiniert die Eingabepause; die gemeinsame virtuelle
Listensteuerung lädt das neue Fenster. Bereits beim Tippen werden alte Antworten
entwertet. Snapshot und Scrollposition werden zurückgesetzt, Fokus und Eingabetext
bleiben erhalten. IME-Komposition wird erst nach Abschluss angewendet. Die URL wird
aktualisiert, damit Detailnavigation und Rückweg den Filter weiterverwenden.

Detail-Links, Rückweg, Detailformulare und Schritte-/Teilepagination erhalten `q`
und `status`. Die bestehende URL-gebundene Scrollspeicherung trennt gefilterte Listen.
Die obere ID verhindert das Einschieben neuer Fälle in ein laufendes Fenster,
ist aber kein unveränderlicher Datenbank-Snapshot: Status- oder Textänderungen
können Treffer während des Scrollens verändern. Erneutes Anwenden aktualisiert die Liste.
Englische Texte und deutsche gettext-Übersetzungen umfassen auch den leeren Suchzustand.

## Statusübersicht (K-T03)

Oberhalb der Liste stehen die Zahlen eigener offener, laufender und abgeschlossener
Fälle. Der ausdrücklich beschriftete Überblick gilt für alle eigenen Geräte;
Suchtext, Status-/Gerätefilter und virtuelle Listenfenster schränken ihn nicht ein.
Ohne Fälle erscheinen drei Nullwerte. Ein erneuter HTML-Aufruf liest den aktuellen
Stand, auch nach Abschluss oder Wiederaufnahme eines Falls. Keine Live-Aktualisierung
anderer geöffneter Tabs; AJAX-Listenfilter verändern die globale Übersicht nicht.

Der Slice `get_status_overview` validiert die injizierte Benutzeridentität und
liefert ein unveränderliches DTO über einen eigenen Lese-Port. Sein SQLAlchemy-
Adapter aggregiert mit der gemeinsamen Eigentumsabfrage direkt in PostgreSQL.
Weder Falldetails noch alle Listeneinträge werden geladen. Der System-API-Key
öffnet keine globale Browserübersicht. Composition Root und Fachgrenzen bleiben
erhalten; keine Migration, zusätzliche Bibliothek oder neue Konfiguration.

Die drei gleich gewichteten Karten verwenden bestehende Statusfarben und
Textbeschriftungen, semantische Definitionslisten sowie responsive Bootstrap-
Spalten. Englisch und Deutsch werden serverseitig übersetzt; JavaScript ist
für diese Anzeige nicht erforderlich.
