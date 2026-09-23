# Betrieb, Backup und Wiederherstellung

## Geltungsbereich

RepairHub läuft als modularer Monolith mit `nginx`, `app` und PostgreSQL auf
Debian 12. Produktionsadresse: `https://lab19.ifalabs.org`. Es gibt nur die
GitHub-Environment `production`. Einrichtung, Variablen und Secrets sind in
[CI/CD](ci-cd.md) beschrieben; diese Anleitung enthält keine Zugangsdaten.

T11 umfasst gemäss Benutzerentscheidung die Betriebsdokumentation. Eine
Datenbankwiederherstellung wird im Rahmen der Praxisarbeit nicht durchgeführt.
Die folgenden Wiederherstellungsschritte sind ein Verfahren, kein Prüfnachweis.
Vorhandene und ausstehende Nachweise stehen in [T11-Abnahme](t11-validation.md).

## Reguläre Auslieferung

Ein veröffentlichtes GitHub-Release startet die vollständigen Prüfungen und
anschliessend Veröffentlichung und Deployment. Branch-Pushes und Pull Requests
prüfen den Code, liefern ihn aber nicht produktiv aus. Die Pipeline übernimmt
das bereits gebaute und geprüfte App-Image über seinen GHCR-Digest.

Der Deploy-Job bereitet geschützte Eingaben vor, führt `bootstrap.yml` und dann
`deploy.yml` aus. Ansible verwaltet Docker/Compose, Verzeichnisse, TLS und den
Infrastrukturabgleich. SSH verwendet Passwortauthentifizierung und einen geprüften
Hostschlüssel. Die Anwendung läuft mit Gunicorn hinter Nginx; App und Datenbank
haben in Produktion keine eigenen veröffentlichten Hostports. Öffentliches HTTP
dient Weiterleitung beziehungsweise ACME, nicht der Verarbeitung von Anmeldungen.

Vor einer anstehenden Release-Migration wird die Datenbank gesichert. Die Migration
läuft einmalig im neuen App-Image. Anschliessend werden Dienste, HTTPS und die
lesende API geprüft. Der zentrale `API_SMOKE_KEY` darf systemweit Reparaturen lesen
und gehört deshalb ausschliesslich in die geschützte Konfiguration.

Wiederholungen mit gleichen Eingaben sollen keine Container unnötig neu starten.
Deployment-Sperre und Release-Reihenfolge verhindern parallele oder veraltete
Auslieferungen. Alle vier Produktionsdienste verwenden `restart: unless-stopped`; bewusst
gestoppte Container bleiben gestoppt. Die Neustartrichtlinie ersetzt keine Sicherung. Volumes bleiben erhalten; `down -v` gehört nicht zum Betriebsablauf.

Nach einem Release den Workflow einschliesslich Backup-Upload kontrollieren.
Release-Tag, Commit, App-Digest und Ergebnis der HTTPS-/API-Prüfung im Abnahmeprotokoll
festhalten. Ein grüner Bereitschaftscheck belegt nicht die Zustellung von E-Mails:
Bestätigung oder Passwortwiederherstellung zusätzlich mit einem kontrollierten
Postfach prüfen. SMTP-Annahme und tatsächliche Zustellung unterscheiden.

## Sicherungen und Aufbewahrung

`deploy/ansible/roles/repairhub/tasks/migrate.yml` erstellt mit `pg_dump` einen
Dump im PostgreSQL-Custom-Format. Die Hostkopie liegt unter dem konfigurierten
Installationsverzeichnis in `backups/` (standardmässig `/opt/repairhub/backups`),
mit Verzeichnisrechten 0700 und Dateirechten 0600. Ansible überträgt eine Kopie auf
den Runner; die temporäre Kopie im Datenbankcontainer wird entfernt.

`scripts/ci/encrypt_backups.py` verschlüsselt die Runner-Kopie mit GnuPG/AES-256.
Die Pipeline lädt ausschliesslich `.gpg` im Artefakt
`database-backup-<commit>-<run_attempt>` hoch, auch nach einem fehlgeschlagenen
Deploy, soweit eine Sicherung übertragen wurde. Aufbewahrung: **30 Tage**.
Anschliessend entfernt der Workflow temporäre Klartextdateien und Zugangsdaten
vom Runner. Die geschützte Hostkopie bleibt unverschlüsselt erhalten.

