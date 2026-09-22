# T11 – Betriebsdokumentation und Wiederherstellungsvorbereitung

## Vereinbarter Umfang

Auf ausdrücklichen Benutzerentscheid wird T11 für die Praxisarbeit als
Dokumentationsaufgabe abgeschlossen. Eine tatsächliche Datenbankwiederherstellung
entfällt. Dies ersetzt die ursprüngliche T11-Abnahmeforderung nach einem Restore
in eine getrennte Testdatenbank, ohne eine erfolgreiche Wiederherstellung zu behaupten.

Die [Betriebsanleitung](operations.md) beschreibt Auslieferung, Sicherung,
Aufbewahrung, Serverwechsel, App-Rollback und das nicht ausgeführte Restore-Verfahren.
Es gibt keine Änderungen an Anwendung, Infrastrukturcode, Secrets oder Datenbank.

## Nachweise und Grenzen

| Gegenstand | Tatsächlicher Stand |
| --- | --- |
| Produktionsimage, Migration, HTTPS und API | In T10 lokal und isoliert geprüft; siehe [T10](t10-validation.md) |
| Ansible-Erstlauf und Update | T10: erfolgreich; beide Wiederholungen `changed=0`, Container-IDs und Startzeiten unverändert |
| App-/Konfigurationsrollback | Isolierter Fehlerpfad mit vorherigem API-Key in [T09](t09-validation.md) dokumentiert; keine DB-Rücksicherung |
| Backupverfahren | Dokumentation gegen `migrate.yml`, `encrypt_backups.py` und Workflow abgeglichen; Custom-Dump, geschützter Transfer, AES-256, Artefaktaufbewahrung 30 Tage |
| Datenbank-Restore | Dokumentiert, ausdrücklich nicht ausgeführt; Wiederherstellbarkeit fachlich nicht nachgewiesen |
| Aktuelle Produktionsabnahme | Für T11 kein neuer Release und keine Live-Prüfung ausgeführt; frühere Benutzermeldung eines erfolgreichen Produktionslaufs ersetzt keinen aktuellen Nachweis |
| Architektur | Ausschliesslich Markdown geändert; keine Paketgrenzen, Ports, Adapter oder Laufzeitabhängigkeiten verändert |

## Abschluss und Folgeaufgaben

T11 ist im vereinbarten Dokumentationsumfang abgeschlossen. Die bereits vorhandenen
Testergebnisse wurden nicht erneut erzeugt. Lokale Dokumentationslinks und `git diff --check` wurden erfolgreich
geprüft; vollständige Anwendungstests sind für diese reine Dokumentationsänderung
nicht erforderlich.

T12 erstellt die Gesamtabnahme mit 6–12 ausgewählten Fällen und Soll-/Ist-Vergleich.
Der Restore bleibt dort als nicht ausgeführt ausgewiesen. Bei der abschliessenden
Abgabe in T13 die fehlende Restore-Probe sowie die begrenzte Backupaufbewahrung
als Grenzen benennen. Release-Commit, Image-Digest und aktuelle Produktionsprüfung
bleiben separat nachzutragen; T11 behauptet dafür keine neue Abnahme.
