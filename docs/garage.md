# Garage: privater Objektspeicher

K-T04 ergänzt auf Benutzerwunsch den Compose-Dienst `garage` mit dem offiziellen
Image `dxflrs/garage:v2.4.1`, festgelegt über den Digest in `deploy/infrastructure.json`.
Dies ist ein technischer Speicherdienst, keine neue Fachkomponente. Nur das App-Image
wird in GHCR veröffentlicht; Garage bleibt ein geprüftes Upstream-Image.

`deploy/garage/garage.toml` verwendet ein persistentes Volume, SQLite-Metadaten und
Replikationsfaktor 1. `--single-node --default-bucket` initialisiert den privaten
Bucket. Diese Praxisarbeitsinstallation ist ausdrücklich nicht hochverfügbar.
S3 ist nur im Compose-Netz unter `garage:3900` erreichbar, RPC nur im Container auf
Loopback. Es gibt keinen veröffentlichten S3-, Admin- oder Website-Port.

## GitHub Environment `production`

Vor dem ersten Release mit K-T04 drei zusätzliche **Secrets** anlegen:

| Secret | Format und Zweck |
| --- | --- |
| `GARAGE_ACCESS_KEY_ID` | `GK` gefolgt von 32 zufälligen Hex-Zeichen; S3-Zugang |
| `GARAGE_SECRET_ACCESS_KEY` | 64 zufällige Hex-Zeichen; zugehöriges S3-Geheimnis |
| `GARAGE_RPC_SECRET` | andere 64 zufällige Hex-Zeichen; interner Garage-Schlüssel |

Lokal erzeugt `scripts/setup_storage.py` solche Werte in geschützten Dateien. Für
Produktion ein eigenes Paar in einem separaten privaten Verzeichnis erzeugen und die
Werte über GitHub Settings → Environments → production → Environment secrets eintragen.
Nicht dieselben Zugänge wie in Development verwenden. Es sind keine zusätzlichen
GitHub-Environment-Variablen nötig.

Ansible schreibt Garage- und App-Speicherzugänge getrennt in geschützte Dateien.
Die Anwendung erhält nur S3-Zugänge, nicht den RPC-Schlüssel. `S3_ENDPOINT`, `S3_REGION`
und `S3_BUCKET` werden mit den festen internen Werten bereitgestellt. Bestehende
Speicherzugänge ändern Releases nicht automatisch: ein Fingerprint schützt vor
versehentlichem Aussperren der gespeicherten Objekte. Eine Rotation benötigt eine
geplante Umstellung der Garage-Schlüssel und der Anwendung.

Unveränderte Releases starten Garage nicht neu. Tatsächliche Änderungen der
bind-gemounteten TOML-Konfiguration lösen gezielt eine Neuerstellung dieses Containers
aus, weil Compose eine reine Inhaltsänderung des Mounts sonst nicht erkennt.

## Backup und Wiederherstellung

Vor einer Migration sichert Ansible zuerst PostgreSQL als `.dump`, danach alle
unveränderlichen Bildobjekte als passende `.dump.files.tar`. Das Archiv enthält
`manifest.json` mit Objektschlüsseln, Grössen und SHA-256 sowie `objects/images/...`.
`flask --app app files-backup <destination>` erzeugt das Archiv exklusiv mit Modus 0600;
fehlgeschlagene Archive werden entfernt, vorhandene Sicherungen nicht überschrieben.

Objekte werden vor Datenbankeinträgen geschrieben und physisch derzeit nicht gelöscht.
Die Löschfunktion entfernt ausschliesslich den erreichbaren Datenbankverweis. Deshalb
enthält der anschliessende Objektexport mindestens die zum Datenbanksnapshot gehörigen
Objekte; parallel hinzugefügte, noch nicht referenzierte Bilder dürfen enthalten sein.
Garage-interne SQLite-/Blockdateien werden nicht unkoordiniert im laufenden Betrieb
kopiert. Beide Sicherungen werden ausserhalb des Hosts mit der vorhandenen
`BACKUP_PASSPHRASE` verschlüsselt und gemeinsam als Workflow-Artefakte aufbewahrt.
Der Objektexport ist vollständig, nicht inkrementell: freien Platz und Laufzeit auf
Host und Runner entsprechend dem gesamten Bildbestand einplanen.

Für eine Wiederherstellung zusammengehörige Datenbank- und Objektarchive desselben
Präfixes aufbewahren. In einer isolierten Zielinstallation zuerst Archivmanifest,
Grössen und Prüfsummen kontrollieren; nur Schlüssel des Formats
`images/<32 hex>.webp` beziehungsweise `images/<32 hex>-thumb.webp` zulassen.
Die geprüften Objekte über einen S3-Client in den privaten Bucket hochladen und das
passende PostgreSQL-Backup nach dem vorhandenen Wiederherstellungsplan einspielen.
Nicht blind als Root entpacken oder über laufende neuere Nutzerdaten schreiben.
Erst nach Bild-, Eigentums- und Funktionsprüfung den Verkehr umschalten.
Die tatsächliche Wiederherstellungsübung ist gemäss Benutzerentscheidung nicht
Bestandteil dieser Praxisarbeit; der Export wurde dagegen automatisiert geprüft.

## Security-Scan des offiziellen Images

Garage liefert ein Scratch-Image mit einem Rust-Binary ohne eingebettetes
`cargo-auditable`-Inventar. Ein gewöhnlicher Trivy-Imagescan allein kann dessen
Rust-Abhängigkeiten deshalb nicht nachweisen. Die Pipeline prüft zusätzlich die
Cargo-Manifeste und das Lockfile des offiziellen Release-Commits
`268334bd2530fa99f8b06c7383b2e9f776691edd`.

`deploy/security/garage-source.json` bindet diesen Commit, sämtliche Manifest-Hashes
und den exakten Image-Digest zusammen. `scripts/ci/garage_inventory.py` verfolgt alle
normalen und Build-Abhängigkeiten einschliesslich optionaler und plattformspezifischer
Abhängigkeiten konservativ; lediglich reine Workspace-Testabhängigkeiten bleiben
weg. Das resultierende Inventar umfasst 497 Pakete. Trivy prüft dieses Inventar ohne
CVE-Ausnahmen. Fehlende Quellen, falsche Hashes, ein anderer Image-Digest, leere
Inventare oder hohe/kritische Befunde blockieren. Der allgemeine Schutz gegen leere
Image-Scanberichte bleibt erhalten. Image-Updates benötigen einen neuen Quellenabgleich.

Grenze dieses Nachweises: Die Zuordnung des Rust-Quellstands zum Binary beruht auf dem
festgelegten offiziellen Release, nicht auf einer reproduzierten eigenen Übersetzung
oder einem im Binary enthaltenen Inventar. Dies wird im Scanartefakt dokumentiert.
Das veraltete `rustls-webpki` der Upstream-Integrationstests ist nicht Teil der
normalen Abhängigkeiten; das Laufzeitinventar enthält `rustls-webpki 0.103.13`.

Quellen: [Garage-Release-Quellen](https://git.deuxfleurs.fr/Deuxfleurs/garage/src/commit/268334bd2530fa99f8b06c7383b2e9f776691edd),
[Trivy: Rust](https://trivy.dev/docs/v0.69/guide/coverage/language/rust/).
