"""Einmalige lokale Garage-Zugänge erzeugen; vorhandene Dateien niemals überschreiben."""

import os
import secrets
from pathlib import Path


def setup(directory: Path) -> None:
    garage, storage = directory / "garage.env", directory / "storage.env"
    if garage.exists() and storage.exists():
        print("Garage-Konfiguration ist bereits vorhanden.")
        return
    # Ein Abbruch zwischen den beiden Schreibvorgängen darf beim nächsten Start
    # nicht zwei unterschiedliche Schlüsselpaare für denselben Speicher erzeugen.
    if garage.exists() or storage.exists():
        raise ValueError("Unvollständige Konfiguration: vorhandene Datei sichern und Paar prüfen.")
    access, secret, rpc = "GK" + secrets.token_hex(16), secrets.token_hex(32), secrets.token_hex(32)
    values = {
        garage: f"GARAGE_RPC_SECRET={rpc}\nGARAGE_DEFAULT_ACCESS_KEY={access}\n"
        f"GARAGE_DEFAULT_SECRET_KEY={secret}\nGARAGE_DEFAULT_BUCKET=repairhub\n",
        storage: f"S3_ACCESS_KEY_ID={access}\nS3_SECRET_ACCESS_KEY={secret}\n"
        "S3_BUCKET=repairhub\nS3_REGION=garage\nS3_ENDPOINT=http://garage:3900\n",
    }
    for path, content in values.items():
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
    print("Geschützte garage.env und storage.env angelegt; keine Geheimnisse ausgegeben.")


if __name__ == "__main__":
    setup(Path.cwd())
