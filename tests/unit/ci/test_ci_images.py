"""Nicht vertrauenswürdige oder abweichende Image-Artefakte vor Veröffentlichung abweisen."""

import hashlib
import io
import json
import subprocess
import tarfile

import pytest

from scripts.ci import images as image_gate

COMMIT = "a" * 40


@pytest.fixture
def image_artifacts(tmp_path, monkeypatch):
    configuration = {
        "schema_version": 1,
        "nginx_image": "nginx:synthetic@sha256:" + "b" * 64,
        "postgres_image": "example/db@sha256:" + "c" * 64,
        "database_contract": "synthetic-db-contract",
        "postgres_version": "17.11",
    }
    monkeypatch.setattr(image_gate, "load_infrastructure", lambda path: configuration)
    entries = {}
    for name in ("app", "nginx", "db"):
        config = json.dumps({"name": name, "architecture": "amd64", "os": "linux"}).encode()
        image_id = "sha256:" + hashlib.sha256(config).hexdigest()
        with tarfile.open(tmp_path / f"{name}.tar", "w") as archive:
            for filename, content in (
                ("config.json", config),
                ("manifest.json", json.dumps([{"Config": "config.json"}]).encode()),
            ):
                member = tarfile.TarInfo(filename)
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
        reference = f"repairhub-app:{COMMIT}"
        source_reference = None
        if name != "app":
            source_reference = configuration["nginx_image" if name == "nginx" else "postgres_image"]
            reference = image_gate.infrastructure_reference(name, source_reference)
        entries[name] = {
            "archive": f"{name}.tar",
            "sha256": image_gate.checksum(tmp_path / f"{name}.tar"),
            "image_id": image_id,
            "config_digest": image_id,
            "reference": reference,
        }
        if source_reference:
            entries[name]["source_reference"] = source_reference
    manifest = {
        "infrastructure": configuration,
        "commit": COMMIT,
        "platform": "linux/amd64",
        "images": entries,
        "database_contract": "synthetic-db-contract",
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(image_gate, "docker", lambda *args: "")
    monkeypatch.setattr(
        image_gate,
        "inspect_image",
        lambda reference: {
            "Id": next(
                entry["image_id"] for entry in entries.values() if entry["reference"] == reference
            ),
            "Config": {
                "Labels": (
                    {"org.opencontainers.image.revision": COMMIT}
                    if reference.startswith("repairhub-app:")
                    else {}
                ),
                "Env": ["PG_MAJOR=17", "PG_VERSION=17.11", "PGDATA=/var/lib/postgresql/data"],
            },
        },
    )
    return tmp_path, manifest


def test_archive_integrity_and_commit_are_accepted(image_artifacts):
    directory, manifest = image_artifacts
    assert image_gate.verify(directory, COMMIT) == manifest


def test_tampered_archive_stops_release(image_artifacts):
    directory, _ = image_artifacts
    (directory / "app.tar").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="Prüfsumme"):
        image_gate.verify(directory, COMMIT)


def test_different_commit_cannot_use_images(image_artifacts):
    directory, _ = image_artifacts
    with pytest.raises(ValueError, match="Commit"):
        image_gate.verify(directory, "b" * 40)


