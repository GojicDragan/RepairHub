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
