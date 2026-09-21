"""Echte Ansible-Plattformauswahl ohne Installationen auf dem Host ausführen."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
ROLE = ROOT / "deploy/ansible/roles/docker_host"


@pytest.mark.parametrize(
    ("distribution", "version", "architecture", "suffix", "certbot"),
    [
        ("Debian", "12.7", "x86_64", "debian.12~bookworm", "2.1.0-4"),
        ("Ubuntu", "24.04", "x86_64", "ubuntu.24.04~noble", "2.9.0-1"),
        ("Debian", "13", "x86_64", None, None),
        ("Debian", "12", "aarch64", None, None),
    ],
)
def test_platform_gate_and_rendered_packages(
    tmp_path, distribution, version, architecture, suffix, certbot
):
    defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
    tasks = yaml.safe_load((ROLE / "tasks/main.yml").read_text())
    selected = []
    for task in tasks:
        selected.append(task)
        if "ansible.builtin.set_fact" in task:
            break  # Only platform assertion/selection; never package or user operations.
    packages = next(
        task["ansible.builtin.apt"]["name"]
        for task in tasks
        if "Festgelegte Engine" in task["name"]
    )
    certificate_packages = next(
        task["ansible.builtin.apt"]["name"] for task in tasks if task["name"].startswith("Certbot")
    )
    result = tmp_path / "resolved.json"
    selected.append(
        {
            "name": "Record selected values in isolated test directory",
            "ansible.builtin.copy": {
                "dest": str(result),
                "mode": "0600",
                "content": "{{ {'packages': test_packages, 'certbot': test_certbot} | to_json }}",
            },
        }
    )
    play = [
        {
            "hosts": "localhost",
            "connection": "local",
            "gather_facts": False,
            "vars": {
                **defaults,
                "repairhub_deploy_user": "fixture",
                "ansible_facts": {
                    "distribution": distribution,
                    "distribution_version": version,
                    "distribution_major_version": version.split(".")[0],
                    "architecture": architecture,
                },
                "test_packages": packages,
                "test_certbot": certificate_packages,
            },
            "tasks": selected,
        }
    ]
    path = tmp_path / "check.yml"
    path.write_text(yaml.safe_dump(play))
    environment = dict(os.environ, ANSIBLE_CONFIG=str(ROOT / "deploy/ansible/ansible.cfg"))
    process = subprocess.run(
        [str(Path(sys.executable).parent / "ansible-playbook"), "-i", "localhost,", str(path)],
        env=environment,
        capture_output=True,
        text=True,
        timeout=45,
    )
    if suffix is None:
        assert process.returncode != 0
        assert "Erkannte Plattform" in process.stdout
        assert not result.exists()
    else:
        assert process.returncode == 0, process.stdout + process.stderr
        values = json.loads(result.read_text())
        assert values["packages"] == [
            f"docker-ce=5:29.8.1-1~{suffix}",
            f"docker-ce-cli=5:29.8.1-1~{suffix}",
            f"containerd.io=2.3.5-1~{suffix}",
            f"docker-buildx-plugin=0.37.1-1~{suffix}",
            f"docker-compose-plugin=2.40.3-1~{suffix}",
        ]
        assert values["certbot"] == [f"certbot={certbot}", "openssl"]
