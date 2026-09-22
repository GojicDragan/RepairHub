# Ersatzteile und geschätzte Reparaturkosten (T08)

## Fachregeln und Beispiele

Jeder eigene Reparaturfall erhält Arbeitsstunden und Stundensatz sowie beliebig
viele Ersatzteilpositionen mit Bezeichnung, Einzelpreis und positiver ganzer Menge.
Neue und vorhandene Fälle starten mit Arbeitswerten von null. Teile können
hinzugefügt und bearbeitet werden; Löschen und Lagerverwaltung sind nicht vorgesehen.

Die reine Funktion `app.domains.costs.model.calculate` berechnet:

`Arbeitsstunden × Stundensatz + Summe(Einzelpreis × Menge)`

Alle Beträge sind CHF. Python verwendet ausschliesslich `Decimal`, PostgreSQL
`NUMERIC`. Erst die Gesamtsumme wird mit `ROUND_HALF_UP` auf zwei Nachkommastellen
gebracht. Die ebenfalls angezeigten Arbeits-/Teilesummen und Positionsbeträge
verwenden dieselbe Funktion. Kein Gesamtbetrag wird unabhängig gespeichert oder
vom Browser übernommen. Die spätere API erhält die Kosten über `GetRepair`.

- 2 Stunden × CHF 80 + 3 × CHF 15 = **CHF 205.00**.
- Dieselbe Arbeit ohne Teile = **CHF 160.00**.
- 3 × CHF 0.10 = **CHF 0.30**.
- 0.01 Stunden × CHF 0.50 = **CHF 0.01**, kaufmännisch gerundet.

Eingabegrenzen, ausgehend von den Fachwerten:

| Wert | Grenze | Persistenz |
| --- | --- | --- |
| Bezeichnung | 1–200 Zeichen, getrimmt, keine Steuerzeichen | VARCHAR(200), Pflichtfeld |
| Arbeitsstunden | 0–999999.99, höchstens 2 Nachkommastellen | NUMERIC(8,2) |
| Stundensatz / Einzelpreis | CHF 0–999999999.99, höchstens 2 Nachkommastellen | NUMERIC(11,2) |
| Menge | 1–2147483647, ganzzahlig | INTEGER |

Die numerischen Grenzen sind technische Konkretisierungen, keine vorgezogenen
Tabellenvorgaben. Leere, negative, nichtnumerische Werte, NaN, Unendlich,
Exponentenschreibweise und zusätzliche Nachkommastellen werden abgewiesen, bevor
PostgreSQL einen Wert runden könnte. JSON übergibt Dezimalwerte als Strings mit
Punkt; binäre Float-Eingaben und boolesche Mengen werden abgewiesen. Native
Zahlenfelder übernehmen die Browsereingabe; die Servervalidierung bleibt verbindlich.

## Architektur und Zugriff

- `parts.add_part` und `parts.update_part` besitzen eigene Commands, Ports und
  Handler. Sie prüfen Identität, Zuordnung und Werte und verwenden `costs` für
  den Positionsbetrag. Die Datenadapter kennen ausschliesslich Domain-DTOs/Ports.
- `repairs.update_work` verwaltet Arbeitswerte. `repairs.get_repair` führt die
  Berechnungsgrundlagen aus dem eigenen Repository der reinen Kostenfunktion zu.
  Es importiert keine Teile-Slices. Die Fallauskunft besitzt eigene Positions-DTOs.
- `app.bootstrap` injiziert alle konkreten Adapter. Keine neue Fachabhängigkeit:
  ausschliesslich die bereits vorgesehenen `parts → costs` und `repairs → costs`.
- Eigentumsgebundene Abfragen verknüpfen Position → Fall → Gerät → Benutzer.
  Beim Schreiben erneut prüfen und Zeile bis zum Commit sperren. Fehler rollen
  die gesamte Operation zurück; fremde/unbekannte Objekte liefern gleichartige 404.

## Oberfläche und HTTP

Das vorhandene Reparaturdetail zeigt Arbeitswerte, Kostenzusammenfassung und Teile.
Die Formulare verwenden den gemeinsamen DOM-freien Reparatur-Presenter und dessen
Humble-Object-Adapter. AJAX ersetzt serverseitig gerendertes, escapedes HTML und
aktualisiert damit auch die Kosten. Ungespeicherte andere Formulare bleiben erhalten.
Ohne JavaScript führen erfolgreiche POSTs über HTTP 303 zurück zum Detail.

- `POST /repairs/<id>/work`
- `POST /repairs/<id>/parts`
- `POST /repairs/<id>/parts/<part_id>`

Dies sind CSRF-geschützte Browserendpunkte, keine Erweiterung der geplanten
lesenden REST-API. Validierungsfehler liefern HTTP 422 mit übersetzten Feldmeldungen.
Englische URLs und Msgids, deutsche Übersetzung anhand von Accept-Language.
Leere und unveränderte Formulare werden mit JavaScript nicht abgesendet.

Die Teileliste zeigt 20 Positionen pro Seite (`part_offset`); Schritte und Teile
haben getrennte Offsets. Für die exakte Summe lädt die Fallauskunft derzeit alle
zugehörigen Positionswerte. Die DOM-Grösse ist begrenzt, der Speicherbedarf dieser
Berechnungsgrundlage wächst mit der Anzahl Positionen. Geräte- und Reparaturlisten
behalten ihre bestehende virtuelle Scrollsteuerung.

## Migration und Betrieb

`0004_parts_and_work` ergänzt `part_items` und zwei Arbeitswert-Spalten an
`repairs`. Vorhandene Benutzer, Geräte, Fälle und Schritte bleiben erhalten;
Arbeitswerte erhalten null. Fremdschlüssel, Pflichtfelder und Wertebereiche sind
auch in PostgreSQL abgesichert. Keine gespeicherten Summen, keine neuen Secrets,
Images, Bibliotheken oder Umgebungsvariablen.

Ansible sichert vor dem Schema-Upgrade und führt Alembic im neuen App-Image aus.
Die Migration ist additiv und zum bisherigen Image kompatibel. Wiederholtes
`upgrade` wendet sie nicht erneut an; ein datenlöschendes Downgrade ist gesperrt.
Prüfergebnisse und noch ausstehende externe Abnahme: [T08-Nachweis](t08-validation.md).
