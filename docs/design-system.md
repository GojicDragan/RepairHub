# RepairHub: Marke und Gestaltung

Umgesetzt am 21. September 2026 auf Benutzerwunsch. Bezug: M07, F15, N06, N09–N10.
Das Thema ist eine ruhige, sorgfältig organisierte Reparaturwerkstatt. Der englische
Markengedanke lautet «Good things deserve a second life.» Wiederverwenden und
Reparieren prägen Wortwahl, Farben und Illustration.

## Visuelles System

| Element | Festlegung |
| --- | --- |
| Grundfläche | Warmes Off-White `#f8f6f0` |
| Text und dunkle Markenfläche | Dunkelgrün `#243b35` |
| Hauptaktion und Akzente | Rostorange `#b84020` |
| Sekundärer Text | `#58645e` |
| Trennlinien | `#d9dcd1` |
| Schrift | Lokale System-Sans; Monospace für kurze Abschnittskennzeichnungen |
| Bildsprache | Eigene SVG-Linienzeichnung eines reparierbaren Radios; dekorativ |
| Markenzeichen | Eigene Schraubenschlüssel-SVG und RepairHub-Wortmarke |

Bootstrap bleibt die Grundlage. `app/web/static/app.css` definiert zentrale Tokens
und Komponentenvarianten. SVGs sind eigene lokale Template-Partials; keine externen
Bilder, Fonts, CDNs, neuen Bibliotheken oder JavaScript-Frameworks.

## Gestaltregeln in der Umsetzung

- **Nähe:** Feldlabel, Eingabe, Hilfetext und Fehler bilden eine Gruppe. Abstände
  zwischen Gruppen sind grösser als innerhalb einer Gruppe.
- **Gemeinsame Region:** Kontoformulare stehen auf einer hellen, zusammenhängenden
  Fläche. Markenstory und Formular haben klar getrennte, aufeinander ausgerichtete
  Bereiche. Mobile reduziert die Story auf einen kurzen Einstieg.
- **Ähnlichkeit:** Gleiche Farben, Radien, Schriftgewichte und Abstände kennzeichnen
  gleiche Funktionen. Primäre Aktionen sind rostorange; Navigation und ergänzende
  Links sind zurückhaltender.
- **Figur und Grund:** Dunkler Text auf ruhigen Flächen und gezielter Akzent schaffen
  eine klare Hierarchie zwischen Überschrift, Erklärung und Handlung.
- **Ausrichtung und Fortsetzung:** Ein gemeinsames Raster verbindet Kopfzeile,
  Inhalte und Fusszeile. Desktop-Spalten wechseln mobil in eine eindeutige Lesereihenfolge.

Die Startseite benennt geplante Geräte-/Reparaturfunktionen ausdrücklich als
«Coming next». Sie zeigt keine erfundenen Falldaten oder funktionslosen Aktionsbuttons.
Die Illustration und ihr Siegel sind dekorativ und nicht interaktiv.

## Bedienbarkeit und Architektur

Registrierung: Benutzername → E-Mail → Passwort → Wiederholung. Passwortanforderungen
stehen am Feld und sind über `aria-describedby` zugeordnet. Passende `autocomplete`-
Attribute unterstützen Passwortmanager. Labels bleiben immer sichtbar. Bestehende
Bibliotheksvalidierung, CSRF und Mailabläufe bleiben erhalten.

Die Oberfläche verwendet semantische Landmarken, genau eine H1 je Seite, einen
Skip-Link, sichtbare Tastaturfokusse und eine englische HTML-Sprachangabe. SVG-Dekor
ist für Screenreader ausgeblendet. Reduzierte Bewegung wird respektiert. Die
Anwendung bleibt ohne JavaScript bedienbar; bestehende Notification-Humble-Objects
bleiben unverändert. Texte sind weiterhin über gettext übersetzbar.

## Lokaler Nachweis

- Produktionsimage neu gebaut und mit PostgreSQL auf Bereitschaft geprüft.
- 89 PostgreSQL-Integrationstests bestanden, einschliesslich Formulare und i18n.
- Desktop-Screenshots bei 1440 px und mobile Screenshots bei 390 px visuell geprüft.
- Startseite, Registrierung, Anmeldung, Bestätigung und Fehlerseite zusätzlich bei
  320, 360 und 768 px ohne JavaScript geprüft: kein horizontaler Überlauf.
