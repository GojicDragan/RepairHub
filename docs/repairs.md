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

`app.domains.repairs` enthält sieben vertikale Slices: `create_repair`,
`list_repairs`, `get_repair`, `update_description`, `change_status`, `add_step`
und `update_step`. Jeder besitzt eigene Commands, Ports und Handler. Gemeinsame
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
