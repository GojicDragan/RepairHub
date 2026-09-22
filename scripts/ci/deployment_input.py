"""Geschützte Ansible-Eingaben aus getrennten Environment-Secrets erzeugen."""

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
    # OpenSSH liest die askpass-Antwort als genau eine Passwortzeile.
    if any(character in ssh_password for character in ("\r", "\n", "\0")):
        raise ValueError("SSH-Passwort darf keine Zeilenumbrüche oder NUL-Zeichen enthalten.")
    backup_password = required("BACKUP_PASSPHRASE")
    if len(backup_password) < 32 or any(char in backup_password for char in "\r\n\0"):
        raise ValueError("Backup-Passphrase benötigt mindestens 32 Zeichen ohne Steuerzeichen.")
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
    # Die URL enthält das Geheimnis URL-kodiert; diese Form in Actions separat maskieren.
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::add-mask::{database_url}")
    # Das raw-Format von Compose erhält $, Anführungszeichen und # ohne Interpolation.
    runtime_env = f"SECRET_KEY={secret}\nDATABASE_URL={database_url}\n"
    mail = {
        name: required(name)
        for name in (
            "MAIL_SERVER",
            "MAIL_PORT",
            "MAIL_DEFAULT_SENDER",
            "MAIL_USERNAME",
            "MAIL_PASSWORD",
        )
    }
    mail.update(
        {
            "MAIL_USE_TLS": os.environ.get("MAIL_USE_TLS", "true"),
            "MAIL_USE_SSL": os.environ.get("MAIL_USE_SSL", "false"),
            "PUBLIC_URL": required("PUBLIC_URL"),
        }
    )
    if any(any(char in value for char in "\r\n\0") for value in mail.values()):
        raise ValueError("SMTP-/URL-Werte dürfen keine Zeilenumbrüche oder NUL enthalten.")
    runtime_env += "".join(f"{name}={value}\n" for name, value in mail.items())
    values = {
        "ansible_password": ssh_password,
        "repairhub_app_image": required("APP_IMAGE"),
        "repairhub_release_commit": required("GITHUB_SHA"),
        "repairhub_release_sequence": int(required("GITHUB_RUN_NUMBER")),
        # Die bisherigen Migrationen ergänzen Tabellen und bleiben abwärtskompatibel.
        # Vor künftig inkompatiblen Änderungen muss dieser Modus neu beurteilt werden.
        "repairhub_migration_mode": "compatible",
        "repairhub_backup_fetch_dir": str(directory / "backups"),
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
        # Passwort authentifiziert den Benutzer, der Hostschlüssel dagegen den Server.
        "known_hosts": required("DEPLOY_SSH_KNOWN_HOSTS") + "\n",
    }
    for name, content in paths.items():
        path = directory / name
        # Bereits beim Anlegen restriktive Rechte setzen; ein erst nachträgliches
        # chmod könnte neue Dateien kurzzeitig für andere Benutzer lesbar lassen.
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            stream.write(content)
        path.chmod(0o600)


if __name__ == "__main__":
    main()
