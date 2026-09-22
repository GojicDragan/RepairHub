# Automatisches Infrastruktur-Upgrade und Idempotenz

## Verhalten

Der normale `deploy.yml`-Aufruf gleicht Infrastruktur und Anwendung automatisch
mit dem geprüften Stand ab. Die auf Benutzerwunsch verworfene Freigabe pro Tag
ist entfernt; weder `INFRASTRUCTURE_MAINTENANCE_TAG` noch ein vorbereitender
Wartungsaufruf ist erforderlich. Eine bereits angelegte Variable bleibt wirkungslos.

Dateien und Compose-Dienste werden bei jedem Lauf tatsächlich abgeglichen.
Unveränderte Dienste behalten Container-ID und Startzeit. Abweichende Dateien
werden wiederhergestellt; fehlende Dienste werden neu angelegt. Nur eine
geänderte Nginx-Konfiguration führt nach erfolgreichem Syntaxcheck zum Reload.
Ein gespeicherter Fingerprint allein gilt nicht als Nachweis des tatsächlichen
Hostzustands. Infrastruktur-Snapshots und der Abschlussmarker bleiben erhalten.

Die Schritte laufen unter einer gemeinsamen Hostsperre: Konfiguration und
geprüfte Images, Datenbankbereitschaft, gegebenenfalls Backup/Migration im neuen
App-Image, App/Assets, Nginx, HTTPS-/API-Abnahme. Die bestehende alte App führt
keine neuen Migrationen aus. Nach Unterbrechung kann derselbe Deploy fortgesetzt
werden; der Pending-Marker erzwingt keinen manuellen Sonderweg.

Datenbank-Vertragswechsel, Änderungen bestehender Datenbankzugänge und veraltete
Release-Sequenzen werden weiterhin vor Hoständerungen abgewiesen. Die bisherigen
Vorgaben für kompatiblen App-Rollback, Sicherungen und Verzicht auf automatische
Datenbank-Downgrades bleiben bestehen. Ein reiner `infrastructure.yml`-Aufruf
ist optional; er verwendet weiterhin den laufenden Digest und dessen Fähigkeiten.

## Bezug zum gemeldeten Fehler

Installiert war Commit `a0d8174be766ca7289c9a8f853894edd362d0f82` (v0.3).
v0.5 zeigt auf `0901b5f8b724d03fdeb80421c015730a13fa7e7a`. Zwischen diesen Tags
ändert sich die Nginx-Konfiguration; Compose und Infrastruktur-Pins sind gleich.
Das frühere Playbook wies diesen Sollzustandswechsel ab. Der automatische
Abgleich übernimmt ihn jetzt innerhalb desselben normalen Deployments.

Die Korrektur benötigt einmalig einen neuen Commit/Release. Ein Retry von v0.5
führt weiterhin dessen alten Workflow aus. Danach sind keine manuellen
Freigabevariablen pro Release nötig. Bedienung: [CI/CD](ci-cd.md#automatischer-idempotenter-infrastrukturabgleich).

## Regressionstest vom 22. September 2026

Isolierter Docker-in-Docker-Host, Test-Registry, eigene SSH-Schlüssel und Test-CA;
keine Produktionsverbindung. Ausgang: archiviertes migrationsfreies T03-Prüfimage
und Compose-/Nginx-/Capability-Dateien aus v0.3. Ziel: aktuelles T07-Prüfimage mit
Migrationen. Dies prüft den Fähigkeitswechsel und Datenerhalt; es ist kein
Nachweis eines aus GitHub veröffentlichten v0.5-Images.

Reproduzierbarer Test: `tests/deployment/check_automatic_deployment.py`.
Das Skript prüft Container-IDs und `StartedAt`, Release-Metadaten, einen vor dem
Upgrade gespeicherten PostgreSQL-Prüfwert und die tatsächlich angelegte
Alembic-Version. Alle Prüfungen verwenden das normale `deploy.yml` ohne zusätzliche
Freigabe. Geschützte lokale Logs: `.qa/automatic-deployment/`.

| Prüfung | changed | Ergebnis |
| --- | --- | --- |
| Alten Stand initial bereitstellen | 23 | Bestanden |
| Alten Stand wiederholen | 0 | Bestanden |
| Direktes Upgrade mit Nginx-Änderung und Migration | 32 | Bestanden |
| Neuen Stand wiederholen | 0 | Bestanden |
| Abweichende Nginx-Datei korrigieren | 2 | Bestanden |
| Nach Dateikorrektur wiederholen | 0 | Bestanden |
| Fehlenden Nginx-Container wiederherstellen | 1 | Bestanden |
| Nach Wiederherstellung wiederholen | 0 | Bestanden |
| Geänderte DB-Zugangsdaten abweisen | 0 | Erwartungsgemäss blockiert |
| Veralteten Release abweisen | 0 | Erwartungsgemäss blockiert |
| Unterbrochenen Abgleich abschliessen | 1 | Bestanden |
| Nach Wiederaufnahme wiederholen | 0 | Bestanden |
| Inkompatiblen DB-Vertrag abweisen | 0 | Erwartungsgemäss blockiert |

Die Wiederholungen haben auch identische Container-IDs und Startzeiten bestätigt.
Der PostgreSQL-Prüfwert blieb über sämtliche Schritte erhalten. Die anfänglich
falsche Eigentümerschaft des künstlich angelegten Pending-Markers wurde in der
Test-Fixture korrigiert; der erneute Wiederaufnahmetest bestand.
Die eigene Fixture wurde nach Abschluss entfernt. TLS wurde mit einer lokalen
Test-CA geprüft; der ACME-Ablauf ist unverändert und wurde hier nicht erneut getestet.

Zusätzlich: 218 CI-Python-Tests, 97 Architekturtests, Architektur-Skript,
Ansible-Lint und Actionlint bestanden. App-/Domain-Code und die bereits geprüften
Container-Images wurden für diese Korrektur nicht verändert.
