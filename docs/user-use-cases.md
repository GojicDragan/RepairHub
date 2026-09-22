# Benutzeranwendungsfälle und Bibliotheksadapter

Umsetzung der Benutzerentscheidung vom 21. September 2026, Bezug M01 und N10.
Diese Struktur ersetzt die bisher dokumentierte Ausnahme, bei der Flask-Security
mit seinem eigenen Blueprint direkt die Identitätspersistenz verwaltete.

## Tatsächlicher Aufrufweg

```text
HTTP → app.web.routes.users → injizierter Domain-Handler
     → Slice-Port → FlaskSecurityUsers → Flask-Security / IdentityDatastore
```

`app.domains.users` enthält acht vertikale Slices: `register_user`, `login_user`,
`logout_user`, `confirm_email`, `resend_confirmation`, `request_password_reset`,
`check_reset_link` und `reset_password`. Jeder besitzt `dto.py`, `ports.py` und
`handler.py`. Commands sind unveränderlich; Passwort-/Tokenfelder sind von der
Repräsentation ausgeschlossen. `UserResult` transportiert stabile Ergebniscodes
und unveränderliche Fehlermeldungen, niemals Requests, Formulare, Responses oder
ORM-Objekte. Die technischen Ports werden per Konstruktor injiziert.

Die Handler sind bewusst dünn: Aktuell gibt es neben der delegierten
Identitätsverwaltung keine zusätzlichen RepairHub-spezifischen Registrierungs-
regeln. Sicherheitslogik wird nicht dupliziert, um eine umfangreichere Domain zu
simulieren. Eigene zukünftige Regeln gehören in den jeweils zuständigen Slice.

`app.bootstrap` erstellt Bibliothek, Datastore, konkreten Adapter und Handler und
übergibt die Handler an `create_user_blueprint`. Die Routen halten diese expliziten
Abhängigkeiten als Closure, ohne einen Service-Locator. Bibliotheks-Formularklassen
werden separat für die Darstellung übergeben; ihre Validierung im Adapter liest
nur Command-Daten, nicht implizit HTTP-Formulardaten. Die Webgrenze setzt CSRF durch.

## Bibliotheksgrenze

Flask-Security wird mit `register_blueprint=False` initialisiert. Der eigene
Blueprint heisst weiterhin `security`, damit bestehende Endpoint-Namen,
Templates und von der Bibliothek erzeugte E-Mail-Links kompatibel bleiben.
Es existiert genau eine Route pro bestehendem Benutzerendpoint. Es werden keine
Funktionen aus `flask_security.views` aufgerufen; die Architekturprüfung verbietet
diese Imports ausdrücklich.

Der Adapter verwendet die Funktionen der installierten Flask-Security-Version:
`registerable.register_user/register_existing`,
`confirmable.confirm_email_token_status/confirm_user/send_confirmation_instructions`,
`recoverable.reset_password_token_status/update_password/send_reset_password_instructions`
und `login_user/logout_user`. Grundlage: Bibliotheksquellen in der gesperrten
Version 5.8.2. Es wurde kein View-Code übernommen. Hashing, Token-Signatur,
Passwortregeln, Eindeutigkeitsprüfung, Bestätigungspflicht und Sitzungsrotation
bleiben Bibliotheksfunktionen. Ihre Formulare benötigen weiterhin einen Flask-
Kontext innerhalb des technischen Adapters; das betrifft nicht die Domain.

Bibliothekshelfer lösen teilweise Signale und Flash-Nachrichten aus. Diese
Seiteneffekte bleiben innerhalb der Adapterintegration, während Redirects,
Statuscodes, HTML und Session-Cookies zur HTTP-/Framework-Schicht gehören.
Datenänderungen werden explizit im Adapter committed; Ausnahmen führen zu einem
Rollback. Gleichzeitige Eindeutigkeitskonflikte werden wie bisher als Konflikt
behandelt. SMTP und PostgreSQL bilden keine gemeinsame atomare Transaktion:
Mailfehler verhindern den Commit, eine erfolgreiche Zustellung vor einem späteren
Commitfehler kann aber nicht zurückgenommen werden.

## Verhalten und Abgrenzung

Englische URLs, kombinierter Login, englische/deutsche Formulare und E-Mails,
Bestätigung sowie Passwort-Recovery bleiben erhalten. Login führt bewusst immer
zur Startseite; übermittelte `next`-URLs werden nicht übernommen. Die eigenen
Browserendpoints liefern HTML. Eine JSON-Authentifizierungs-API gehört weiterhin
zum separaten API-Task und wird nicht durch Bibliotheks-Nebenfunktionen angeboten.
Alle Identitätsseiten erhalten `Cache-Control: no-store` und
`Referrer-Policy: no-referrer`. Domain und Datenbankschema bleiben unabhängig.

