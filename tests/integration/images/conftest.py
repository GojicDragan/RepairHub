"""Ein echter, isolierter Garage-Knoten; keine Verbindung zum lokalen Benutzerbestand."""

import json
import os
import secrets
import socket
import subprocess
import time
from pathlib import Path

import pytest
from botocore.exceptions import BotoCoreError, ClientError

from app.data.files.storage import ObjectStorage


@pytest.fixture(scope="session")
def garage(tmp_path_factory):
    directory = tmp_path_factory.mktemp("garage")
    name = "repairhub-images-test-" + secrets.token_hex(6)
    pin = json.loads(Path("deploy/infrastructure.json").read_text())["garage_image"]
    access, secret = "GK" + secrets.token_hex(16), secrets.token_hex(32)
    env = directory / "garage.env"
    fd = os.open(env, os.O_CREAT | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(
            f"GARAGE_RPC_SECRET={secrets.token_hex(32)}\nGARAGE_DEFAULT_ACCESS_KEY={access}\n"
            f"GARAGE_DEFAULT_SECRET_KEY={secret}\nGARAGE_DEFAULT_BUCKET=repairhub\n"
        )

    def docker(*args):
        result = subprocess.run(["docker", *args], capture_output=True, text=True)
        if result.returncode:
            pytest.fail("Isolierte Garage-Testumgebung konnte nicht bereitgestellt werden.")
        return result.stdout.strip()

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        fixed_port = listener.getsockname()[1]
    try:
        docker(
            "run",
            "-d",
            "--name",
            name,
            "--env-file",
            str(env),
            "-p",
            f"127.0.0.1:{fixed_port}:3900",
            "--volume",
            name + ":/var/lib/garage",
            "--mount",
            f"type=bind,src={Path('deploy/garage/garage.toml').resolve()},dst=/etc/garage.toml,readonly",
            pin,
            "/garage",
            "server",
            "--single-node",
            "--default-bucket",
        )
        port = docker("port", name, "3900/tcp").rsplit(":", 1)[1]
        endpoint = f"http://127.0.0.1:{port}"
        storage = ObjectStorage(endpoint, "garage", "repairhub", access, secret)
        for _attempt in range(60):
            try:
                storage.client().head_bucket(Bucket="repairhub")
                break
            except (BotoCoreError, ClientError):
                time.sleep(0.5)
        else:
            pytest.fail("Garage-Bucket wurde nicht bereit.")
        yield {
            "S3_ENDPOINT": endpoint,
            "S3_REGION": "garage",
            "S3_BUCKET": "repairhub",
            "S3_ACCESS_KEY_ID": access,
            "S3_SECRET_ACCESS_KEY": secret,
            "container": name,
            "docker": docker,
            "storage": storage,
        }
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)
        subprocess.run(["docker", "volume", "rm", name], capture_output=True)


@pytest.fixture(autouse=True)
def storage_configuration(garage, monkeypatch):
    for key, value in garage.items():
        if key.startswith("S3_"):
            monkeypatch.setenv(key, value)
