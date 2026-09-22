"""Echter GnuPG-Roundtrip sowie Fehler ohne versehentliches Klartext-Artefakt."""

import subprocess

import pytest

from scripts.ci.encrypt_backups import encrypt


@pytest.mark.parametrize("suffix", [".dump", ".dump.files.tar"])
def test_backup_roundtrip_and_wrong_passphrase(tmp_path, suffix):
    source = tmp_path / "source" / "production"
    source.mkdir(parents=True)
    content = b"disposable test database backup"
    (source / ("test" + suffix)).write_bytes(content)
    output = tmp_path / "encrypted"
    password = "synthetic-backup-passphrase-for-tests-only"
    encrypt(source.parent, output, password)
    encrypted = output / ("production-test" + suffix + ".gpg")
    assert content not in encrypted.read_bytes()
    home = tmp_path / "gnupg"
    home.mkdir(mode=0o700)
    command = [
        "gpg",
        "--homedir",
        str(home),
        "--batch",
        "--pinentry-mode",
        "loopback",
        "--no-symkey-cache",
        "--passphrase-fd",
        "0",
        "--decrypt",
        str(encrypted),
    ]
    result = subprocess.run(command, input=password.encode(), capture_output=True, check=True)
    assert result.stdout == content
    rejected = subprocess.run(command, input=b"wrong", capture_output=True, check=False)
    assert rejected.returncode != 0
    assert rejected.stdout == b""
    assert list(output.iterdir()) == [encrypted]


def test_no_backup_needs_no_secret(tmp_path):
    encrypt(tmp_path / "missing", tmp_path / "output", "")
    assert not (tmp_path / "output").exists()


def test_invalid_passphrase_does_not_publish_plaintext(tmp_path):
    source = tmp_path / "production"
    source.mkdir()
    (source / "test.dump").write_bytes(b"private")
    with pytest.raises(ValueError):
        encrypt(tmp_path, tmp_path / "output", "short")
    assert not (tmp_path / "output").exists()


def test_gpg_failure_removes_partial_artifact(tmp_path, monkeypatch):
    source = tmp_path / "production"
    source.mkdir()
    (source / "test.dump").write_bytes(b"private")
    output = tmp_path / "encrypted"

    def fail(command, **kwargs):
        from pathlib import Path

        Path(command[command.index("--output") + 1]).write_bytes(b"partial")
        return subprocess.CompletedProcess(command, 1, b"", b"private diagnostic")

    monkeypatch.setattr("scripts.ci.encrypt_backups.subprocess.run", fail)
    with pytest.raises(RuntimeError, match="Verschlüsselung fehlgeschlagen") as error:
        encrypt(tmp_path, output, "synthetic-backup-passphrase-for-tests-only")
    assert "private" not in str(error.value)
    assert list(output.iterdir()) == []