## Prüfungen am 21. September 2026

- `pytest tests/unit tests/integration/app/test_user_routing.py -q`: 368 bestanden
  (359 Unit-Tests und neun Tests des tatsächlichen HTTP→Handler-Aufrufwegs).
- Isolierter PostgreSQL-Lauf `.qa/t04/run-integration.py`: 149 bestanden,
  einschliesslich Registrierung, Bestätigung, Passwort-Reset, CSRF,
  Eindeutigkeitskonflikten und SMTP-Fehlerpfaden. Migration und Schemaabgleich
  erfolgreich; keine neue Migration erforderlich.
- Alle acht Handler mit `python -S` ohne site-packages importiert.
- `scripts/ci/images.py build --directory artifacts/user-use-cases-final`: bestanden.
- `pytest tests/e2e --image-artifacts artifacts/user-use-cases-final`: 12 bestanden;
  vollständige Abläufe in Englisch und Deutsch, jeweils mit/ohne JavaScript,
  isoliertes SMTP, Token-Logredaktion und Datenbank-Neuerstellung.
- `scripts/ci/security.py --artifacts artifacts/user-use-cases-final --reports
  reports/security/user-use-cases-final --binaries /tmp/repairhub-t02-scanners`:
  Dependency-, Bandit-, Gitleaks- und Container-Gates bestanden. Bestehende
  PostgreSQL-Ausnahme unverändert.
- Ruff, Formatierung, Architekturprüfung und `git diff --check` bestanden.

Lokale Entwicklungsanwendung neu geladen. Keine Produktionsbereitstellung,
keine neue Ansible-Abnahme; Bibliotheks-DeprecationWarnings bleiben sichtbar.

### Historischer ZAP-Befund vor der Scannerkorrektur

Nachtrag: Die nachfolgend dokumentierten Formular-/Browserprobleme wurden
anschliessend reproduziert und in der Scannersteuerung behoben. Ursachen,
unveränderte Befundgrenzen und aktive Nachprüfungen: [DAST-Nachweis](dast.md).
Die folgenden Absätze beschreiben den früheren Prüfstand.

Zwei aktive Läufe des ersten Refactoring-Images (`artifacts/user-use-cases`)
blockierten mit Regel [40018 – SQL Injection](https://www.zaproxy.org/docs/alerts/40018/)
bei mittlerer Confidence. Der Wiederholungslauf meldete acht Instanzen:
`POST /confirm` (`email`, `submit`, `query`), `POST /login` (`identity`, `password`)
und `POST /reset` (`email`, `submit`, `query`). Der Scanner begründet diese mit
Unterschieden zwischen booleschen Testeingaben, nicht mit ausgegebenen SQL-Fehlern.

Die acht Fälle wurden gegen PostgreSQL auf dem endgültigen Stand nachgespielt
(`tests/integration/users/test_injection_regression.py`). Wahr-/Falsch-/OR-
Varianten erzeugten jeweils dieselbe sichtbare Antwort nach Entfernung des
reflektierten Eingabewerts und des zeitabhängigen CSRF-Tokens. Keine Anmeldung,
keine zusätzlichen E-Mails, keine Veränderung der Kontenzahl, keine Angriffszeichenfolge
im SQL-Statement. CSRF blieb eingeschaltet. Damit ist eine SQL-Injection nicht
bestätigt; ein vollständiger grüner ZAP-Lauf ist dadurch ausdrücklich nicht belegt.
Unterschiede bei CSRF-/Sitzungszuständen sind eine zu untersuchende Hypothese.

Zusätzlich übersprang ZAP DOM-XSS, weil Firefox nicht gestartet werden konnte
(`Failed to read marionette port`). Diese Abdeckung fehlt trotz erfolgreicher
Playwright-Tests. Die Scan-Konfiguration, Befundgrenzen und Ausnahmen wurden nicht
geändert. Die vollständige Sicherheitsabnahme bleibt offen; keine Freigabe oder
Produktionseinführung behaupten. Nach der letzten Änderung (explizites Ignorieren
von `next` bei der Bibliotheksvalidierung) wurden Build, E2E und die übrigen
Security-Gates mit `artifacts/user-use-cases-final` erneut erfolgreich geprüft.

Sanitisierte Berichte: `reports/security/user-use-cases/zap.json` und
`reports/security/user-use-cases-recheck/zap.json`. Lokale Detaildaten bleiben
unter `.qa/` mit restriktiven Dateirechten und sind kein veröffentlichtes Artefakt.