def test_archive_path_cannot_escape_artifact_directory(image_artifacts):
    directory, manifest = image_artifacts
    manifest["images"]["app"]["archive"] = "../other.tar"
    (directory / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Archivname"):
        image_gate.verify(directory, COMMIT)


def test_wrong_oci_commit_label_blocks(image_artifacts, monkeypatch):
    directory, _ = image_artifacts
    monkeypatch.setattr(
        image_gate,
        "inspect_image",
        lambda reference: {
            "Id": next(
                entry["image_id"]
                for entry in image_artifacts[1]["images"].values()
                if entry["reference"] == reference
            ),
            "Config": {"Labels": {}},
        },
    )
    with pytest.raises(ValueError, match="Commit-Label"):
        image_gate.verify(directory, COMMIT)


def test_wrong_archive_cannot_reuse_a_cached_image_id(image_artifacts):
    directory, manifest = image_artifacts
    manifest["images"]["app"]["image_id"] = "sha256:" + "e" * 64
    (directory / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="erwartete Image-ID"):
        image_gate.verify(directory, COMMIT)


def test_database_contract_must_match_scanned_image(image_artifacts):
    directory, manifest = image_artifacts
    manifest["database_contract"] = "incompatible-data-directory"
    (directory / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Kompatibilitätsvertrag"):
        image_gate.verify(directory, COMMIT)


@pytest.mark.parametrize(
    "environment",
    [
        None,
        {},
        [None],
        [],
        ["PG_MAJOR=18", "PG_VERSION=17.11", "PGDATA=/var/lib/postgresql/data"],
        ["PG_MAJOR=17", "PG_VERSION=17.10", "PGDATA=/var/lib/postgresql/data"],
        ["PG_MAJOR=17", "PG_VERSION=17.11", "PGDATA=/var/lib/postgresql"],
        [
            "PG_MAJOR=17",
            "PG_VERSION=17.11",
            "PG_VERSION=17.11",
            "PGDATA=/var/lib/postgresql/data",
        ],
    ],
)
def test_database_version_or_layout_mismatch_blocks_release(
    image_artifacts, monkeypatch, environment
):
    directory, _ = image_artifacts
    original = image_gate.inspect_image

    def inspect(reference):
        actual = original(reference)
        if reference.startswith("repairhub-db:"):
            actual["Config"]["Env"] = environment
        return actual

    monkeypatch.setattr(image_gate, "inspect_image", inspect)
    with pytest.raises(ValueError, match="PostgreSQL-Image"):
        image_gate.verify(directory, COMMIT)


def test_docker_failure_does_not_include_command_credentials(monkeypatch):
    def failed_run(command, **kwargs):
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(image_gate.subprocess, "run", failed_run)
    with pytest.raises(RuntimeError) as error:
        image_gate.docker("run", "--env", "SECRET_KEY=synthetic-placeholder", "test")
    assert "synthetic-placeholder" not in str(error.value)
    assert error.value.__suppress_context__ is True


@pytest.fixture
def containerd_archive(tmp_path):
    # Docker 29/containerd: Kompatibilitätsmanifest plus Index → Manifest → Konfiguration.
    # Die zusätzliche BuildKit-Attestierung zählt nicht als ausführbares Laufzeitimage.
    config = json.dumps({"architecture": "amd64", "os": "linux"}).encode()
    config_digest = "sha256:" + hashlib.sha256(config).hexdigest()
    runtime = json.dumps(
        {"schemaVersion": 2, "config": {"digest": config_digest}, "layers": []}
    ).encode()
    runtime_digest = "sha256:" + hashlib.sha256(runtime).hexdigest()
    index = json.dumps(
        {
            "schemaVersion": 2,
            "manifests": [
                {"digest": runtime_digest, "platform": {"os": "linux", "architecture": "amd64"}},
                {
                    "digest": "sha256:" + "f" * 64,
                    "annotations": {"vnd.docker.reference.type": "attestation-manifest"},
                    "platform": {"os": "unknown", "architecture": "unknown"},
                },
            ],
        }
    ).encode()
    index_digest = "sha256:" + hashlib.sha256(index).hexdigest()
    archive = tmp_path / "containerd.tar"
    with tarfile.open(archive, "w") as stream:
        contents = {
            "manifest.json": json.dumps(
                [{"Config": "blobs/" + config_digest.replace(":", "/"), "Layers": []}]
            ).encode(),
            "index.json": json.dumps({"manifests": [{"digest": index_digest}]}).encode(),
            "blobs/" + config_digest.replace(":", "/"): config,
            "blobs/" + runtime_digest.replace(":", "/"): runtime,
            "blobs/" + index_digest.replace(":", "/"): index,
        }
        for name, content in contents.items():
            member = tarfile.TarInfo(name)
            member.size = len(content)
            stream.addfile(member, io.BytesIO(content))
    return archive, config_digest, runtime_digest, index_digest


def test_containerd_index_platform_manifest_and_config_are_distinct(containerd_archive):
    archive, config_digest, runtime_digest, index_digest = containerd_archive
    metadata = image_gate.archived_image_metadata(archive)
    assert metadata["config_digest"] == config_digest
    assert set(metadata["identities"]) == {config_digest, runtime_digest, index_digest}
    assert "sha256:" + "f" * 64 not in metadata["identities"]


def test_containerd_descriptor_payload_cannot_be_changed(containerd_archive, tmp_path):
    archive, _, runtime_digest, _ = containerd_archive
    corrupted = tmp_path / "corrupted.tar"
    with tarfile.open(archive, "r") as source, tarfile.open(corrupted, "w") as target:
        for member in source.getmembers():
            content = source.extractfile(member).read()
            if member.name == "blobs/" + runtime_digest.replace(":", "/"):
                content = b"{}"
                member.size = len(content)
            target.addfile(member, io.BytesIO(content))
    with pytest.raises(ValueError, match="Deskriptor-Prüfsumme"):
        image_gate.archived_image_metadata(corrupted)


@pytest.fixture
def upstream_multiarch_archive(containerd_archive, tmp_path):
    archive, config_digest, runtime_digest, previous_index = containerd_archive

    def create(platform):
        old_name = "blobs/" + previous_index.replace(":", "/")
        with tarfile.open(archive, "r") as source:
            index = json.load(source.extractfile(old_name))
            index["manifests"].append({"digest": "sha256:" + "e" * 64, "platform": platform})
            content = json.dumps(index).encode()
            index_digest = "sha256:" + hashlib.sha256(content).hexdigest()
            output = tmp_path / "upstream-multiarch.tar"
            with tarfile.open(output, "w") as target:
                for member in source.getmembers():
                    payload = source.extractfile(member).read()
                    if member.name == old_name:
                        member.name = "blobs/" + index_digest.replace(":", "/")
                        payload = content
                    elif member.name == "index.json":
                        payload = json.dumps({"manifests": [{"digest": index_digest}]}).encode()
                    member.size = len(payload)
                    target.addfile(member, io.BytesIO(payload))
        return output, {config_digest, runtime_digest, index_digest}

    return create


def test_upstream_multiarch_index_accepts_only_the_archived_platform(upstream_multiarch_archive):
    archive, identities = upstream_multiarch_archive({"os": "linux", "architecture": "arm64"})
    metadata = image_gate.archived_image_metadata(archive)
    assert set(metadata["identities"]) == identities
    assert "sha256:" + "e" * 64 not in metadata["identities"]


def test_ambiguous_upstream_platform_cannot_bypass_archive_identity(upstream_multiarch_archive):
    archive, _ = upstream_multiarch_archive({"os": "linux", "architecture": "amd64"})
    with pytest.raises(ValueError, match="genau ein Linux/amd64"):
        image_gate.archived_image_metadata(archive)


def test_containerd_provenance_referrer_is_not_an_additional_runtime(containerd_archive, tmp_path):
    archive, config_digest, runtime_digest, index_digest = containerd_archive
    attestation = json.dumps(
        {"layers": [{"mediaType": "application/vnd.in-toto+json", "digest": "sha256:" + "d" * 64}]}
    ).encode()
    attestation_digest = "sha256:" + hashlib.sha256(attestation).hexdigest()
    extended = tmp_path / "with-referrer.tar"
    with tarfile.open(archive, "r") as source, tarfile.open(extended, "w") as target:
        for member in source.getmembers():
            content = source.extractfile(member).read()
            if member.name == "index.json":
                index = json.loads(content)
                index["manifests"].append(
                    {
                        "digest": attestation_digest,
                        "annotations": {"io.containerd.manifest.subject": runtime_digest},
                    }
                )
                content = json.dumps(index).encode()
                member.size = len(content)
            target.addfile(member, io.BytesIO(content))
        member = tarfile.TarInfo("blobs/" + attestation_digest.replace(":", "/"))
        member.size = len(attestation)
        target.addfile(member, io.BytesIO(attestation))
    metadata = image_gate.archived_image_metadata(extended)
    assert set(metadata["identities"]) == {config_digest, runtime_digest, index_digest}


def test_registry_pull_accepts_linked_platform_digest(containerd_archive, monkeypatch, tmp_path):
    archive, config_digest, runtime_digest, index_digest = containerd_archive
    configuration = {
        "nginx_image": "nginx:synthetic@sha256:" + "b" * 64,
        "postgres_image": "example/db@sha256:" + "c" * 64,
        "database_contract": "synthetic-db-contract",
    }
    manifest = {
        "infrastructure": configuration,
        "database_contract": "synthetic-db-contract",
        "images": {
            "app": {
                "reference": "repairhub-app:" + COMMIT,
                "image_id": index_digest,
                "config_digest": config_digest,
                "archive": archive.name,
            }
        },
    }
    calls = []
    monkeypatch.setattr(image_gate, "verify", lambda directory, commit, infrastructure: manifest)
    monkeypatch.setattr(image_gate, "docker", lambda *args: calls.append(args))
    registry_digest = "ghcr.io/example/repairhub/app@" + index_digest
    monkeypatch.setattr(
        image_gate,
        "inspect_image",
        lambda reference: (
            {"Id": runtime_digest} if "@" in reference else {"RepoDigests": [registry_digest]}
        ),
    )
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    result = image_gate.publish(tmp_path, COMMIT, "example/repairhub")
    assert result["images"]["app"] == registry_digest
    assert ("pull", "--platform", "linux/amd64", registry_digest) in calls


def test_infrastructure_source_must_match_versioned_pin(image_artifacts):
    directory, manifest = image_artifacts
    manifest["images"]["nginx"]["source_reference"] = "nginx@sha256:" + "d" * 64
    (directory / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Infrastruktur-Quelle"):
        image_gate.verify(directory, COMMIT)


def test_build_creates_only_app_and_pulls_pinned_infrastructure(image_artifacts, monkeypatch):
    directory, existing = image_artifacts
    calls = []
    monkeypatch.setattr(image_gate, "docker", lambda *args: calls.append(args))
    monkeypatch.setattr(
        image_gate, "archive_image", lambda directory, name, reference: existing["images"][name]
    )
    monkeypatch.setattr(image_gate, "inspect_image", lambda reference: {"Id": "synthetic-identity"})
    monkeypatch.setattr(
        image_gate, "archived_image_metadata", lambda path: {"identities": ["synthetic-identity"]}
    )
    monkeypatch.setattr(image_gate, "verify", lambda *args: None)
    image_gate.build(directory, COMMIT)
    builds = [command for command in calls if command[0] == "build"]
    assert len(builds) == 1
    assert builds[0][builds[0].index("--target") + 1] == "app"
    assert [command[-1] for command in calls if command[0] == "pull"] == [
        existing["infrastructure"]["nginx_image"],
        existing["infrastructure"]["postgres_image"],
    ]


def test_normal_publisher_pushes_only_app_and_exposes_only_app_output(image_artifacts, monkeypatch):
    directory, manifest = image_artifacts
    calls = []
    app_digest = "ghcr.io/example/repairhub/app@sha256:" + "d" * 64
    monkeypatch.setattr(
        image_gate, "publish_archive", lambda *args: calls.append(args) or app_digest
    )
    output = directory / "outputs"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    released = image_gate.publish(directory, COMMIT, "example/repairhub")
    assert len(calls) == 1
    assert calls[0][1] == manifest["images"]["app"]
    assert calls[0][2] == "ghcr.io/example/repairhub/app"
    assert released["images"] == {
        "app": app_digest,
        "nginx": manifest["infrastructure"]["nginx_image"],
        "db": manifest["infrastructure"]["postgres_image"],
    }
    assert output.read_text() == f"app_image={app_digest}\n"
