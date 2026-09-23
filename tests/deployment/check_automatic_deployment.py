"""Echter Regressionstest gegen eine vorbereitete isolierte Legacy-Fixture.

Vorher controller.env laden und das alte Image mit old.json bereitstellen.
vars.json beschreibt das neue Image samt geänderter Infrastruktur. Alle Änderungen
betreffen ausschliesslich den gelabelten Docker-in-Docker-Testhost.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


def verify(directory: Path, *, recovery_only: bool = False) -> None:
    host = (directory / "container-name").read_text().strip()
    label = subprocess.check_output(
        ["docker", "inspect", "--format", '{{index .Config.Labels "repairhub.fixture"}}', host],
        text=True,
    ).strip()
    if not host.startswith("repairhub-check-") or label != "deployment":
        raise ValueError("Ausschliesslich isolierte Deployment-Fixtures sind zulässig.")

    def run(*args, input=None):
        result = subprocess.run(
            ["docker", "exec", *(["-i"] if input is not None else []), host, *args],
            input=input,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise AssertionError(
                "Fixture-Kontrollbefehl fehlgeschlagen; keine vertrauliche Ausgabe."
            )
        return result.stdout.strip()

    def containers():
        result = {}
        for service in ("app", "db", "nginx"):
            identifier = run(
                "docker", "ps", "-aq", "--filter", f"label=com.docker.compose.service={service}"
            )
            result[service] = run(
                "docker", "inspect", "--format", "{{.Id}} {{.State.StartedAt}}", identifier
            )
        return result

    def deploy(name, inputs="vars.json", *, success=True, unchanged=False):
        log = directory / (name + ".log")
        command = [
            str(Path(sys.executable).with_name("ansible-playbook")),
            "-i",
            "tests/deployment/inventory.yml",
            "deploy/ansible/deploy.yml",
            "--extra-vars",
            "@" + str(directory / inputs),
        ]
        with log.open("w") as output:
            status = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT).returncode
        if (status == 0) != success:
            raise AssertionError(
                f"Unerwartetes Deployment-Ergebnis: {name}; siehe geschütztes Log."
            )
        text = log.read_text()
        if unchanged and not re.search(r"changed=0\s", text):
            raise AssertionError(f"Wiederholung verändert den Host: {name}.")
        print(name + ": bestanden", flush=True)
        return text

    def sql(query):
        database = run("docker", "ps", "-q", "--filter", "label=com.docker.compose.service=db")
        return run(
            "docker", "exec", database, "psql", "-U", "repairhub", "-d", "repairhub", "-Atc", query
        )

    def check_recovery(target):
        before_recovery = containers()
        installed = json.loads(run("cat", "/opt/repairhub/infrastructure.json"))
        marker = {
            name: installed[name]
            for name in ("fingerprint", "database_contract", "database_configuration_fingerprint")
        }
        # Unterbrechung nach dem Infrastrukturabgleich, vor dessen Abschlussvermerk.
        run(
            "sh",
            "-c",
            'umask 077; cat > "$1"',
            "sh",
            "/opt/repairhub/infrastructure-pending.json",
            input=json.dumps(marker),
        )
        run(
            "chown",
            run("stat", "-c", "%u:%g", "/opt/repairhub/current.json"),
            "/opt/repairhub/infrastructure-pending.json",
        )
        deploy("resume-interrupted")
        assert containers() == before_recovery
        assert (
            run(
                "sh",
                "-c",
                'test ! -e "$1" && echo removed',
                "sh",
                "/opt/repairhub/infrastructure-pending.json",
            )
            == "removed"
        )
        deploy("resumed-repeat", unchanged=True)
        assert containers() == before_recovery

        pins = json.loads(Path(target["repairhub_infrastructure_file"]).read_text())
        pins["database_contract"] = "incompatible-postgres-layout"
        pins_path = directory / "incompatible-infrastructure.json"
        pins_path.write_text(json.dumps(pins))
        denied = directory / "reject-contract.json"
        descriptor = os.open(denied, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w") as output:
            json.dump({**target, "repairhub_infrastructure_file": str(pins_path)}, output)
        deploy("reject-contract", denied.name, success=False, unchanged=True)
        assert containers() == before_recovery
        assert sql("SELECT value FROM deployment_probe") == "preserved"

    if recovery_only:
        check_recovery(json.loads((directory / "vars.json").read_text()))
        return

    old = json.loads((directory / "old.json").read_text())
    target = json.loads((directory / "vars.json").read_text())
    current = json.loads(run("cat", "/opt/repairhub/current.json"))
    if current["app_image"] != old["repairhub_app_image"]:
        raise AssertionError("Der Test benötigt zuerst den alten App-Stand.")
    before = containers()
    deploy("legacy-repeat", "old.json", unchanged=True)
    assert containers() == before, "Identischer alter Release startet Container neu."
    sql(
        "CREATE TABLE deployment_probe(value text PRIMARY KEY); "
        "INSERT INTO deployment_probe VALUES ('preserved')"
    )
    deploy("automatic-upgrade")
    current = json.loads(run("cat", "/opt/repairhub/current.json"))
    assert current["app_image"] == target["repairhub_app_image"]
    assert current["commit"] == target["repairhub_release_commit"]
    assert sql("SELECT value FROM deployment_probe") == "preserved"
    assert sql("SELECT version_num FROM alembic_version")
    upgraded = containers()
    assert upgraded["db"] == before["db"], "Unveränderte Datenbank wurde neu gestartet."
    assert upgraded["nginx"] == before["nginx"], "Nginx-Konfiguration benötigt nur einen Reload."
    log = deploy("automatic-repeat", unchanged=True)
    assert "TASK [repairhub : Migration einmalig" not in log
    assert containers() == upgraded, "Identischer Release startet Container neu."

    # Tatsächliche Dateiabweichungen korrigieren, auch bei unverändertem Soll-Fingerprint.
    path = "/opt/repairhub/infrastructure/nginx/nginx.conf"
    original = run("cat", path)
    run("sh", "-c", 'cat >> "$1"', "sh", path, input="\n# fixture drift\n")
    deploy("repair-drift")
    assert run("cat", path) == original
    assert containers() == upgraded, "Dateireparatur benötigt keinen Container-Neustart."
    deploy("drift-repeat", unchanged=True)

    # Ein laufender, aber unhealthy Nginx muss zuerst seine reparierte Konfiguration
    # laden können. Compose --wait würde bereits vor diesem Reload abbrechen.
    nginx = run("docker", "ps", "-q", "--filter", "label=com.docker.compose.service=nginx")
    assert "proxy_pass http://$upstream;" in original
    broken = original.replace("proxy_pass http://$upstream;", "return 503;")
    run("sh", "-c", 'cat > "$1"', "sh", path, input=broken)
    run("docker", "exec", nginx, "nginx", "-s", "reload", "-c", "/etc/nginx/repairhub/nginx.conf")
    deadline = time.monotonic() + 90
    while run("docker", "inspect", "--format", "{{.State.Health.Status}}", nginx) != "unhealthy":
        if time.monotonic() >= deadline:
            raise AssertionError("Fixture-Nginx wurde mit HTTP 503 nicht unhealthy.")
        time.sleep(1)
    deploy("repair-unhealthy-nginx")
    assert run("docker", "inspect", "--format", "{{.State.Health.Status}}", nginx) == "healthy"
    assert containers() == upgraded, "Nginx-Erholung benötigt keinen Container-Neustart."

    # Ein fehlender Dienst wird wiederhergestellt; die übrigen Dienste bleiben bestehen.
    nginx = run("docker", "ps", "-q", "--filter", "label=com.docker.compose.service=nginx")
    run("docker", "rm", "--force", nginx)
    deploy("repair-missing-nginx")
    repaired = containers()
    assert repaired["app"] == upgraded["app"] and repaired["db"] == upgraded["db"]
    deploy("repaired-repeat", unchanged=True)
    assert containers() == repaired

    # Automatischer Abgleich darf keine Passwortrotation oder inkompatible DB-Upgrades vortäuschen.
    for name, changes in (
        (
            "reject-database-secret",
            {"repairhub_database_env": "POSTGRES_PASSWORD=fixture-rejected-change\n"},
        ),
        (
            "reject-old-release",
            {
                "repairhub_release_sequence": 1,
                "repairhub_release_commit": old["repairhub_release_commit"],
            },
        ),
    ):
        filename = name + ".json"
        descriptor = os.open(directory / filename, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w") as output:
            json.dump({**target, **changes}, output)
        deploy(name, filename, success=False, unchanged=True)
        assert containers() == repaired
    assert sql("SELECT value FROM deployment_probe") == "preserved"
    check_recovery(target)
    print(
        "Automatisches Upgrade, Datenerhalt, Wiederholung, "
        "Driftkorrektur und Schutzprüfungen bestanden.",
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--recovery-only", action="store_true")
    args = parser.parse_args()
    verify(args.directory.resolve(), recovery_only=args.recovery_only)
