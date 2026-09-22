"""Logische Sicherung unveränderlicher Objekte; keine Garage-internen Live-Dateien kopieren."""

import hashlib
import json
import tarfile
from io import BytesIO
from pathlib import Path

from app.data.files.storage import OBJECT_KEY


def backup(storage, destination):
    path = Path(destination)
    client = storage.client()
    manifest = []
    created = False
    try:
        # Exklusiv anlegen: ein erfolgreiches Backup wird niemals überschrieben.
        with path.open("xb") as output:
            created = True
            path.chmod(0o600)
            with tarfile.open(fileobj=output, mode="w") as archive:
                for page in client.get_paginator("list_objects_v2").paginate(Bucket=storage.bucket):
                    for item in page.get("Contents", []):
                        key = item["Key"]
                        if not OBJECT_KEY.fullmatch(key):
                            raise ValueError("unexpected_object")
                        body = storage.read(key)
                        record = {
                            "key": key,
                            "size": len(body),
                            "sha256": hashlib.sha256(body).hexdigest(),
                        }
                        manifest.append(record)
                        entry = tarfile.TarInfo("objects/" + key)
                        entry.size, entry.mode = len(body), 0o600
                        archive.addfile(entry, BytesIO(body))
                data = json.dumps({"version": 1, "objects": manifest}).encode()
                entry = tarfile.TarInfo("manifest.json")
                entry.size, entry.mode = len(data), 0o600
                archive.addfile(entry, BytesIO(data))
    except Exception:
        # Unvollständige Sicherungen bekommen nie den Namen eines gültigen Artefakts.
        # Bestehende Dateien bei exklusivem Öffnungsfehler hingegen unangetastet lassen.
        if created:
            path.unlink(missing_ok=True)
        raise
