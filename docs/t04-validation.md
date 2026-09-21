# T04 – Registrierung und E-Mail-Verifikation mit Flask-Security

Stand: 21. September 2026. Bezug: **M01, F01, N01, N03, N06–N07, N10**.
Die Bibliotheksintegration liefert bereits Login/Logout für den Bestätigungsablauf
(F02); die weitergehende T05-Abnahme wird dadurch nicht pauschal als erledigt markiert.

## Umsetzung und Entscheidungen

Auf ausdrücklichen Benutzerwunsch wurde die begonnene eigene Registrierung durch
**Flask-Security 5.8.2** ersetzt. Registrierung, Bestätigungstokens, Passwortprüfung
und Sitzungsabläufe stammen aus der Bibliothek. Keine eigene Kryptografie und kein
parallel beibehaltener Registrierungs-Handler. Flask-Mailman 1.1.1 stellt SMTP mit
Zertifikatsprüfung bereit, Flask-Babel 4.0.0 die i18n-Anbindung mit Englisch als Standardsprache.

- `/register`: Benutzername, E-Mail, Passwort und Passwortbestätigung.
- `/confirm`: erneuter Versand; `/confirm/<token>` bestätigt die Adresse.
- `/login`: Anmeldung erst nach Bestätigung; `/logout` ausschliesslich per
  POST mit CSRF. Automatische Anmeldung nach Bestätigung bleibt ausgeschaltet.
- Passwörter **8–128 Zeichen**, Mindestlänge vom Benutzer gewählt. Keine zusätzlichen
  Kompositionsregeln; Unicode/Leerzeichen erlaubt. Argon2id übernimmt die Bibliothek
  mit individuellem Salt, ohne zusätzlich an SECRET_KEY gekoppelten Passwort-Pepper.
- Benutzername **1–80 Buchstaben/Ziffern**, NFC-Normalisierung gemäss konfiguriertem
  Bibliotheksverfahren. E-Mail-Syntaxprüfung ohne DNS-Zustellbarkeitstest.
  Benutzername und E-Mail sind **case-insensitive eindeutig**, auch unter Konkurrenz.
  Die E-Mail-Eindeutigkeit wurde ausdrücklich vom Benutzer genehmigt.
- Bestätigungslinks sind **24 Stunden** gültig. Ungültige/abgelaufene Links schalten
  Konten nicht frei. Die E-Mail-Verifikation wurde nachträglich als Muss ergänzt.
- Bootstrap-Vorlagen verwenden weiterhin die Bibliotheksformulare; keine doppelte
  fachliche Formularvalidierung. Passwörter werden nicht wieder ins HTML eingesetzt.
  Der Ablauf funktioniert ohne JavaScript; bestehende Humble Objects schliessen Meldungen.

