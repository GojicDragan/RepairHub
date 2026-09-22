# K-T02 – Suche in der Geräteliste

## Ergebnis und Architektur

Die Geräteliste durchsucht eigene Bezeichnungen, Hersteller und Modelle.
Mehrere Teilwörter müssen vorkommen, dürfen aber verschiedene Felder treffen.
Gross-/Kleinschreibung ist unerheblich; Umlaute werden nicht umgeschrieben.
Literalzeichen, Eingabegrenzen und Sortierung: [Geräteverwaltung](devices.md).

Erweitert wurde der bestehende Slice `list_devices`: Command und Repository-Port
tragen den Suchtext, der Handler validiert und normalisiert ihn. Suchtechnik,
Eigentumsabfragen und begrenzte Fenster liegen im Datenadapter. Keine Abhängigkeit
von Flask oder ORM im Fachkern; Composition Root und Komponentengrenzen bleiben
unverändert. Keine neue Bibliothek, Migration, Environment-Variable oder Secret.

Suche nach 300 ms Eingabepause, SSR-Startseite mit 20 Zeilen, virtuelle AJAX-Fenster
mit maximal 60 Zeilen, Leerzustand und Wiederholen verwenden die gemeinsame
Listensteuerung. Ein Statusfeld ist dabei optional. Englische Originaltexte und
deutsche Übersetzungen sind vorhanden. Ohne JS funktioniert das GET-Formular.
Geräte-Links werden korrekt aus Pfad und Query gebaut; Details, Bearbeitung und
Rückweg erhalten den Suchbegriff und die URL-gebundene Scrollposition.

## Abnahmefälle

| Fall | Nachweis |
| --- | --- |
| Begriffe in allen drei Feldern, unterschiedliche Schreibweise, Umlaute | PostgreSQL-Beispiele für `RAD`, `MÜLL`, `rx/2` und feldübergreifende Kombination |
| Keine Treffer, leere Suche, Literalzeichen | PostgreSQL: `%`, `_`, Backslash, SQL-/HTML-Zeichen und Leerzeichen; keine Wildcard- oder SQL-Ausführung |
| Ungültige Eingaben | Domain und HTTP weisen überlange Texte und Steuerzeichen zurück |
| Fremde Konten | Kein Treffer, Maximum oder Trefferzähler eines anderen Benutzers; ohne Sitzung JSON 401 |
| Fenster und Snapshot | 85 eigene Treffer in getrennten Fenstern, später angelegtes Gerät ausgeschlossen; SSR auf 20 begrenzt |
| Debounce und Fokus | Mehrere schnelle Eingaben erzeugen eine Anfrage; kein Dokumentneuladen, Fokus bleibt im Suchfeld |
| Scrollen und Navigation | 240 Treffer im Browser, begrenztes Fenster, Detail/Bearbeitung/Rückweg erhalten Suche und Scrollposition |
| Leere Suche nach Zurücksetzen | Gesamtbestand wieder sichtbar, Scrollposition null; neue Suche nach leerem Ergebnis möglich |
| Netzwerkfehler | Abgebrochener Fetch zeigt Wiederholen; Wiederholung nach Aufheben der Störung funktioniert |
| Deutsch/Englisch und No-JS | Vier Browservarianten, GET-Pagination ohne JS; mobile Ansicht ohne horizontalen Überlauf |

## Prüfstand

631 Unit-Tests einschliesslich 97 Architekturtests bestanden; Architektur-Skript
meldet keine unerlaubten Imports. Alle 27 bestehenden JavaScript-Tests bestanden.
Alle 298 PostgreSQL-Integrationstests bestanden.
Alle 15 ausgewählten Browserfälle bestanden: vier neue Suchfälle sowie bestehende
Geräte- und Reparaturfilterprüfungen. Die mobile deutsche Ansicht wurde visuell geprüft. Ruff, Formatierung, Katalogtest und Diff-Prüfung bestanden.

Produktionsimage gebaut und mit PostgreSQL/HTTPS auf Bereitschaft geprüft.
Isolierter Ansible-Erstlauf inklusive HTTPS-/API-Abnahme bestanden (`changed=33`).
Identische Wiederholung bestanden (`changed=0`), Container-IDs und Startzeiten
unverändert. Der isolierte Testhost wurde danach entfernt. pip-audit, Bandit, Gitleaks und Trivy bestanden;
bestehende PostgreSQL-Ausnahmen unverändert. Geänderte und neue Dateien zusätzlich
separat mit Gitleaks geprüft. Aktiver ZAP-Lauf bestanden: 1300 SQL-Injection-Prüfanfragen,
DOM-XSS vollständig abgeschlossen, keine blockierenden Befunde und keine
fehlgeschlagenen Abdeckungsprüfungen.

Geprüft wird der Arbeitsstand auf Basis von Commit
`a29b69d692464b1ae58b59756d263aeb33962e3e` einschliesslich uncommitteter K-T02-Änderungen.
App-Image-ID: `sha256:537932c23bd7faec8a86fe0bab6f85e6846255caf2ebee5f2e6dcc6edc6fc0b6`.
Archive: `artifacts/kt02/`; Scanberichte: `reports/security/kt02/`;
Screenshots: `reports/kt02/`; geschützte Deployment-Protokolle: `.qa/kt02/`.
Keine Produktionsauslieferung durchgeführt. Der bestehende ZAP-Plan ersetzt
keine fachlichen Eigentumsprüfungen der authentifizierten Suche.
