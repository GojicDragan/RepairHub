# Passwort zurücksetzen

Benutzerentscheidung vom 21. September 2026: Passwort-Recovery wird zusätzlich zum
ursprünglichen Umfang umgesetzt (Benutzerverwaltung, Bezug M01/N10). Die bisherige
Aussage «ausserhalb des Umfangs» ist damit überholt.

## Ablauf

1. Auf der Anmeldeseite «Forgot password?» / «Passwort vergessen?» wählen.
2. E-Mail-Adresse auf `/reset` eingeben. Die Antwort verrät nicht, ob ein Konto
   existiert. Nur ein bestätigtes, berechtigtes Konto erhält den Reset-Link;
   unbestätigte Konten verwenden zuerst die bestehende E-Mail-Bestätigung.
3. Über `/reset/<token>` ein neues Passwort mit Wiederholung eingeben. Bestehende
   Passwortregeln bleiben gültig: 8–128 Zeichen.
4. Danach erneut anmelden. Die Bibliothek entwertet bestehende Sitzungen und
   verbrauchte Reset-Links nach erfolgreicher Passwortänderung. Eine separate
   Nachricht informiert über die Änderung.

Flask-Security verwaltet Signatur, Gültigkeit (eine Stunde), Passwort-Hashing,
Validierung und Sitzungswechsel. Kein eigener kryptografischer Ablauf, keine
Migration, keine neuen Python-Abhängigkeiten. Technische Einbindung bleibt im
Identitätsadapter; die Fachdomänen bleiben frameworkfrei.

`SECURITY_RETURN_GENERIC_RESPONSES` schützt auch andere anonyme Identitätsabläufe:
Doppelte Registrierungen liefern dieselbe Weiterleitung wie erfolgreiche und
senden einen Hinweis per E-Mail, ohne ein weiteres Konto anzulegen. Generische
Loginfehler werden am Formular angezeigt; die gemeinsame Identitätseingabe bleibt
erhalten. Alle zusätzlichen E-Mails sind als HTML und Plain-Text gestaltet und
übersetzt. Die Sprache richtet sich nach dem Browser der auslösenden Anfrage.

## Betrieb

Keine zusätzlichen Environment-Variablen oder Secrets erforderlich. Bestehende
SMTP-Einstellungen und `PUBLIC_URL` werden wiederverwendet. Lokal fängt Mailpit
die Nachrichten ab. Produktion verwendet den konfigurierten externen SMTP-Dienst.
Nginx protokolliert Reset-Pfade als `/reset/[redacted]`; bestehende Zielhosts
benötigen dafür die Infrastruktur-Aktualisierung gemäss `ci-cd.md`. Die Seiten
werden mit `noindex, nofollow` ausgeliefert und veröffentlichen keine Token-URLs
in Canonical-/Social-Metadaten.

## Nachweis vom 21. September 2026

- `pytest tests/unit -q`: 333 bestanden.
- Isolierter PostgreSQL-Lauf über `.qa/t04/run-integration.py`: 129 bestanden;
  leere Migration und Schemaabgleich erfolgreich. Nach Ergänzung des `/reset`-
  Metadatenfalls zusätzlich `pytest tests/integration/app/test_metadata.py -q`:
  9 bestanden.
- `scripts/ci/images.py build --directory artifacts/password-reset`: erfolgreich.
- `pytest tests/e2e --image-artifacts artifacts/password-reset`: 12 bestanden,
  einschliesslich Registrierung, Bestätigung, Reset über tatsächlichen isolierten
  SMTP-Empfänger, Anmeldung mit neuem Passwort, Token-Logredaktion und
  Datenbank-Neuerstellung. Englisch/Deutsch jeweils mit und ohne JavaScript.
- `scripts/ci/security.py --artifacts artifacts/password-reset --reports
  reports/security/password-reset --binaries /tmp/repairhub-t02-scanners`:
  Dependency-, Bandit-, Gitleaks- und alle drei Container-Scans bestanden;
  bestehende explizite PostgreSQL-Ausnahme unverändert.
- Ruff, Format- und Architekturprüfung sowie `git diff --check` bestanden.

Tests prüfen abgelaufene/manipulierte und wiederverwendete Tokens, CSRF,
Passwortregeln, Ablehnung des alten Passworts und Entwertung einer bestehenden
Sitzung. Bibliotheks-DeprecationWarnings bleiben sichtbar. Lokales Nginx wurde
validiert und neu geladen. Keine Produktion bereitgestellt; ZAP und Ansible
wurden für diese Änderung nicht erneut ausgeführt.
