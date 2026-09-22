# T05 – Anmeldung und Browsersitzungen

Stand: 21. September 2026. Bezug: M01, F02, N01, N06–N07.

Die Anmeldung und Abmeldung waren bereits als vertikale Benutzer-Slices umgesetzt.
T05 ergänzt ihre gezielte Sitzungsabnahme. Es wurde keine zweite Authentifizierung,
kein neues Datenmodell und kein vorgezogener Geräte-Endpunkt eingeführt.

## Aufrufweg und Identitätsgrenze

`app.web.routes.users` übersetzt HTTP-Eingaben in Commands für `LoginUser` und
`LogoutUser`. Die Handler erhalten ihre Gateway-Implementierung in `app.bootstrap`.
`FlaskSecurityUsers` nutzt die Passwortprüfung und Sitzungsverwaltung von
Flask-Security; dessen eigene HTTP-Views bleiben deaktiviert. Fachlicher Code
bleibt frei von Flask, SQLAlchemy und Sitzungsobjekten.

Die Anmeldung nimmt E-Mail-Adresse oder Benutzername in einem gemeinsamen Feld an.
E-Mail-Bestätigung und ein aktives Konto sind Voraussetzung. Erfolgreiche Anmeldung
führt auf die Startseite; übergebene externe Weiterleitungsziele werden ignoriert.
`FlaskSecurityIdentity.current()` liefert ausschliesslich den unveränderlichen
`UserIdentity(id, username)` für angemeldete, bestätigte Benutzer. Die Bibliothek
lädt deaktivierte Konten nicht als Sitzungsidentität. Dieser Port ist die geprüfte
Grenze für spätere Fachfunktionen; eine Geräteberechtigung wird damit noch nicht
behauptet.

## Abnahmekriterien und Nachweise

| Prüfung | Nachweis |
| --- | --- |
| Anmeldung mit E-Mail oder Benutzername, auch bei anderer Gross-/Kleinschreibung | `tests/integration/users/test_registration.py` |
| Gleiche Passwörter ergeben unterschiedliche gültige Argon2-Hashes | `test_password_hashes_are_salted` |
| Falsche Zugangsdaten, unbekannte und unbestätigte Konten erhalten keine Sitzung | Registrierungs- und Sitzungstests |
| Deaktivierte Konten können sich nicht anmelden | `test_inactive_account_cannot_log_in` |
| POST-Abmeldung entfernt Identität und vorheriges CSRF-Token | `test_login_exposes_only_verified_identity_and_logout_removes_it` |
| Fehlende, manipulierte und fremde CSRF-Tokens ändern den Anmeldestatus nicht | `test_csrf_failure_cannot_change_authentication` für Login und Logout |
| Manipulierte Sitzungs-/Remember-Cookies ergeben keine Identität | `test_tampered_cookie_never_provides_identity` |
| Remember-Cookie stellt die Identität wieder her und wird beim Logout gelöscht | `test_remember_cookie_restores_identity_and_logout_clears_it` |
| Cookies tragen Secure, HttpOnly und SameSite=Lax; ohne Auswahl kein Remember-Cookie | `test_cookies_have_secure_attributes_and_contain_no_password` |
| Deaktivierung, entzogene Bestätigung oder rotierte Sitzungskennung sperren die bisherige Identität | `test_existing_session_cannot_bypass_current_identity_state` |
| Fehler geben Passwörter nicht erneut aus; Antworten sind nicht cachebar und senden keinen Referer | `test_login_errors_never_echo_password_or_create_session` |
| Passwort-Reset entwertet eine bestehende Sitzung | `tests/integration/users/test_password_reset.py` |
| HTTP-Routen rufen die injizierten Handler auf; Domain-Imports bleiben frameworkfrei | Routing-, Domain- und Architekturtests |

Die 18 neuen PostgreSQL-Integrationstests stehen in
`tests/integration/users/test_sessions.py`. Sie prüfen echte Cookies, Formulare,
Bibliotheksabläufe und den verdrahteten Identitätsport. CSRF bleibt eingeschaltet.
Es wird ausschliesslich ein kurzlebiges isoliertes Datenbankschema verwendet.

Der bestehende Browserablauf prüft Registrierung, Bestätigung, Anmeldung,
Abmeldung und Recovery auf Deutsch/Englisch mit und ohne JavaScript. Seine
Recovery-Negativfälle unterschieden bisher nicht zwischen diesen Betriebsarten:
Ohne JavaScript muss der Server die Eingabe ablehnen; ein deaktivierter Button
und dynamische Hinweise dürfen dort nicht erwartet werden. Der Test prüft nun
beide vorgesehenen Wege ausdrücklich, statt eine JS-Funktion ohne JS zu verlangen.

## Ausgeführte Prüfungen

