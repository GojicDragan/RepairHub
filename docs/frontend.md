# Frontend: Bootstrap und Humble Objects

Entscheidung vom 21. September 2026 auf Benutzerwunsch; Bezug M07, N09–N10.
Jinja erzeugt die Seiten weiterhin serverseitig. Bootstrap 5.3.8 stellt Layout,
Abstände, Buttons und Meldungen bereit. Die unveränderte CSS-Datei und MIT-Lizenz
liegen unter `app/web/static/vendor/bootstrap-5.3.8/`. Herkunft:
[offizieller Release](https://github.com/twbs/bootstrap/tree/v5.3.8),
[Einbindung und veröffentlichter SHA-384](https://getbootstrap.com/docs/5.3/getting-started/introduction/).
Der Download wurde gegen den veröffentlichten SHA-384 geprüft. Updates erfolgen
explizit mit Versionswechsel, Lizenz-/Integritätsprüfung und Browserprüfung.

Es gibt keine CDN-Anfragen, npm-Abhängigkeiten oder einen zusätzlichen Frontend-
Build. Bootstrap-JavaScript wird erst eingebunden, wenn eine seiner interaktiven
Komponenten benötigt wird. Die aktuelle Rückmeldung verwendet native DOM-APIs.
Nginx liefert ES-Module mit JavaScript-MIME-Typ aus; die CSP erlaubt Skripte nur
von der eigenen Origin, ohne Inline-Skripte oder `eval`.

## Zuständigkeiten

- **Jinja/HTML:** semantisches Markup und Bootstrap-Klassen; `data-*`-Attribute
  sind die Hooks für Interaktion, keine CSS-Klassenselektoren im Presenter.
- **Presenter:** `notification-presenter.mjs` entscheidet über den UI-Ablauf.
  Er kennt nur `focusReturnTarget()` und `remove()` seiner injizierten View,
  keine Browser-Globals, Selektoren, Bootstrap-Klassen oder HTTP-Aufrufe.
- **Humble Object:** `NotificationView` in `notification-view.mjs` übersetzt
  Klicks in Presenter-Aufrufe und führt DOM-Operationen aus. Kein Fachzustand,
  keine Berechtigungsprüfung und keine Kostenberechnung in dieser Schicht.
- **Verdrahtung:** `main.mjs` bindet die Views nach dem Parsen des Dokuments.

Das Muster gilt auch für künftige Formulare und Interaktionen: Verhalten zuerst
in unabhängig testbaren Funktionen/Presentern, DOM- und gegebenenfalls Bootstrap-
Adapter bewusst klein halten. Die Python-Komponentengrenzen bleiben unverändert.
Serverseitige Validierung und CSRF bleiben verbindlich. JavaScript ergänzt den
Bedienkomfort; Navigation, Inhalte und spätere Standardformulare müssen ohne JS
benutzbar bleiben. Schliessbuttons sind ohne JS ausgeblendet, Meldungen sichtbar.
Beim Schliessen erhält der Inhaltsbereich den Fokus. Jinja escaped Meldungstexte.

## Tests

`node --test tests/unit/frontend/*.test.mjs` prüft Presenter mit einer Fake-View,
ohne DOM oder Browser. Lokal geprüft mit Node 24.18.0; CI verwendet das Node.js
auf dem `ubuntu-24.04`-Runner (keine Node-Abhängigkeit im Produktionsimage).
Der Test läuft verpflichtend im Test-Job; ein fehlendes Node führt zum Fehler.

Python-Integration prüft Escaping und HTML-Fallback für Flash-Meldungen. Playwright
prüft Bootstrap-CSS, ES-Module unter echter Nginx-CSP, Schliessen und Fokus sowie
mobile Darstellung ohne JS. Solange Fachrouten fehlen, fügt der Adaptertest eine
Meldung als Browser-Fixture ein; er behauptet keinen fachlichen Speichervorgang.

## Sprache

Englische Quelltexte und Endpoints sind verbindlich. Übersetzungen ausschliesslich
über Flask-Babel/gettext; siehe [i18n-Konvention](i18n.md). Keine deutschen Texte
in Templates oder JavaScript fest codieren.

## Verbindliche visuelle Sprache

Die neue Werkstatt-Gestaltung mit Wort-Bild-Marke, Palette, Typografie,
Formularhierarchie und den angewandten Gestaltregeln ist in
[Design-System](design-system.md) beschrieben. Neue Fachseiten sollen diese Tokens
und Komponenten wiederverwenden. Geplante Funktionen nicht als bereits verfügbare
Aktionen oder mit erfundenen Nutzerdaten darstellen.

## Passwort vergessen

Seit dem Benutzerauftrag vom 21. September 2026 umfasst die Anwendung zusätzlich
Passwort-Recovery. Der Login verlinkt `/reset`; `/reset/<token>` zeigt das Formular
für ein neues Passwort mit Wiederholung. Beide Seiten nutzen das Auth-Layout und
funktionieren ohne JavaScript. Englische Endpoints, englische und deutsche Texte.

## Benutzer-Routen und Anwendungsfälle

`app.web.routes.users` übersetzt HTTP-Eingaben in frameworkfreie Commands und ruft
in der Factory injizierte Handler auf. Der Bibliotheks-Blueprint ist deaktiviert;
Formularklassen dienen der Darstellung und der Validierung im technischen Adapter.
Details: [Benutzeranwendungsfälle](user-use-cases.md).

## Absenden erst bei ausgefüllten Pflichtfeldern

Benutzerwunsch vom 21. September 2026: Registrierung, Login, Passwort-Recovery
und erneuter Versand der Bestätigung deaktivieren den Absende-Button, solange
Pflichtfelder leer sind. Das gemeinsame Formular übernimmt dies auch für die
Eingabe eines neuen Passworts. Optionale Checkboxen und versteckte Felder gehören
nicht zur Vollständigkeitsprüfung.

`FormCompletionPresenter` entscheidet ohne DOM-Abhängigkeit über den Zustand;
`FormCompletionView` liest die markierten Inputs und setzt die native
`disabled`-Eigenschaft. Eingabe, Änderung, Reset, Seitenwiederherstellung und
Autofill werden berücksichtigt. Passwortmanager ohne Eingabeereignis werden
bei sichtbarer Seite alle 500 ms abgeglichen; beim Verlassen stoppt der Timer.
Textfelder mit ausschliesslich Leerzeichen gelten als leer. Passwörter werden
nicht getrimmt. Vollständigkeit ersetzt keine Format-/Passwort-/Servervalidierung.

Die Deaktivierung wird erst mit JavaScript aktiviert. Ohne JavaScript bleiben
Buttons bedienbar; HTML-`required` und die Serverprüfung sichern Pflichtfelder ab.
Damit werden Benutzer ohne JavaScript nicht dauerhaft ausgesperrt.

Prüfung: drei Node-Tests bestanden. Die acht Browserprüfungen aus
`tests/e2e/test_form_completion.py` lokal über Nginx in Englisch und Deutsch
jeweils mit und ohne JavaScript ausgeführt (16 Fälle); Eingeben, Leeren,
Leerzeichen, stilles Autofill und Formular-Reset geprüft. Ruff, Formatierung und
`git diff --check` bestanden. Kein erneuter vollständiger Security-/Deployment-Lauf
für diese Darstellungsänderung.

Beim erneuten Versand des Bestätigungslinks wird zusätzlich die native
E-Mail-Formatprüfung in die Buttonfreigabe einbezogen (`data-validate-email`).
Der DOM-Adapter liefert den Gültigkeitswert, der Presenter entscheidet über die
Freigabe. Keine eigene E-Mail-Regex, keine Netzwerkprüfung des Postfachs.
Die serverseitige Bibliotheksvalidierung bleibt verbindlich. Vier Node-Tests
bestanden; ungültige Formate, gültige Adresse mit Plus-Zusatz, erneutes Leeren
und Autofill auf der Bestätigungsseite in Englisch/Deutsch im Browser geprüft.

### Markeneigene E-Mail-Hinweise

Bestätigungslink erneut senden (`/confirm`) und Passwort wiederherstellen
(`/reset`) verwenden dieselbe E-Mail-Formatprüfung und übersetzte Inline-Hinweise
in der RepairHub-Akzentfarbe. Nach dem ersten Verlassen des Felds erscheint ein
Hinweis für leere bzw. ungültige Eingaben. Korrekturen aktualisieren ihn sofort;
Formular-Reset entfernt den Berührungszustand. Fehlerrahmen, `aria-invalid`,
`aria-describedby` und eine höfliche Live-Region ergänzen die Textmeldung.

Der Browser liefert weiterhin den technischen Syntaxbefund (`validity`), aber
keine Popups: Nach JS-Anbindung setzt der Adapter `noValidate` für diese beiden
Formulare. Der frameworkfreie Presenter entscheidet über Hinweise und Button;
der Humble-Object-Adapter liest und schreibt lediglich den DOM-Zustand. Ohne JS
bleibt die native HTML-Pflichtfeldprüfung aktiv; Servervalidierung gilt immer.

Prüfung: fünf Node-Tests und der Übersetzungskatalogtest bestanden. Beide Seiten
lokal in Chromium bei 390 px auf Deutsch/Englisch geprüft: Format, Hinweise,
Brandfarbe, ARIA-Zustand, Korrektur, Reset, Autofill sowie Fallback ohne JavaScript.
Ruff und `git diff --check` bestanden.

Dieselbe markeneigene E-Mail-Validierung gilt nun auch für `/register`:
Inline-Hinweise und Fehlerrahmen wie bei Bestätigungsversand und Recovery.
Der Registrierungsbutton benötigt weiterhin alle übrigen Pflichtfelder zusätzlich
zur formal gültigen E-Mail-Adresse. Bestehende Browserprüfungen auf Registrierung
erweitert und lokal auf Deutsch/Englisch einschliesslich Fallback ohne JavaScript
geprüft; Ruff, Formatierung und `git diff --check` bestanden.

### Passwortwiederholung

Bei Registrierung und Passwort-Reset muss `password_confirm` exakt mit `password`
übereinstimmen. Der gemeinsame Presenter vergleicht die übergebenen Werte ohne
Trimmen oder Normalisieren; der DOM-Adapter liefert nur Feldnamen, Vergleichsziel
und Werte. Abweichungen deaktivieren den Button. Nach Verlassen der Wiederholung
erscheint ein übersetzter RepairHub-Hinweis am Feld. Änderungen an beiden Feldern
aktualisieren den Zustand; die serverseitige Bibliotheksprüfung bleibt bestehen.

Sechs Node-Tests und der Katalogtest bestanden. Registrierung auf Deutsch/Englisch
im lokalen Browser geprüft, einschliesslich abweichender Leerzeichen, Korrektur,
Änderung des ersten Passworts und leerer Wiederholung. Der bestehende Reset-E2E-
Ablauf enthält zusätzlich eine Prüfung auf deaktiviertes Absenden bei Abweichung;
der vollständige Container-E2E-Lauf wurde hierfür nicht erneut ausgeführt.

Neue Passwörter benötigen zusätzlich mindestens acht Zeichen, bevor der Button
aktiv wird (Registrierung und Reset). Die Mindestlänge kommt aus der bestehenden
Serverkonfiguration; der Presenter zählt Unicode-Codepoints wie Python und trimmt
Passwörter nicht. Nach Verlassen des Felds erscheint bei Unterschreitung ein
übersetzter Inline-Hinweis. Auch identische, aber zu kurze Passwörter bleiben
blockiert. Login übernimmt diese Regel zur Vergabe neuer Passwörter nicht.

Sieben Node-Tests und der Katalogtest bestanden. Die Grenze 7/8 Zeichen,
Unicode-Zeichen, erneutes Kürzen und Kombination mit Passwortwiederholung wurden
lokal auf Deutsch/Englisch im Browser geprüft. Der vorhandene Reset-E2E-Test
wurde um dieselbe Mindestlängenprüfung erweitert, aber nicht erneut als vollständiger
Containerlauf ausgeführt. Ruff, Formatierung und `git diff --check` bestanden.

## T06: AJAX-Geräteformulare und virtuelle Liste

Auf Benutzerwunsch werden Erfassung und Bearbeitung per Fetch ohne Neuladen des
Dokuments ausgeführt. Die erste Liste rendert 20 Geräte serverseitig. Danach
hält der virtuelle Scrollbereich höchstens 60 Zeilen im DOM; Fenster werden auch
beim Zurückscrollen über AJAX nachgeladen. DOM-freie Presenter steuern Speicher-
und Anfragezustände; kleine Views übernehmen DOM und Fetch. Progressive Erweiterung,
CSRF und gettext bleiben erhalten. Details und Grenzen: [Geräteverwaltung](devices.md).

### Autocomplete aus eigenen Geräten

Die Gerätefelder verwenden eine markeneigene Combobox mit weiterhin freier Eingabe.
`DeviceSuggestionsPresenter` koordiniert Eingabepause, Auswahl, Tastatur und veraltete
Antworten; `device-suggestions-view.mjs` kapselt ausschliesslich DOM, Timer und Fetch.
Die serverseitige Eigentumsprüfung und Eingabevalidierung bleiben im Geräte-Slice.
Umfang, Rückfallverhalten und Datenschutz: [Geräteverwaltung](devices.md).

## T07: Reparaturformulare

`RepairFormPresenter` entscheidet DOM-frei über Änderungen, leere Pflichtwerte,
laufende Speicheranfragen und Fehler. `repair-form-view.mjs` bindet delegierte
DOM-Ereignisse und Fetch an serverseitig gerenderte Formulare. Erfassung,
Fehlerbeschreibung, Status und Schritte speichern per AJAX, mit CSRF und einer
normalen POST-Weiterleitung als Rückfall ohne JavaScript. Andere Formularentwürfe
werden beim Ersetzen des Detailbereichs wiederhergestellt, auch vorübergehend
leere Eingaben. Schritte sind auf 20 Einträge je Seite begrenzt; die Reparaturliste
verwendet die unten beschriebene gemeinsame virtuelle Listensteuerung.
Fachregeln und Eigentumsprüfung bleiben ausschliesslich serverseitig in den
injizierten Reparatur-Slices. Details: [Reparaturverwaltung](repairs.md).


### Gemeinsame virtuelle Listen für Geräte und Reparaturfälle

`virtual-list-presenter.mjs` enthält die gemeinsame DOM-freie Fenstersteuerung
(20er-Seiten, höchstens 60 sichtbare/vorgeladene Zeilen, Schutz vor verspäteten
Antworten). `virtual-list-view.mjs` kapselt Fetch, Platzhalter, Tastatur/Fokus,
Fehlerwiederholung und benutzer-/listenbezogene Scrollpositionen. Geräte und
Reparaturen liefern nur ihre jeweiligen Zeilen-Renderer; keine kopierte zweite
Scrollimplementierung. Der bisherige Geräte-Presenter exportiert die gemeinsame
Klasse kompatibel weiter. Bestehende URL-Filter werden beim Nachladen erhalten.

Reparaturzeilen verwenden dieselbe Höhe von 112 px und denselben gebrandeten
Scrollbereich. Nutzereingaben werden über `textContent` gerendert. Ohne JavaScript
bleiben SSR-Seiten und Seitenlinks nutzbar. Listenfenster und Eigentumsprüfung
werden unabhängig davon im jeweiligen Python-Slice begrenzt.

### T08: Teile und Arbeitswerte im Reparaturdetail

Die zusätzlichen Formulare nutzen dieselben `RepairFormPresenter`- und
`repair-form-view`-Instanzen wie Beschreibung, Status und Schritte. Keine zweite
AJAX-Implementierung und keine clientseitige Kostenformel. Die Serverantwort
aktualisiert den gesamten Arbeitsbereich samt Kosten und erhält andere Entwürfe.
Teilepositionen werden wie Schritte in 20er-Seiten angezeigt. Details:
[Teile und Kosten](parts-and-costs.md).

## Persönlicher API-Key

`/account/api-key` verwendet das bestehende Bootstrap-/Markensystem, englische
Msgids und deutsche Übersetzungen. Erzeugen/Ersetzen und Widerrufen sind
sitzungsgebundene CSRF-geschützte Formulare, vollständig ohne JavaScript nutzbar.
Der Klartext wird nur in der unmittelbaren POST-Antwort angezeigt; keine
Speicherung in Flash, Session oder Local Storage.


## T10: durchgängige Bedienung und Fehlerpfade

Die Hauptnavigation markiert den aktuellen Fachbereich mit `aria-current`;
Geräte- und Reparaturdetails bleiben ihrem Bereich zugeordnet. Die Startseite
beschreibt die inzwischen vorhandenen Funktionen ohne Ankündigung als Zukunftsplan.
Beim Blättern durch Reparaturschritte bleiben Gerätefilter und Teilefenster erhalten.

Reparaturformulare fokussieren nach AJAX-Validierungsfehlern das erste betroffene
Feld. Zahlenfelder tragen auch in serverseitigen Fehlerantworten `aria-invalid`.
Bei HTTP 401 entscheidet der DOM-freie Presenter über den Anmeldehinweis; die View
zeigt die übersetzte Meldung und den Login-Link, ohne Entwürfe automatisch zu
verwerfen oder weiterzuleiten. Fachvalidierung und Berechtigungen bleiben serverseitig.

Der Registrierungs-E2E-Ablauf führt jetzt nach der echten E-Mail-Bestätigung über
sichtbare Navigation bis zu Geräten, Reparaturschritten, Status und CHF-Kosten.
Englisch/Deutsch, mit/ohne JS, negative Zahleneingaben, erhaltene Formularwerte,
Abmeldung und mobile Ansichten gehören zur Abnahme. Ein absichtlich unterbrochener Request prüft Netzwerkfehler; eine tatsächlich
entfernte Browsersitzung prüft die UI-Reaktion auf 401 einschliesslich verfallenem CSRF-Wert. Ergebnisse: [T10](t10-validation.md).

## K-T01: Reparatursuche

Suche und Status bilden eine gemeinsame Bootstrap-Formulargruppe über der
Reparaturliste. Das GET-Formular funktioniert ohne JavaScript. Mit JavaScript
koordiniert der DOM-freie `ListFilterPresenter` eine Eingabepause von 300 ms;
Statuswechsel und Enter reagieren sofort; der Anwenden-Button erscheint nur
ohne JavaScript als Fallback. Timer und DOM bleiben
im View-Adapter. Die gemeinsame virtuelle Listensteuerung verwirft alte Antworten
bereits beim Tippen und lädt neue Filter ohne alten Snapshot ab Position null.
Sie übernimmt die Filter aus der Daten-URL für alle weiteren AJAX-Fenster.
Keine neue Browser-Fachlogik oder zweite Listenimplementierung. Detailnavigation
und Rückweg erhalten die Filter. Verhalten und Suchsemantik: [Reparaturen](repairs.md).

### Lokale Template- und Moduländerungen

In Development ist `TEMPLATES_AUTO_RELOAD` explizit aktiv, während Debug deaktiviert
bleibt. Gunicorns Python-Reload allein erkennt Änderungen an Jinja-Templates nicht
zuverlässig. Ohne diese Einstellung kann ein altes Formular ohne Debounce-Hook mit
neuem JavaScript kombiniert werden. Nginx verlangt für lokale statische Dateien
mit `expires -1` eine Revalidierung; Produktions-Caching bleibt unverändert.
Bereits geöffnete Seiten nach Änderungen neu laden.

## K-T02: Gerätesuche mit derselben Listensteuerung

Die Geräteliste verwendet das vorhandene `data-list-filters`-Formular und den
DOM-freien `ListFilterPresenter` aus der Reparatursuche. Das Statusfeld ist im
Humble-Object-Adapter optional; eine reine Textsuche benötigt keinen unsichtbaren
Statusfilter. Trefferzahl, Leerzustand, Zurücksetzen, Fehlerwiederholung und Scroll-Reset
verwenden dieselbe virtuelle Liste. Gerätezeilen bauen Detail-/Bearbeitungslinks
über die URL-API auf, damit Suchparameter nicht Teil des URL-Pfads werden.

## K-T03: Statusübersicht

Die Reparaturliste erhält drei gleich gewichtete Statuskarten vor den Filtern.
Die Angaben beziehen sich ausdrücklich auf alle eigenen Geräte, unabhängig von
Listenfiltern. Semantische Definitionslisten verbinden Zahl und Statusbeschriftung;
Statusfarben entsprechen den vorhandenen Badges. Bootstrap stapelt die Karten auf
kleinen Bildschirmen. Die Anzeige entsteht vollständig auf dem Server und braucht
weder einen zusätzlichen Presenter noch JavaScript. Bestehende AJAX-Filter und
virtuelle Fenster bleiben unabhängig; beim nächsten HTML-Aufruf werden die Zahlen
neu gelesen. Details: [Reparaturverwaltung](repairs.md#statusübersicht-k-t03).
