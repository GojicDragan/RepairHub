"""Create protected Ansible input from separate environment secrets."""

import json
import os
from pathlib import Path
from urllib.parse import quote


def required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise ValueError(f"Erforderliche Deployment-Eingabe fehlt: {name}")
    return value


def main() -> None:
    required("REPAIRHUB_DEPLOY_HOST")
    required("REPAIRHUB_DEPLOY_USER")
    ssh_password = required("DEPLOY_SSH_PASSWORD")
    # OpenSSH consumes the askpass response as one password line.
    if any(character in ssh_password for character in ("\r", "\n", "\0")):
        raise ValueError("SSH-Passwort darf keine Zeilenumbrüche oder NUL-Zeichen enthalten.")
    directory = Path(required("DEPLOY_INPUT_DIR"))
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory.chmod(0o700)
    user = os.environ.get("POSTGRES_USER", "repairhub")
    database = os.environ.get("POSTGRES_DB", "repairhub")
    password = required("POSTGRES_PASSWORD")
    secret = required("SECRET_KEY")
    if any("\n" in item or "\r" in item for item in (user, database, password, secret)):
        raise ValueError("Laufzeitwerte dürfen keine Zeilenumbrüche enthalten.")
    database_url = (
        f"postgresql+psycopg://{quote(user, safe='')}:{quote(password, safe='')}"
        f"@db:5432/{quote(database, safe='')}"
    )
    # The derived URL contains a URL-encoded secret, so mask it separately in Actions.
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::add-mask::{database_url}")
    # Compose's raw env-file format preserves $, quotes and # without interpolation.
    runtime_env = f"SECRET_KEY={secret}\nDATABASE_URL={database_url}\n"
    values = {
        "ansible_password": ssh_password,
        "repairhub_app_image": required("APP_IMAGE"),
        "repairhub_release_commit": required("GITHUB_SHA"),
        "repairhub_release_sequence": int(required("GITHUB_RUN_NUMBER")),
        "repairhub_public_url": required("PUBLIC_URL"),
        "repairhub_postgres_user": user,
        "repairhub_postgres_db": database,
        "repairhub_runtime_env": runtime_env,
        "repairhub_database_env": f"POSTGRES_PASSWORD={password}\n",
        "repairhub_tls_mode": "acme",
        "repairhub_acme_email": required("ACME_EMAIL"),
        "ansible_become_password": os.environ.get("DEPLOY_BECOME_PASSWORD", ""),
        "repairhub_registry_username": os.environ.get("GHCR_READ_USERNAME", ""),
        "repairhub_registry_password": os.environ.get("GHCR_READ_TOKEN", ""),
    }
    paths = {
        "vars.json": json.dumps(values),
        "known_hosts": required("DEPLOY_SSH_KNOWN_HOSTS") + "\n",
    }
    for name, content in paths.items():
        path = directory / name
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            stream.write(content)
        path.chmod(0o600)


if __name__ == "__main__":
    main()
