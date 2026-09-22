# Bilder zu Geräten und Reparaturfällen (K-T04)

Benutzer laden auf der Detailseite eigener Geräte und Reparaturfälle Bilder hoch.
Erlaubt sind JPEG, PNG und WebP mit höchstens 10 MiB und 20 Millionen Pixeln.
Animierte Bilder, PDF, SVG und beschädigte Dateien werden abgewiesen. Die tatsächlichen
Bilddaten entscheiden, nicht die Dateiendung oder der vom Browser gemeldete MIME-Typ.

Die Detailseite zeigt ein responsives Mosaik mit höchstens 24 Bildern pro Seite.
Hoch- und Querformate erhalten passende Rasterflächen; auf kleinen Bildschirmen
bleiben zwei Spalten. Vorschaubilder sind maximal 640 Pixel gross und werden verzögert
geladen. Weitere Bilder sind über die nächste Seite erreichbar; der DOM wächst nicht
unbegrenzt. Ein Klick öffnet das vollständige Bild. Uploads funktionieren mit AJAX
und ohne JavaScript. Während des Uploads und ohne gewählte Datei bleibt der Button
inaktiv. Englische und deutsche Texte verwenden die vorhandene Browser-Sprachwahl.

## Daten und Berechtigungen

Die vertikalen Slices `upload_image`, `list_images`, `get_image` und `delete_image` gehören jeweils
zu `devices` beziehungsweise `repairs`. Sie prüfen Eigentümerschaft vor Bildverarbeitung
oder Speicherzugriff. Ports für Metadaten, Bildverarbeitung und Objektspeicher werden
in `app.bootstrap` injiziert. Der Fachkern importiert weder Flask noch SQLAlchemy,
Pillow oder boto3. Technische Wiederverwendung liegt unter `app.data.files`.

Pillow dekodiert das Bild, korrigiert EXIF-Orientierung und erzeugt neue WebP-Pixelbilder.
EXIF/GPS, Kommentare und angehängte Daten werden nicht übernommen. Es handelt sich
somit nicht um ein unverändertes Originalarchiv. Originalgrösse und Vorschau bekommen
zufällige serverseitige Schlüssel; Benutzernamen oder Dateinamen werden nicht zu Pfaden.
Die additive Migration `0006_images` speichert Zuordnung und Metadaten in zwei Tabellen.

Garage ist privat. Browser erhalten keine S3-Zugangsdaten oder öffentlichen Objekt-URLs.
`/devices/{id}/images` und `/repairs/{id}/images` bieten Liste und CSRF-geschützten
Upload. `.../images/{image_id}` liefert das Bild nach erneuter Eigentumsprüfung
(`?thumbnail=1` für Vorschauen), mit `private, no-store` und `nosniff`.
Fremde und unbekannte Objekte ergeben gleichartige 404-Antworten; Bildabrufe ohne
Anmeldung ergeben 401. Die lesende Reparatur-API wird nicht um Dateioperationen erweitert.

Beide Objekte werden vor dem Metadatensatz geschrieben. Nach einem Speicherfehler wird
kein unvollständiger Datensatz veröffentlicht. Bei einem mehrdeutigen Datenbankfehler
können unreferenzierte private Objekte zurückbleiben: automatisches Löschen könnte ein
trotz Verbindungsabbruch erfolgreich gespeichertes Bild zerstören. Eine spätere
Bereinigung benötigt einen expliziten Referenzabgleich; sie ist nicht Teil dieses Tasks.

## Lokale Einrichtung

Vor dem ersten Compose-Start einmal `uv run --locked python scripts/setup_storage.py`
ausführen. Das erzeugt `garage.env` und `storage.env` mit Berechtigung 0600 und gibt
keine Geheimnisse aus. Vorhandene Dateipaare bleiben erhalten; unvollständige Paare
werden nicht stillschweigend überschrieben. Beide Dateien sind von Git ausgeschlossen.
Danach das App-Image neu bauen, Garage starten und `flask --app app db upgrade` ausführen
(siehe README). Ein bestehendes Garage-Volume niemals mit neu generierten Schlüsseln
kombinieren. Das dauerhafte Volume heisst im Compose-Projekt `garage_data`.

## Produktion und Sicherung

Siehe [Garage-Betrieb](garage.md), [CI/CD](ci-cd.md) und [Prüfnachweis](kt04-validation.md).

## Bilder löschen

Jede Mosaikkachel enthält «Löschen» mit einer aufklappbaren Bestätigung. Der
CSRF-geschützte POST-Endpunkt `.../images/{image_id}/delete` entfernt den
Eigentumsverweis atomar. AJAX aktualisiert nur die Galerie; ohne JavaScript folgt
eine Weiterleitung zur Detailseite. Fremde, unbekannte und bereits gelöschte Bilder
liefern 404. Original und Vorschau sind nach erfolgreicher Löschung nicht mehr abrufbar.
Es gibt keine Löschung per GET und keine Erweiterung der lesenden API.

Die unveränderlichen Garage-Objekte bleiben vorerst privat gespeichert. Dies erhält
die Konsistenz der bisherigen Sicherungsreihenfolge (Datenbanksnapshot vor
Objektexport) auch bei gleichzeitigem Löschen. Eine physische Speicherbereinigung
oder garantierte vollständige Datenvernichtung ist nicht implementiert. Dafür braucht
es einen separaten, mit laufenden Sicherungen abgestimmten Aufbewahrungs-/Bereinigungsablauf.
