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
