"""Echte Ansible-Retries gegen eine lokale Docker-API-Testantwort prüfen."""

import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("recovers", [True, False])
def test_deployment_waits_for_recovery_but_rejects_persistent_failure(tmp_path, recovers):
    observations = []

    class DockerAPI(BaseHTTPRequestHandler):
        def do_GET(self):
            if "/containers/json?" in self.path:
                payload = [{"Id": "fixture", "Names": ["/repairhub-fixture-app-1"]}]
            elif self.path.endswith("/containers/fixture/json"):
                status = "healthy" if recovers and observations else "unhealthy"
                observations.append(status)
                payload = {"State": {"Status": "running", "Health": {"Status": status}}}
            else:
                self.send_error(404)
                return
            body = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), DockerAPI) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        play = [
            {
                "hosts": "localhost",
                "connection": "local",
                "gather_facts": False,
                "vars": {
                    "ansible_python_interpreter": sys.executable,
                    "repairhub_project_name": "repairhub-fixture",
                    "repairhub_wait_service": "app",
                    "repairhub_wait_timeout": 3,
                },
                "module_defaults": {
                    "community.docker.docker_container_info": {
                        "docker_host": f"tcp://127.0.0.1:{server.server_port}",
                        "api_version": "1.44",
                    }
                },
                "tasks": [
                    {
                        "name": "Exercise production readiness wait",
                        "ansible.builtin.include_tasks": str(
                            ROOT / "deploy/ansible/roles/repairhub/tasks/wait_healthy.yml"
                        ),
                    }
                ],
            }
        ]
        path = tmp_path / "check.yml"
        path.write_text(yaml.safe_dump(play))
        try:
            result = subprocess.run(
                [
                    str(Path(sys.executable).parent / "ansible-playbook"),
                    "-i",
                    "localhost,",
                    str(path),
                ],
                env=dict(os.environ, ANSIBLE_CONFIG=str(ROOT / "deploy/ansible/ansible.cfg")),
                capture_output=True,
                text=True,
                timeout=30,
            )
        finally:
            server.shutdown()
            thread.join(timeout=5)
    assert (result.returncode == 0) == recovers, result.stdout + result.stderr
    assert observations == ["unhealthy", "healthy" if recovers else "unhealthy"]