Quellen: [Flask-Security-Funktionen](https://flask-security.readthedocs.io/en/stable/features.html),
[Konfiguration](https://flask-security.readthedocs.io/en/stable/configuration.html),
[Modellvertrag](https://flask-security.readthedocs.io/en/stable/models.html).

## Architektur und Persistenz

Die generische Identitätsverwaltung liegt als technische Integration in
`app.adapters.users` und `app.data.users`. Der Fachkern erhält ausschliesslich
`UserIdentity` über den `IdentityProvider`-Port. Eigene Vorlagen verwenden den DTO,
keine nachladenden ORM-Objekte. Die Composition Root verbindet die Adapter.
Details: [Domain-Architektur](domain-architecture.md).

Erst aus dem Bibliotheksbedarf entstand Migration `0001_register_user` mit `users`,
`roles`, `roles_users`. Die beiden Rollentabellen erfüllen den Bibliotheksvertrag;
es werden keine Rollen vergeben und keine Administratorfunktionen angeboten.
Geräte-, Reparatur-, Schritt- und Teiletabellen sind weiterhin nicht vorgezogen.
Die erste Migration ist additiv. Datenlöschendes Downgrade ist gesperrt.

Funktionale Unique-Indizes auf `lower(username)` und `lower(email)` schützen vor
konkurrierenden Registrierungen. Der Datastore übersetzt nur diese Konflikte in
409 und rollt die Transaktion zurück. Bei SMTP-Fehlern erfolgt ebenfalls Rollback
und eine generische 503-Antwort, ohne SMTP-Zugangsdaten preiszugeben. SMTP-Transfer
und DB-Commit sind keine verteilte atomare Transaktion: Eine bereits übergebene Mail
kann bei anschliessendem Commit-Ausfall nicht zurückgerufen werden. Ein solcher
Link darf ohne gespeichertes Konto nichts bestätigen; der Benutzer kann erneut
registrieren beziehungsweise einen neuen Link anfordern.

Nginx maskiert Tokens unter `/confirm/` im Zugriffslog. Der Host-Header erhält
seinen Port, damit Flask-WTF Herkunftsprüfungen auch bei lokalen HTTPS-Ports stimmen.

## CI und Betrieb

Migrationen sind in `deploy/capabilities.json` aktiviert und im App-Image enthalten.
CI prüft Migration und Modelldrift; Browser-/DAST-Fixtures migrieren einmalig vor
HTTP-Zugriffen. Ansible nutzt weiterhin denselben kontrollierten Migrations-/Backup-
Ablauf. Das Schema wird nicht beim Start einzelner Gunicorn-Worker verändert.

SMTP wird über GitHub-Environment-Variablen und Secrets bereitgestellt, siehe
[Einrichtungsliste](ci-cd.md). Produktion verlangt verschlüsseltes SMTP. `PUBLIC_URL`
bindet externe Links und erlaubte Hostnamen an die Produktionsadresse.

Lokale Tests senden nur an einen wegwerfbaren SMTP-Empfänger: Integration prüft
SMTP auf Loopback, E2E/DAST verwenden einen STARTTLS-Container ohne Host-Port mit
eigener geprüfter Test-CA. Dieser verwendet denselben Python-Interpreter und nur
read-only eingebundene Testabhängigkeiten; er wird weder veröffentlicht noch in
Produktions-Compose aufgenommen. Es gibt keine Zustellung an externe Postfächer.
Die DB-Fixture besitzt ein eigenes temporäres Volume, das Neustarts/Neuerstellung
innerhalb des Tests überlebt und anschliessend gezielt entfernt wird.

## Prüfungen

Lokal am 21. September 2026 ausgeführt:

| Prüfung | Ergebnis |
| --- | --- |
| `pytest tests/unit -q` | 331 bestanden |
| `node --test tests/unit/frontend/notification-presenter.test.mjs` | 1 bestanden |
| Integration über `.qa/t04/run-integration.py` mit isoliertem PostgreSQL | 85 bestanden |
| `scripts/ci/check_capabilities.py` | Leere Migration und Modelldrift bestanden |
| Browserprüfung des finalen Images | 10 bestanden; STARTTLS, Bestätigung, Login/Logout mit und ohne JS, DB-Neuerstellung |
| Ruff, Architekturprüfung und Actionlint | Bestanden |
| Ansible-Lint | Keine Fehler oder Warnungen |
| Dependency-, Bandit-, Gitleaks- und Trivy-Scans | Keine blockierenden Befunde |
| Ergänzender Gitleaks-Dateiscan von `app/` | Keine Geheimnisse gefunden |
| Aktiver ZAP-Scan | Wiederholung gegen dasselbe Image bestanden, nur informative Meldungen; vorheriger Verdacht siehe Einschränkung unten |

Berichte liegen lokal unter `reports/t04/` (nicht eingecheckte QA-Artefakte).
Fünf Deprecation-Warnungen stammen aus Flask-Securitys Bestätigungstoken-Auswertung;
die betreffenden positiven und negativen Tests bestehen.

Der erste Dependency-Scan meldete Befunde für Bleach 6.3.0. Aktualisierung auf
6.4.0 beseitigte die Befunde im anschliessenden pip-audit-Lauf; keine neue Ausnahme
wurde eingeführt. Die bestehende ausdrücklich genehmigte PostgreSQL-gosu-Ausnahme
bleibt unverändert.

## Offene externe Abnahme

Kein Commit, Push oder Produktionsdeployment durch diese Umsetzung. SMTP-Anbieter,
Absenderfreigabe und Zugangsdaten sind noch vom Betreiber einzurichten. GitHub-
Pipeline und Release sowie ein tatsächlicher Bestätigungsempfang in einem externen
Postfach stehen aus. Lokale SMTP-Annahme belegt keine externe Zustellbarkeit.
Die frühere erfolgreiche T02-Produktion bestätigt nicht den neuen T04-Stand.

## Image-Zuordnung

Die lokalen Prüfungen verwenden den noch nicht eingecheckten Arbeitsbaum.
Der verwendete Commit-Bezeichner `c0d02078a4dabe7be9d41618c011ed1324538421` ist der
bisherige HEAD und kein veröffentlichter T04-Commit.

App-Archiv SHA-256: `a066eca7f9e4960bcc08226867c5e61b255b8eef16487edabb24693b2c6e6d5f`.

App-Konfigurationsdigest: `sha256:62bc3c4e24b9ce201412f3c3fba5c60116f519122582198d2e9661b7d8f79633`.

### Deployment und Backup (lokal)

Isolierter SSH-/Docker-in-Docker-Testhost, `deploy/ansible/deploy.yml` mit
`tests/deployment/inventory.yml` und geschützten Fixture-Eingaben:

- Erstlauf einschliesslich Backup und Migration: `ok=77 changed=32 failed=0`.
- Identischer Wiederholungslauf: `ok=46 changed=0 failed=0`; Container-IDs unverändert.
- Tatsächliches Ansible-Backup mit GnuPG verschlüsselt und bytegleich entschlüsselt.
- Fixture enthält keine Produktionsdaten; Testhost und temporäre Zugangsdaten
  nach der Prüfung entfernt. Kein Produktionshost angesprochen.

Die Prüfung deckte fehlende Migrations-/Backup-Eingaben auf. Der Controller liefert
nun die zur additiven T04-Migration passende Kompatibilitätsentscheidung und einen
geschützten Backup-Pfad. GitHub bewahrt ausschliesslich verschlüsselte Backups auf;
neues Environment-Secret `BACKUP_PASSPHRASE`, Einrichtung und Grenzen in `ci-cd.md`.
Die Source-Änderung betrifft den Controller; das geprüfte App-Image blieb unverändert.

### Einschränkung des aktiven Scans

Der erste finale ZAP-Lauf meldete vier Instanzen der Regel 40018 (Risiko hoch,
Konfidenz mittel) und blockierte korrekt. Der vollständige Wiederholungslauf mit
lokal geschütztem Diagnosebericht gegen dasselbe unveränderte Image endete mit
Exit 0 ohne blockierende Befunde. Regeln, Befundgrenzen und Ausnahmen wurden nicht
verändert. Der ursprüngliche Verdacht ist nicht reproduziert und seine Ursache
nicht abschliessend erklärt; dies ist kein Nachweis eines behobenen Fehlers und
keine genehmigte Scan-Ausnahme. Erneut auftretende Befunde müssen wieder blockieren
und anhand ihrer konkreten Anfragen untersucht werden. Die eingesetzten
Flask-Security/SQLAlchemy-Abfragen binden Suchwerte als Parameter.

### Ergänzung: Mailfänger für Development

Benutzerentscheidung: Produktion nutzt externes SMTP, Development fängt Nachrichten
lokal ab. `compose.development.yaml` ergänzt dafür Mailpit v1.31.2 mit geprüftem
Registry-Digest. Die App nutzt `mailpit:1025` ohne TLS/Authentifizierung im internen
Entwicklungsnetz; Produktionswerte aus `runtime.env` werden ausdrücklich überschrieben.
Bestätigungslinks zeigen auf den konfigurierten lokalen HTTP-Port. Mailpit hat keinen
konfigurierten Relay/Forwarder und keinen öffentlichen SMTP-Port; UI nur auf Loopback, standardmässig
8025. Nachrichten liegen temporär im Container. Produktions-Compose und Ansible
bekommen keinen zusätzlichen Dienst. Einrichtung: README, Abschnitt E-Mails in Development.

Geprüft am 21. September 2026 mit `.qa/t04/check_mailpit.py`: beide Compose-
Konfigurationen aufgelöst; Development überschreibt absichtlich gesetzte externe
SMTP-Werte, Produktion behält sie und enthält keinen Mailpit-Dienst. Wegwerfbares
Compose-Projekt gestartet, Healthcheck bestanden, SMTP-Testnachricht aus einem
App-Image im gleichen Docker-Netz zugestellt und über die Mailpit-HTTP-API gelesen.
UI ausschliesslich auf 127.0.0.1, keine SMTP-Portfreigabe. Danach Testprojekt entfernt.
Vorhandene Entwicklungscontainer wurden nicht verändert. `git diff --check` bestanden.

### Englische Anwendung und i18n (anschliessende Benutzerentscheidung)

Anwendungstexte, Bibliothekslabels, E-Mails und Endpoints auf Englisch umgestellt.
Eigene Texte verwenden Flask-Babel/gettext; Sprachkataloge werden über `babel.cfg`
extrahiert. Standardsprache Englisch, keine automatische Browser-Sprachauswahl.
Details und Pflegebefehle: [i18n](i18n.md). Nginx-Tokenmaskierung auf `/confirm/`
umgestellt. Alte deutsche URLs liefern 404.

Nach dieser Änderung: 331 Unit-Tests und 88 PostgreSQL-Integrationstests bestanden,
einschliesslich eines tatsächlich kompilierten temporären Übersetzungskatalogs.
Image-Build und Bereitschaftstest, Ruff, Architekturprüfung und Dependency-/Bandit-/
Gitleaks-/Trivy-Scans bestanden. Keine neuen Abhängigkeiten. Der aktive ZAP-Scan und
der Ansible-Lauf oben beziehen sich auf den Stand vor dieser Sprachumstellung;
sie wurden für die Sprachumstellung nicht erneut ausgeführt.

Das anschliessend gebaute Image enthält den nicht eingecheckten englischen Stand.
App-Archiv SHA-256: `d1544c3f5211574edb188e8da95ea71ca49352296378cc1bccd3dc1853710a70`.
App-Konfigurationsdigest: `sha256:e67d34f7fe2b20f9b806d958f1e84e5a5eade106069b6d6ba2318a80d01cab7c`.

Auch die 10 Browserprüfungen gegen dieses englische Image bestanden: Registrierung,
englische Mail mit `/confirm/`-Link, Bestätigung, Login/Logout mit und ohne JavaScript,
Tokenmaskierung, Darstellung und Datenpersistenz. Bericht: `reports/t04/english-e2e.xml`.

### Lokaler Fehler nach dem Start behoben

Die lokale Registrierung lieferte einen `ProgrammingError`, weil in der vorhandenen
Development-Datenbank noch keinerlei Tabellen existierten. Am 21. September 2026
wurde dort `flask --app app db upgrade` ausgeführt (`0001_register_user`). Die
Ersteinrichtungsanleitung führt die Migration jetzt vor dem Start der Oberfläche aus.
Keine bestehenden Tabellen/Daten gelöscht, kein Testkonto angelegt.

Ein zusätzlicher Fehler trat bei nicht erlaubtem Hostnamen auf: Flask hatte noch
keinen URL-Adapter, die Fehlerseite rief jedoch `url_for` auf. Solche Anfragen erhalten
jetzt eine generische 400-Antwort ohne Navigation oder Host-Wiedergabe. Development
mit lokaler PUBLIC_URL akzeptiert `localhost` und `127.0.0.1`; Produktion bleibt
auf den konfigurierten Host beschränkt. 37 gezielte Konfigurations-/Fehlertests
bestanden. Registrierung auf beiden lokalen Hostnamen sowie datenbankgestützte
Validierung mit absichtlich zu kurzem Passwort erfolgreich geprüft (kein Insert,
keine Mail). Ruff/Format und `git diff --check` bestanden.

## Erweiterung: Passwort-Recovery, 21. September 2026

Auf ausdrücklichen Benutzerauftrag ist Passwort-Reset nun Teil des umgesetzten
Umfangs (M01, N10). Flask-Security-Recovery mit englischen Endpoints,
Bootstrap-Formularen, deutschen Übersetzungen und gestalteten HTML-/Textmails.
Einmalig nutzbare Reset-Links mit einer Stunde Gültigkeit, Login nach Änderung,
Sitzungsentwertung und redaktierte Nginx-Logs. Nachweis: 333 Unit-, 129 Integrations-
und 12 E2E-Tests bestanden; Build und bestehende statische/Dependency-/Secret-/
Container-Security-Gates bestanden. Ausführliche Grenzen, Betriebsfolgen und
Befehle: [Passwort-Recovery](password-reset.md).

## Benutzeranwendungsfälle als tatsächlicher Einstieg, 21. September 2026

M01/N10: Die direkte Flask-Security-Blueprint-Integration wurde auf Benutzerauftrag
ersetzt. Acht frameworkfreie Slices delegieren über injizierte Ports an den
Bibliotheksadapter. Eigene HTTP-Routen verwenden diese Handler; die Composition
Root verbindet alle Komponenten. Architekturregeln verbieten Bibliotheks-Views,
HTTP-Tests belegen den tatsächlichen Aufrufweg. 359 Unit-, 149 Integrations- und
12 E2E-Tests bestanden; Build und statische/Dependency-/Secret-/Container-Gates
bestanden. Details und Grenzen: [Benutzeranwendungsfälle](user-use-cases.md).

**Offen bei dieser Architekturänderung:** ZAP blockierte zweimal mit Regel 40018.
Acht gezielte PostgreSQL-Nachprüfungen bestätigten keine Injection; Scannerbefunde
bleiben dennoch offen. ZAP-DOM-XSS wurde wegen eines Firefox-Startfehlers nicht
geprüft. Keine Ausnahme und keine vollständige Sicherheitsfreigabe. Einzelheiten
und tatsächlich geprüfte Image-Stände stehen in `docs/user-use-cases.md`.
