# T10 – Benutzeroberfläche und Fehlerpfade

## Umfang und Architektur

Bestehende Oberfläche vervollständigt, ohne neue Fachfunktionen, Datenbankmigrationen
oder Abhängigkeiten. Bootstrap, Markenfarben, englische Endpoints und deutsche
gettext-Übersetzungen bleiben erhalten. Betroffen sind ausschliesslich die
Webpräsentation und ihre Tests; die Fachdomänen und API-Berechtigungen bleiben
unverändert. Der Presenter entscheidet über HTTP-401-Verhalten, der DOM-Adapter
übernimmt Darstellung und Fokus. Bestehende Domain-Handler validieren weiterhin
alle Werte und prüfen Eigentum.

## Behobene Lücken

- Überholtes «Coming next» auf der Startseite entfernt.
- Aktuellen Geräte-, Reparatur- oder API-Bereich in der Hauptnavigation markiert.
- Gerätefilter und Teilefenster beim Blättern durch Reparaturschritte erhalten.
- Fehlerhafte Zahlenfelder auch in HTML-Antworten für assistive Technik markiert.
- Bei AJAX-Validierungsfehlern das erste betroffene Reparaturfeld fokussiert.
- Bei abgelaufener Sitzung Anmeldehinweis und Link angeboten; Entwürfe bleiben stehen.
  Auch ein wegen Sitzungsverlust ungültiger CSRF-Wert liefert für AJAX nun 401.
  Angemeldete Anfragen mit ungültigem CSRF bleiben 400; keine Schreibfreigabe entfällt.

## Abnahmefälle

| Kriterium | Nachweis |
| --- | --- |
| Registrierung bis Kostenanzeige über sichtbare Bedienung | Erweiterter `test_registration.py`: reale Bestätigungsmail, Anmeldung, Gerät, Fall, Schritt, Status, Arbeit und Teile; CHF 205.00 |
| Deutsch/Englisch, mit/ohne JavaScript | Vier Varianten des vollständigen Ablaufs |
| Gültige Eingaben nach Fehlern erhalten | Ungültige Menge 0, Name und Preis bleiben erhalten, anschliessend erfolgreiche Korrektur |
| Netzwerkfehler und erneutes Speichern | Ein abgebrochener HTTP-Request, erhaltener Entwurf, erfolgreicher erneuter Versuch |
| Sitzung abgelaufen | Browsercookies entfernt, alter CSRF-Wert wird abgewiesen, Anmeldehinweis sichtbar |
| Keine privaten Inhalte nach Abmeldung | Direkter erneuter Aufruf des Reparaturdetails führt zur Anmeldung |
| Unbekannte URL mit Rückweg | Fehlerseite auf Englisch/Deutsch, Link zur Startseite |
| Keine technischen Details | Bestehende Integrationstests für 500, Logs, CSRF und Fehlerantworten |
| Navigation und Fensterkontext | HTML-Integration prüft Gerätefilter und Teilefenster in Vor-/Zurück-Links |
| Kleine und grosse Bildschirme | Browserprüfung bei 320, 768 und 1440 px; Screenshots unter `reports/t10/` |

## Prüfergebnisse

Architektur-Skript und 618 Unit-Tests (einschliesslich 97 Architekturtests) bestanden.
Alle 57 JavaScript-Tests bestanden. Ruff, Formatierung und Diff-Prüfung bestanden.
284 PostgreSQL-Integrationstests bestanden, einschliesslich Migration einer leeren
Datenbank und Schemaabgleich ohne weitere Upgrade-Operationen. Alle 51 Browserprüfungen
gegen das abschliessende Produktionsimage bestanden; Screenshots der deutschen
Tabletansicht und englischen Desktopansicht sowie der mobilen Darstellung visuell geprüft.

Produktionsimage unter `artifacts/t10-final` gebaut und über HTTPS/Nginx mit
PostgreSQL geprüft. pip-audit, Bandit, Gitleaks und Trivy bestanden; bestehende
PostgreSQL-Ausnahmen unverändert. Zusätzlich wurden die noch nicht committeten
geänderten Dateien separat mit Gitleaks geprüft. Aktiver ZAP 2.17.0 bestanden:
1'300 SQL-Injection-Prüfanfragen, DOM-XSS-Prüfung vollständig beendet, keine
blockierenden Befunde. Berichte: `reports/security/t10-final/`.

Isolierter Ansible-Testhost: Erstlauf erfolgreich (`changed=33`), Wiederholung
`changed=0`; Update auf das abschliessende Image erfolgreich (`changed=22`),
erneute Wiederholung `changed=0` mit unveränderten Container-IDs und Startzeiten.
HTTPS- und authentifizierte API-Prüfung bestanden. Geschützte lokale Protokolle
unter `.qa/t10/`; Testhost nach Abschluss entfernt.

Geprüfter Arbeitsstand auf Basis von Commit
`413b293263ecbee28638a88c7abd1a1d0c93b5fa`, einschliesslich der noch nicht
committeten T10-Änderungen. App-Image-ID:
`sha256:6eb6bbaadf358772c60c21eb5513d0f45fca2e7fdd89ab6ae5b8e4847a10d852`.
Ein vorläufiger Scan wurde vor Abschluss beendet, um die abschliessende
Sitzungsbehandlung im neu gebauten Image zu prüfen; nur der finale Scan zählt
für diese Abnahme.

Keine Produktionsauslieferung durchgeführt und keine GitHub-Secrets geändert.
Keine neuen Environment-Variablen erforderlich. Produktionsabnahme erfolgt mit
dem regulären Release und wird getrennt dokumentiert.