- Reihenfolge der Formularfelder und Autocomplete im echten Browser kontrolliert.
- Screenshots lokal unter `reports/ui/`; keine Produktionsbereitstellung.

Die Entwicklung verwendet Quellcode-/CSS-Mounts. Der lokale Gunicorn wurde zur
Übernahme gecachter Vorlagen neu geladen; vorhandene Benutzer und Daten bleiben erhalten.

Die zentralen Text-/Flächenpaare wurden rechnerisch auf Kontrast geprüft:
weiss auf Rostorange 5.54:1, Rostorange auf Formularfläche 5.49:1, sekundärer Text
auf Grundfläche 5.72:1, Haupttext 11.09:1 und heller Story-Text auf Dunkelgrün 9.22:1.
Dies ist keine vollständige Barrierefreiheitszertifizierung.

Bootstraps weiches Scrollen ist im Theme gezielt deaktiviert. Beim Fokussieren und
Absenden langer Formulare bleibt die Position dadurch auch ohne JavaScript stabil.
Der reproduzierte No-JavaScript-Scrollfehler wurde ohne erzwungene Testklicks behoben.

Abschliessend alle 10 Browserprüfungen gegen das neu gebaute Image bestanden,
einschliesslich Registrierung, lokaler Bestätigungsmail, Login und Logout mit/ohne
JavaScript. Der bestehende Humble-Object-JS-Test besteht ebenfalls. Ruff,
Formatprüfung und `git diff --check` bestanden. Security-Scans und Ansible wurden
für diese reine Darstellungsänderung nicht erneut ausgeführt.

## Transaktionale E-Mails

Willkommens- und erneut angeforderte Bestätigungsmails verwenden dieselbe Palette,
Wortmarke, englische Markensprache und Hierarchie. Gemeinsames Layout:
`app/web/templates/security/email/_base.html`. Dunkelgrüner Kopf, helle Inhaltsfläche,
rostoranger Bestätigungsbutton, Gültigkeitshinweis, kopierbarer Ersatzlink und
zurückhaltender Sicherheitshinweis bilden klar getrennte Gruppen.

E-Mail-HTML verwendet Präsentationstabellen und Inline-CSS statt Bootstrap, Flexbox
oder externen Stylesheets. Breite maximal 600 px, Systemschriften, keine externen
Bilder, Webfonts, Skripte oder Tracking-Anfragen. Lange Bestätigungslinks können
umbrechen. Für klassische Outlook-Layouts ist eine bedingte Breitentabelle enthalten.
Die HTML-Vorlage erbt nicht vom Browserlayout. Palettenänderungen deshalb auch im
E-Mail-Basislayout nachvollziehen. Englische Texte verwenden weiterhin gettext.

Jede Nachricht behält ihren Plain-Text-Teil mit Link und Markensignatur. Der SMTP-
Integrationstest prüft beide MIME-Teile und die HTML-Gestaltung. 89 Integrationstests
bestanden. Beide Mailtypen mit überlangem Testlink bei 800 und 360 px gerendert;
kein horizontaler Überlauf, mobile Vorschau visuell geprüft. Browser-Vorschauen
unter `reports/ui/emails/`. Native Outlook-/Gmail-/Apple-Mail-Tests nicht ausgeführt.

## Deutsche Darstellung

Die Marke ist nun auch vollständig deutsch verfügbar; englische Quelltexte bleiben
die gettext-Basis. Sprache folgt `Accept-Language` mit Englisch als Fallback.
85 eigene Texte sind übersetzt, Bibliothekslabels und Mailbetreffzeilen kommen aus
dem mitgelieferten deutschen Flask-Security-Katalog. Die Wortmarke bleibt RepairHub.
Deutsche Seiten bei 320/390/1440 px und die deutsche Mail bei 320 px mit überlangem
Ersatzlink geprüft. Bei sehr schmalen Ansichten erhält die Navigation zwei Zeilen,
statt übersetzte Beschriftungen abzuschneiden. Details: `docs/i18n.md`.

## Favicon und Suchmetadaten (21. September 2026)