Dies sind **Deployment-Sicherungen**, keine täglichen Backups. Derselbe unveränderte
Release erzeugt nicht automatisch eine neue Sicherung. Ein abgebrochener Runner
vor dem Upload kann die externe Kopie verhindern. Ohne zusätzliche Sicherung können
alle Änderungen seit dem letzten erfolgreichen Dump verloren gehen. Eine garantierte
Wiederanlaufzeit oder ein tägliches Sicherungsintervall ist nicht nachgewiesen.

Für längere Aufbewahrung die verschlüsselten Artefakte vor Ablauf herunterladen
und ausserhalb der VM geschützt archivieren. Die passende `BACKUP_PASSPHRASE`
separat im Passwortmanager behalten; bei Rotation auch die zu älteren Sicherungen
gehörenden Werte erhalten. Hostkopien haben keine automatische Rotation und
benötigen eine kontrollierte Aufbewahrung sowie Überwachung des freien Speichers.

## Unterlagen für einen Serverwechsel

Eine Datenbanksicherung allein stellt den Betrieb nicht wieder her. Zum
Wiederherstellungssatz gehören:

- Verschlüsselter Dump, zugehörige Passphrase und Sicherungszeitpunkt.
- Release-Commit, App-Digest und die gepinnten Infrastruktur-Images; deren
  Verfügbarkeit in den Registries muss erhalten bleiben.
- Passender Repository-Stand mit Compose, Ansible, Nginx und Migrationen sowie
  bekannte Alembic-Revision des gesicherten Schemas.
- Geschützte Konfiguration: Datenbankzugang, Anwendungsschlüssel, SMTP-Zugang,
  API-Prüfschlüssel, Registry- und Hostzugang. Keine Geheimnisse ins Repository kopieren.
- Inventory, öffentliche URL, DNS-Zugang und ACME-Konfiguration. Zertifikate und
  private Schlüssel geschützt übernehmen oder auf dem Ersatzhost neu ausstellen.

GitHub-Environment-Secrets werden nicht vom Datenbank-Dump gesichert. Ein Dump
enthält Anwendungsdaten einschliesslich Identitätsdaten und Schlüssel-Hashes,
jedoch keine vollständige Sicherung der VM, globalen PostgreSQL-Rollen oder TLS-Dateien.

## Datenbankwiederherstellung – dokumentiert, nicht ausgeführt

1. Sicherungszeitpunkt und betroffenen Release bestimmen. Vor einem produktiven
   Eingriff Schreibzugriffe stoppen und den aktuellen Stand separat erhalten.
   Kein Backup ungeprüft über neuere Nutzerdaten schreiben.
2. Verschlüsseltes Artefakt in ein geschütztes Arbeitsverzeichnis herunterladen.
   Mit `gpg --output database.dump --decrypt BACKUP.dump.gpg` entschlüsseln;
   Passphrase interaktiv eingeben, nicht in Shell-Historie oder Logs schreiben.
3. Einen getrennten Zielhost beziehungsweise eine isolierte leere Datenbank mit
   der passenden PostgreSQL-17-Version und benötigter Rolle vorbereiten. Inventory,
   Volumes und Zugangsdaten müssen von Produktion getrennt sein. Ein neuer Host
   wird mit dem vorhandenen Ansible-Bootstrap vorbereitet.
4. Archivinhalt mit `pg_restore --list database.dump` prüfen. Das zeigt die
   Lesbarkeit des Archivs, beweist aber noch keine erfolgreiche Wiederherstellung.
   Anschliessend per `pg_restore` ausdrücklich die isolierte Zieldatenbank wählen,
   bei Fehlern abbrechen und Eigentümer-/Rollen-Zuordnung auf das Ziel abstimmen.
   Es existiert kein automatisiertes Datenbank-Restore-Playbook im Repository.
5. Schema zunächst mit dem zum Backup passenden App-Image verwenden. Weitere
   Migrationen nur kontrolliert über den bestehenden Auslieferungsweg durchführen.
   Tabellen, Alembic-Revision, Datensätze und Beziehungen prüfen; danach Anmeldung,
   Eigentumsgrenzen, Geräte, Reparaturen, Schritte, Teile, CHF-Kosten und API prüfen.
