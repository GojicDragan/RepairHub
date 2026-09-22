# Isolierter Ansible-Deploymenttest

Diese Fixture startet einen ausschliesslich über Loopback erreichbaren SSH-Host
mit einem eigenen Docker-Daemon. Sie bindet **keinen Docker-Socket des Rechners**
ein. Docker-in-Docker benötigt für diesen lokalen Test `--privileged`.
Die Fixture ist kein Produktivhost und prüft nicht das Ubuntu-Bootstrap-Playbook.
Es gibt keine dauerhafte Testumgebung und kein GitHub Environment `test`.
Das einzige Betriebsziel liegt in `deploy/ansible/inventories/production/`.
Das lokale Inventory `tests/deployment/inventory.yml` ist auf `127.0.0.1`
festgelegt und verwendet ausschliesslich den zufälligen Fixture-SSH-Port aus
`REPAIRHUB_FIXTURE_SSH_PORT`; ohne diesen Wert ist kein gültiger Zielport gesetzt.
Die interne Playbookkennung `repairhub_environment: test` bezeichnet nur diese
wegwerfbare Fixture, deren Compose-Projekt `repairhub-fixture` heisst.

Voraussetzungen sind Linux amd64, Docker, OpenSSH, OpenSSL sowie die installierte
CI-Abhängigkeitsgruppe und Ansible-Collections. Die veröffentlichten Docker-Ports
werden zufällig vergeben. Schlüssel und TLS-Testidentität werden pro Fixture
frisch erzeugt; der SSH-Hostschlüssel wird über den lokalen Docker-Kontrollkanal
bezogen und danach streng geprüft.

Aus dem Repository-Stamm zuerst das App-Image bauen und zusammen mit den
gepinnten offiziellen Nginx- und PostgreSQL-Images archivieren. Deren freigegebene
Digests stehen in `deploy/infrastructure.json`; ein eigener Datenbank-Build oder
eine separate Datenbank-Veröffentlichung ist nicht erforderlich. Für lokale Vorabprüfungen kann
`REPAIRHUB_INFRASTRUCTURE_FILE` auf eine eigene Datei mit echten lokalen
Registry-Digests zeigen. Innerhalb eines Prüfstands bleiben dieselben Archive
Grundlage für Smoke-Test, Scans und Deployment:

```bash
uv sync --locked --group ci
uv run --locked --group ci ansible-galaxy collection install -r deploy/ansible/requirements.yml
uv run --locked python scripts/ci/images.py build --commit "$(git rev-parse HEAD)"
uv run --locked python -m scripts.prepare_deployment_test --directory .qa/deployment --commit "$(git rev-parse HEAD)"
source .qa/deployment/controller.env
uv run --locked --group ci ansible-playbook -i tests/deployment/inventory.yml deploy/ansible/deploy.yml --extra-vars @.qa/deployment/release.json
```

`.qa/deployment` darf vor dem Vorbereitungslauf noch nicht existieren. Bei
uncommitteten Änderungen ist der erzeugte Prüfstand ausdrücklich kein aus diesem
Commit veröffentlichter Release. Ein externer Pipeline-Nachweis entsteht erst
auf GitHub Actions aus dem eingecheckten Stand.

Das Vorbereitungswerkzeug lädt die verifizierten Archive in den isolierten
Daemon, veröffentlicht sie ausschliesslich in dessen lokaler Fixture-Registry
und erzeugt eine separate Infrastruktur-Pin-Datei für Ansible. Diese lokale
Vorbereitung prüft den Digest-Pull, sie bildet keinen normalen GHCR-Publish-Job
nach: dieser veröffentlicht nur die App. Das Werkzeug implementiert keine
zweite Deploymentlogik. `release.json` enthält
vertrauliche Testwerte und darf nicht ausgegeben oder eingecheckt werden.
TLS wird gegen die neu erzeugte lokale Test-CA vollständig validiert.
`controller.env` ist ausschliesslich für diese Fixture bestimmt und setzt auch
`ANSIBLE_INVENTORY` auf deren lokales Inventory. Produktive `DEPLOY_*`-Werte
werden für die Fixture nicht verwendet.