Das vorhandene Schraubenschlüssel-Zeichen ist als eigenständiges `favicon.svg`
mit festen Markenfarben eingebunden. PNG-Varianten: 96 px für Browser/Suche,
180 px für Apple-Touch-Icon und 512 px als quadratisches Social-Sharing-Bild.
Die Rasterdateien wurden mit Chromium aus demselben SVG gerendert; keine neue
Laufzeitabhängigkeit. Bei einer Änderung am Zeichen alle Varianten aktualisieren.
Die Nginx-CSP erlaubt dafür Bilder vom eigenen Ursprung (`img-src 'self'`).

`partials/metadata.html` liefert übersetzte Beschreibungen, Robots-Regeln und für
die anonyme Startseite Canonical-, Open-Graph- und Twitter-Card-Tags. Titel und
Beschreibungen folgen derselben Browser-Sprachwahl wie die Seite. Absolute URLs
verwenden die über `PUBLIC_URL` konfigurierte Domain und das konfigurierte Schema;
Query-Parameter, Bestätigungstokens und Benutzernamen werden nicht übernommen.
Nur die anonyme Produktionsstartseite ist indexierbar. Konto-, Bestätigungs-,
Fehlerseiten und angemeldete Ansichten sowie Entwicklungs-/Testumgebungen erhalten
`noindex, nofollow`. Das ist eine Suchmaschinenanweisung, kein Zugriffsschutz.

Grundlagen: [Google-Favicon-Dokumentation](https://developers.google.com/search/docs/appearance/favicon-in-search)
und [noindex](https://developers.google.com/search/docs/crawling-indexing/block-indexing).
Keine künstlichen Sprach-URLs oder hreflang-Verweise: Beide Sprachen nutzen dieselbe
URL mit HTTP-Sprachaushandlung. Bestehende Produktionshosts benötigen für die neue
Nginx-CSP die in `docs/ci-cd.md` beschriebene Infrastruktur-Aktualisierung.

Prüfung: 27 gezielte Metadaten-/Sprach-/Katalogtests bestanden; Ruff,
Architekturprüfung und `git diff --check` bestanden. Im lokalen Chromium über Nginx
beide Sprachen geprüft und sämtliche Icons erfolgreich unter der CSP geladen.
Lokale Nginx-Konfiguration validiert und neu geladen. Keine Produktionsbereitstellung
oder tatsächliche Suchmaschinenindexierung durchgeführt.

## Kombinierte Anmeldung (21. September 2026)

Login enthält ein Textfeld «Email or username» / «E-Mail oder Benutzername» vor
«Password» / «Passwort». `autocomplete="username"` unterstützt Passwortmanager;
kein E-Mail-Inputtyp erzwingt eine E-Mail-Adresse. Registrierung behält separate
Felder. `CombinedLoginForm` im technischen Identitätsadapter verwendet den
Identity-Lookup von Flask-Security; Passwortprüfung, Bestätigungspflicht, Sitzungen
und CSRF bleiben Bibliotheksabläufe. Keine JavaScript-Abhängigkeit.

Positive Tests decken beide Identitätsarten mit Gross-/Kleinschreibung ab,
negative Tests falsche Passwörter, unbekannte/leere Identität und den bestehenden
Bestätigungsschutz. PostgreSQL-Integrationssuite inklusive Migration/Schemaabgleich
erfolgreich; Katalog-, Ruff- und Architekturprüfung bestanden. Feldreihenfolge
und Sichtbarkeit lokal bei 390 px in Englisch/Deutsch ohne JavaScript geprüft.

## Scrollbar der Geräteliste

Die native Scrollbar verwendet Rostorange auf der warmen Grundfläche. Ihre
Systembreite sowie Tastatur- und Touchbedienung bleiben erhalten; ein stabiler
Scrollbarrand verhindert seitliche Layoutsprünge. Für ältere WebKit-Browser
besteht ein CSS-Fallback mit abgerundetem Griff. Im erzwungenen Kontrastmodus
gelten Systemfarben. Keine JavaScript-Scrollbar und keine neue Abhängigkeit.

Am 22. September 2026 mit dem echten Stylesheet in Chromium geprüft: berechnete
Markenfarben, Scrollfunktion und Systemfarben im Kontrastmodus. WebKit-Fallback
nicht separat im Browser geprüft.