6. Erst nach erfolgreicher fachlicher Prüfung einen produktiven Wechsel planen,
   DNS/TLS und Erreichbarkeit prüfen und den Wiederanlauf protokollieren. Geschützte
   temporäre Klartextkopien anschliessend entfernen.

Diese Schritte wurden für T11 nicht ausgeführt. Entschlüsselungstests oder ein
funktionierender App-Rollback ersetzen die fehlende Datenbank-Restore-Probe nicht.

## Fehlgeschlagene Releases und App-Rollback

Bei fehlgeschlagener Migration oder Abnahme bleibt der Workflow fehlgeschlagen.
Ein automatischer Datenbank-Downgrade findet nicht statt. Der vorhandene App-Rollback
ist nur bei kompatiblem Schema und identischer Infrastruktur zulässig. Er stellt
App-Konfiguration, Image und statische Dateien wieder her und prüft HTTPS/API.

Eine Notfallausführung verwendet `deploy/ansible/rollback.yml` mit derselben
SSH-Hostprüfung und geschützten Eingaben wie die Pipeline; der Aufruf steht in
[CI/CD](ci-cd.md). `repairhub_rollback_schema_compatible=true` darf erst nach
Prüfung der Kompatibilität gesetzt werden. Bei unterbrochenem Infrastrukturabgleich
zuerst den Deploy mit denselben Release-Eingaben abschliessen. Eine zurückgelassene
Hostsperre erst entfernen, wenn nachweislich kein Deployment mehr läuft.

`roles/repairhub/tasks/restore.yml` bezeichnet diesen **App-Rollback**, keine
Rücksicherung von Datenbankinhalten. Bei inkompatiblem Schema ist ein gesonderter
Wartungs- und Wiederherstellungsablauf nötig; kein blindes Zurücksetzen auf ein
älteres Image oder Backup.

## Aktueller Abnahmestand

Der Release-/HTTPS-/API-Nachweis zu v0.9 steht unter [T12](t12-validation.md).
Seit K-T04 umfasst die Sicherung zusätzlich die unveränderlichen Garage-Objekte
als passendes `.dump.files.tar`; beide Archive werden verschlüsselt aufbewahrt.
Für eine Wiederherstellung gehören Datenbank- und Objektarchiv zusammen.
Details und Grenzen: [Garage](garage.md). Ein tatsächlicher Datenbank-/Gesamtrestore
wurde auch bei T12 nicht durchgeführt.

## Korrekturphase und Störungsprotokoll

Die Praxisarbeit verlangt mindestens vier Wochen Erreichbarkeit nach dem tatsächlichen
Abgabetermin. Termin, Fristende, verantwortliche Person und Prüfzugang werden im
[Übergabeblatt](submission/README.md) festgehalten. Solange sie nicht bestätigt sind,
sind sie offen; ein erfolgreicher Release erfüllt die Betriebsfrist noch nicht.

Während der Frist täglich und nach jedem Eingriff von ausserhalb des Hosts prüfen:

```bash
curl --fail --silent --show-error https://lab19.ifalabs.org/health/ready
```

Zusätzlich nach Releases Anmeldung, vorhandenes Beispielgerät und einen persönlichen
API-Lesezugriff kontrollieren; Zugangsdaten nicht in ein öffentliches Protokoll schreiben.
Zertifikatserneuerung, freien Speicher und erfolgreiche zusammengehörige DB-/Garage-
Backups anhand der oben beschriebenen Betriebswege kontrollieren. Diese Regel ist
ein Betriebsplan, kein bereits über 28 Tage ausgeführtes Monitoring.

Bei Ausfall Zeitpunkt und Symptom notieren, Host/Docker/Compose und Bereitschaft prüfen,
anschliessend den dokumentierten Wiederanlauf oder kompatiblen App-Rollback verwenden.
Keine Volumes löschen und keine Datenbank blind auf einen älteren Stand zurücksetzen.
Nach der Behebung HTTPS, Anmeldung und API erneut prüfen. Muss der Examinator informiert
werden, übernimmt dies die verantwortliche Person über den vereinbarten Kontaktkanal.

| Datum/Zeit mit Zeitzone | Prüfung / Symptom | Massnahme | Wieder verfügbar / offen | Verantwortlich |
| --- | --- | --- | --- | --- |
| Nach tatsächlicher Abgabe einzutragen | Noch keine Betriebsfrist protokolliert | — | Offen | Zu bestätigen |
