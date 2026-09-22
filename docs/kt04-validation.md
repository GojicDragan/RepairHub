# K-T04 – lokaler Prüfnachweis

Benutzerentscheidung: ausschliesslich Bilder, keine PDF-Anhänge; Darstellung als
Mosaik. Privater Speicher über das offizielle `dxflrs/garage`-Image.

## Geprüfter Umfang

- 700 Python-Unit-Tests bestanden, einschliesslich Domain-Fakes, Bildvalidierung,
  Architekturgrenzen, Backup-Verschlüsselung und striktem Garage-Quellinventar.
- 30 JavaScript-Tests bestanden; Auswahl, deaktivierte Buttons, Mehrfachsendeschutz,
  Erfolgs- und Fehlerzustände ohne DOM im Presenter geprüft.
- PostgreSQL-Integrationslauf: 317 von 318 zunächst erfolgreich. Der verbleibende
  Test erwartete noch die alte Tabellenliste; um die beiden Bildtabellen ergänzt
  und separat erfolgreich wiederholt. Alembic meldet keine Modellabweichungen.
  Zwei zusätzlich ausgeführte Paginationstests bestanden (je 26 echte Uploads,
  erste Seite 24 Bilder, zweite Seite 2). Insgesamt damit 320 Integrationsfälle geprüft.
- 16 Browser-E2E-Tests bestanden: AJAX auf Deutsch und ohne JavaScript auf Englisch,
  echte Garage-Bilder, private Abrufe, ungültige Inhalte und mobile Darstellung.
  Screenshots unter `reports/kt04/` für Geräte/Reparaturen bei 1280 und 390 Pixeln;
  Desktop- und Mobilmosaik visuell geprüft.
- Echte Garage-Integration prüft Bildabruf nach Container-Neustart sowie Objektexport
  mit Manifest und Prüfsummen. Keine produktiven Daten für Tests verwendet.
- Architekturprüfskript, Ruff, Formatprüfung, Actionlint und Ansible-Lint bestanden.
  Die Fachdomänen bleiben frei von Flask, ORM, Pillow, boto3 und konkreten Adaptern.
- App-Image gebaut; archivierte Kombination aus App, Nginx, PostgreSQL und Garage mit
  PostgreSQL und HTTPS gestartet und geprüft. Nur das App-Image wird veröffentlicht.
- Dependency-Scan, Bandit, Gitleaks, Trivy und ergänzender Garage-Rust-Scan bestanden.
  Zusätzlich den vollständigen aktuellen Arbeitsstand mit Gitleaks geprüft, einschliesslich
  noch nicht eingecheckter Dateien. Aktiver isolierter ZAP-DAST-Lauf: Exit 0.

## Deployment

Das echte Ansible-Playbook lief gegen einen isolierten SSH-/Docker-Testhost.
Während der Umsetzung gefundene Compose-, Dateiberechtigungs- und Backup-UID-Fehler
wurden korrigiert. Der abschliessende vollständige Lauf meldet `failed=0`,
`rescued=0`; Datenbank- und Objektbackup werden vor Migration erzeugt und vom Host
geholt. Der Lauf umfasst Migration, App-Auslieferung, HTTPS und authentifizierte API-Prüfung.

Wiederholung mit identischen Eingaben: `changed=0`, `failed=0`. IDs und Startzeiten
aller vier Container (App, Nginx, PostgreSQL, Garage) sind unverändert.
Der Objektbackup-Schritt verwendet die numerische Eigentümerschaft des geschützten
Hostverzeichnisses, statt Root-Zugriff ohne `DAC_OVERRIDE` vorauszusetzen.

Die lokale Entwicklungsdatenbank wurde vor Migration gesichert. Migration auf
`0006_images`, Garage-Start und App-Aktualisierung durchgeführt; lokaler
Bereitschaftscheck unter Port 8080 erfolgreich. Kein Produktionsdeployment ausgeführt.

## Grenzen und offene Abnahme

Vor dem Release müssen die drei [Garage-Secrets](garage.md) in GitHub `production`
vorhanden sein. Die tatsächliche Release-Abnahme auf dem Produktionshost bleibt offen.
Die Zuordnung des Garage-Quellinventars zum offiziellen Binary und ihre Grenze sind
in [Garage](garage.md) dokumentiert; es wird keine eingebettete Binary-SBOM behauptet.
Ein tatsächlicher vollständiger Restore wurde gemäss Benutzerentscheidung nicht
praktisch durchgeführt. Keine PDF-Anhänge oder öffentliche S3-Freigabe.

## Ergänzung: Bilder löschen

Eigene Bilder können nach einer Bestätigung in der Mosaikkachel entfernt werden.
Neue `delete_image`-Slices halten die Eigentumsprüfung im Fachkern; der Adapter
entfernt den Datenbankverweis atomar. Private Garage-Objekte bleiben für konsistente
laufende Backups erhalten (keine physische Speicherbereinigung).

Erneut geprüft: 708 Unit-Tests, 30 JavaScript-Tests, 24 Bild-Integrationstests mit
PostgreSQL und Garage sowie beide Bild-Browserabläufe (AJAX/Deutsch und ohne
JavaScript/Englisch) bestanden. Löschfälle prüfen CSRF, fremden Zugriff, GET-Verbot,
wiederholte Löschung und 404 für Original/Vorschau nach Erfolg. Architekturprüfung,
Ruff und Formatprüfung bestanden. Neues App-Image gebaut; Dependency-, Bandit-,
Gitleaks- und Trivy-Prüfungen einschliesslich Garage-Quellinventar bestanden.
Auch nicht eingecheckte Dateien wurden erneut mit Gitleaks geprüft. Die zuvor
beschriebene ZAP-Abnahme stammt vom Stand vor Ergänzung des Löschendpunkts.
Lokale Anwendung aktualisiert; keine neue Migration oder neue Secrets erforderlich.