Das Inventory lässt sich vor dem Deployment ohne SSH-Verbindung kontrollieren:

```bash
uv run --locked --group ci ansible-inventory -i tests/deployment/inventory.yml --graph
uv run --locked --group ci ansible-playbook -i tests/deployment/inventory.yml deploy/ansible/deploy.yml --list-hosts
```

Für die Wiederholungsprüfung denselben Ansible-Aufruf erneut ausführen und
Container-IDs sowie `State.StartedAt` im isolierten Daemon vergleichen. Bei einem
App-Update müssen Nginx und DB unverändert bleiben; statische Dateien müssen
aus dem neuen App-Image kommen und beim Rollback zur alten App passen.
Infrastrukturänderungen werden im normalen Deploy automatisch abgeglichen;
identische Eingaben dürfen keine Container neu starten. Weitere Abnahmefälle
sind absichtlicher App-Abnahmefehler mit kompatiblem Rollback, veraltete
Release-Sequenz und falscher SSH-Hostschlüssel.
Die tatsächlich geprüften Fälle stehen in `docs/t02-validation.md`.

Nach abgeschlossener Diagnose nur den ausdrücklich erzeugten Testhost entfernen:

```bash
docker rm --force --volumes "$(cat .qa/deployment/container-name)"
```

Dies entfernt ausschliesslich den wegwerfbaren Testhost samt seinen anonymen
Fixture-Volumes und dem darin isolierten Datenbestand. Es ist kein
Betriebsverfahren für RepairHub. Lokale Testschlüssel und Berichte anschliessend
gezielt entfernen; keine pauschale Docker-Bereinigung durchführen.

## Regression: automatisches Upgrade und Idempotenz

Eine Fixture zunächst mit einem archivierten migrationsfreien T03-Prüfimage und
den Compose-/Nginx-/Capability-Dateien aus v0.3 bereitstellen. Die geschützten
bisherigen Eingaben liegen als `old.json`, die neuen Release-Eingaben als
`vars.json` im Fixture-Verzeichnis. Die neue Release-Sequenz muss höher sein;
alle Registry-Digests stammen weiterhin ausschliesslich aus der lokalen Fixture.
Dann mit dem geladenen `controller.env` aus dem Repository-Stamm ausführen:

```bash
source .qa/FIXTURE/controller.env
uv run --locked --group ci python tests/deployment/check_automatic_deployment.py .qa/FIXTURE
```

Das Prüfskript verlangt Namen und Label eines isolierten Deployment-Testhosts.
Es wiederholt zunächst den alten Stand, legt einen Datenerhalt-Prüfwert an und
führt anschliessend den neuen Release mit geändertem Nginx und Migrationen durch.
Dafür wird ausschliesslich das normale `deploy.yml` verwendet, ohne zusätzliche
Variablen, vorbereitenden Wartungslauf oder Freigabe-Tag.

Geprüft werden Migration, Datenerhalt, `changed=0` bei Wiederholung sowie die
Identität **und Startzeit** aller Container. Danach verändert der Test eine
Nginx-Datei auf dem Host und entfernt den Nginx-Container: Der normale Deploy muss
beides reparieren und anschliessend wieder unverändert durchlaufen. Manipulierte
Datenbank-Zugangsdaten, inkompatible Datenverträge und veraltete Releases müssen
weiterhin ohne Hoständerung scheitern. Ein simulierter Abbruch vor dem Entfernen
des Infrastruktur-Pending-Markers wird mit demselben Deploy abgeschlossen;
die anschliessende Wiederholung muss wieder `changed=0` ergeben. Der Test erzeugt Logs ausschliesslich im geschützten Fixture-Verzeichnis;
keine vollständigen Konfigurationsdateien oder Laufzeitwerte ausgeben.

Konkrete Ergebnisse: [Automatisches Infrastruktur-Upgrade](../../docs/infrastructure-upgrade-validation.md).