- `.venv/bin/pytest tests/unit -q`: 359 bestanden.
- `node --test tests/unit/frontend/*.test.mjs`: 7 bestanden.
- PostgreSQL-Lauf über `.qa/t04/run-integration.py`: 167 Integrationstests bestanden;
  zusätzlich Migration einer leeren Datenbank und Modelldrift geprüft.
- `.venv/bin/python scripts/check_architecture.py`: bestanden.
- `.venv/bin/ruff check .` und `.venv/bin/ruff format --check .`: bestanden.
- `scripts/ci/images.py build --directory artifacts/t05 --commit <HEAD>`: bestanden.

Der lokale Build verwendet den Basiscommit
`b19de2c6ddfa8406e923f90956b393121a138e77`. T05 ändert Tests und Dokumentation,
keinen Anwendungscode. Das Commit-Label ist kein Nachweis eines veröffentlichten
T05-Commits; Image-Identitäten stehen im lokalen `artifacts/t05/manifest.json`.
App-Image-ID: `sha256:f779ada451f9d7fa5d167de8061c020b51e626a994b03c975d513f2c89403c2c`.

- `.venv/bin/pytest tests/e2e --image-artifacts artifacts/t05
  --junitxml=reports/t05/e2e.xml -q`: 28 bestanden, einschliesslich vier
  vollständiger Registrierungs-/Login-/Logout-/Recovery-Abläufe über HTTPS.
- `scripts/ci/security.py --artifacts artifacts/t05 --reports reports/security/t05
  --binaries /tmp/repairhub-t02-scanners`: Dependency-, Bandit-, Gitleaks- und
  alle drei Containerprüfungen bestanden. Die bestehende ausdrücklich genehmigte
  PostgreSQL-Ausnahme bleibt unverändert; es wurde keine Ausnahme ergänzt.
- `scripts/ci/smoke_images.py --directory artifacts/t05 --commit <HEAD>`: bestanden;
  PostgreSQL, Gunicorn und HTTPS mit Zertifikatsprüfung bereit.
- `scripts/ci/dast.py --artifacts artifacts/t05 --reports reports/security/t05
  --commit <HEAD>`: **blockiert**, vier Instanzen der Regel 40018 (Risiko 3,
  Konfidenz 2). Der Scannerprozess endete mit 0, die eigene Befundprüfung
  verweigerte korrekt die Freigabe und lieferte Exit 1. Bericht:
  `reports/security/t05/zap.json`. Zusätzlich zeigte das Scannerprotokoll erneut
  `Failed to read marionette port`; DOM-XSS ist damit nicht vollständig geprüft.
  Keine Scannerregel, Befundgrenze oder Ausnahme wurde geändert.

Keine Ansible- oder Produktionsauslieferung in T05: Die Änderungen betreffen
Tests und Dokumentation, nicht den Laufzeitstand oder das Schema. Der vollständige
GitHub-Actions-Lauf mit diesen neuen Tests bleibt nach dem Commit auszuführen.

## Grenzen

Flask verwendet signierte Cookies. Logout entfernt die Sitzung und den
Remember-Cookie im betreffenden Browser. Eine zentrale Sperrliste für zuvor
kopierte, noch gültige Cookies gehört nicht zu dieser Implementierung; Logout
wird daher nicht als globale Entwertung gestohlener Cookiekopien ausgewiesen.
Passwort-Reset rotiert dagegen die von der Bibliothek verwendete Benutzerkennung.
Manipulierte Cookies und unverändert kopierte gültige Cookies sind unterschiedliche
Fälle.

Die erneut aufgetretenen ZAP-Befunde und der ausgefallene DOM-XSS-Scan bleiben in `docs/user-use-cases.md` dokumentiert. Eine funktionale
Sitzungsabnahme allein hebt diese Sicherheitsgrenzen nicht auf. Es wird keine
Produktionsbereitstellung behauptet. T06 folgt separat mit Gerätefunktionen und
einer objektbezogenen Eigentumsprüfung.

## Ergebnis

Die funktionale lokale T05-Abnahme ist erfüllt. Eine vollständige Sicherheits-
oder Releasefreigabe ist wegen der beschriebenen ZAP-Befunde nicht gegeben.
Der ursprüngliche SQL-Injection-Verdacht wurde durch die vorhandenen acht
PostgreSQL-Regressionsprüfungen auch in diesem Integrationslauf nicht bestätigt;
das ersetzt keine Klärung der Scannerbefunde. Alle kurzlebigen Container der
Integrations-, Browser-, Smoke- und DAST-Prüfungen wurden entfernt.


### Nachtrag: ZAP-Korrektur

Die oben dokumentierten Formularbefunde und der Firefox-Startfehler wurden
anschliessend gezielt untersucht. Der korrigierte aktive Scanner bestand den
Nachlauf; Herkunft der Fehlmeldungen, unveränderte Befundgrenzen und Grenzen
der Abdeckung sind in [docs/dast.md](dast.md) dokumentiert. Dies ersetzt keinen
authentifizierten Geräte-/API-Scan und keine Produktionsabnahme.
