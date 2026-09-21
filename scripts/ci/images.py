"""Build once, verify archives, and publish the exact scanned image IDs."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import tarfile
from pathlib import Path

if __package__:
    from .infrastructure import load as load_infrastructure
else:
    from infrastructure import load as load_infrastructure

SHA = re.compile(r"[0-9a-f]{40}\Z")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")


def docker(*args: str, capture: bool = False) -> str:
    try:
        result = subprocess.run(["docker", *args], check=True, text=True, capture_output=capture)
    except subprocess.CalledProcessError as error:
        # docker run arguments may contain ephemeral test credentials; never echo argv.
        raise RuntimeError(f"Docker-Operation fehlgeschlagen (Exit {error.returncode}).") from None
    return result.stdout.strip() if capture else ""


def checksum(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def archived_image_metadata(path: Path) -> dict:
    """Separate config identity from Docker's classic/config or containerd/OCI ID."""
    with tarfile.open(path, "r") as archive:

        def read_file(name: str) -> bytes:
            member = archive.getmember(name)
            if not member.isfile():
                raise ValueError("Docker-Metadaten sind keine reguläre Datei.")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError("Docker-Metadaten fehlen.")
            return stream.read()

        manifest = json.loads(read_file("manifest.json"))
        if not isinstance(manifest, list) or len(manifest) != 1:
            raise ValueError("Docker-Archiv muss genau ein Laufzeitimage enthalten.")
        config_bytes = read_file(manifest[0]["Config"])
        config_digest = "sha256:" + hashlib.sha256(config_bytes).hexdigest()
        config = json.loads(config_bytes)
        if config.get("architecture") != "amd64" or config.get("os") != "linux":
            raise ValueError("Docker-Archiv entspricht nicht linux/amd64.")
        identities = {config_digest}

        def walk(descriptor: dict) -> None:
            digest = descriptor["digest"]
            if not DIGEST.fullmatch(digest):
                raise ValueError("Ungültiger OCI-Deskriptor.")
            payload = read_file("blobs/" + digest.replace(":", "/"))
            if "sha256:" + hashlib.sha256(payload).hexdigest() != digest:
                raise ValueError("OCI-Deskriptor-Prüfsumme stimmt nicht überein.")
            document = json.loads(payload)
            if "manifests" in document:
                candidates = [
                    item
                    for item in document["manifests"]
                    if item.get("annotations", {}).get("vnd.docker.reference.type")
                    != "attestation-manifest"
                ]
                # A pulled upstream index retains descriptors for other platforms,
                # whose blobs docker save deliberately omits. Bind the full index
                # digest, but follow only its unique Linux/amd64 runtime branch.
                for item in candidates:
                    if not DIGEST.fullmatch(item.get("digest", "")):
                        raise ValueError("Ungültiger OCI-Plattform-Deskriptor.")
                    if len(candidates) > 1 and (
                        not isinstance(item.get("platform"), dict)
                        or not item["platform"].get("os")
                        or not item["platform"].get("architecture")
                    ):
                        raise ValueError("Mehrdeutige OCI-Plattformangabe.")
                runtime = [
                    item
                    for item in candidates
                    if item.get("platform", {"os": "linux", "architecture": "amd64"}).get("os")
                    == "linux"
                    and item.get("platform", {"architecture": "amd64"}).get("architecture")
                    == "amd64"
                    and not item.get("platform", {}).get("variant")
                ]
                if len(runtime) != 1:
                    raise ValueError(
                        "OCI-Index muss genau ein Linux/amd64-Laufzeitimage enthalten."
                    )
                walk(runtime[0])
            else:
                if document.get("config", {}).get("digest") != config_digest:
                    raise ValueError("OCI-Manifest und Docker-Konfiguration widersprechen sich.")
                layers = [
                    "blobs/" + layer["digest"].replace(":", "/")
                    for layer in document.get("layers", [])
                ]
                if layers != manifest[0].get("Layers", []):
                    raise ValueError("OCI- und Docker-Laufzeitschichten widersprechen sich.")
            identities.add(digest)

        if "index.json" in archive.getnames():
            index = json.loads(read_file("index.json"))
            descriptors = index.get("manifests", [])
            runtime = [
                item
                for item in descriptors
                if "io.containerd.manifest.subject" not in item.get("annotations", {})
            ]
            if len(runtime) != 1:
                raise ValueError("OCI-Archiv muss genau ein oberstes Laufzeitimage enthalten.")
            walk(runtime[0])
            for descriptor in descriptors:
                subject = descriptor.get("annotations", {}).get("io.containerd.manifest.subject")
                if subject is None:
                    continue
                digest = descriptor["digest"]
                if subject not in identities or not DIGEST.fullmatch(digest):
                    raise ValueError("OCI-Attestierung gehört nicht zum Laufzeitimage.")
                payload = read_file("blobs/" + digest.replace(":", "/"))
                if "sha256:" + hashlib.sha256(payload).hexdigest() != digest:
                    raise ValueError("OCI-Attestierungs-Prüfsumme stimmt nicht überein.")
                layers = json.loads(payload).get("layers", [])
                if not layers or any(
                    layer.get("mediaType") != "application/vnd.in-toto+json" for layer in layers
                ):
                    raise ValueError("OCI-Referrer ist keine reine Attestierung.")
        return {"config_digest": config_digest, "identities": sorted(identities)}


def inspect_image(reference: str) -> dict:
    return json.loads(docker("image", "inspect", reference, capture=True))[0]


def archive_image(directory: Path, name: str, reference: str) -> dict:
    archive = directory / f"{name}.tar"
    docker("save", "--output", str(archive), reference)
    metadata = archived_image_metadata(archive)
    image_id = inspect_image(reference)["Id"]
    if image_id not in metadata["identities"]:
        raise ValueError("Docker-Archiv stimmt nicht mit dem bereitgestellten Image überein.")
    return {
        "reference": reference,
        "image_id": image_id,
        "config_digest": metadata["config_digest"],
        "archive": archive.name,
        "sha256": checksum(archive),
    }


def infrastructure_reference(name: str, source: str) -> str:
    return f"repairhub-{name}:infra-{source.rsplit(':', 1)[1]}"


def build(directory: Path, commit: str, infrastructure: Path | None = None) -> None:
    configuration = load_infrastructure(infrastructure)
    directory.mkdir(parents=True, exist_ok=True)
    app_reference = f"repairhub-app:{commit}"
    docker(
        "build",
        "--platform",
        "linux/amd64",
        "--target",
        "app",
        "--build-arg",
        f"VCS_REF={commit}",
        "--tag",
        app_reference,
        ".",
    )
    images = {"app": archive_image(directory, "app", app_reference)}
    for name, field in (("nginx", "nginx_image"), ("db", "postgres_image")):
        source = configuration[field]
        docker("pull", "--platform", "linux/amd64", source)
        source_identity = inspect_image(source)["Id"]
        reference = infrastructure_reference(name, source)
        docker("tag", source, reference)
        entry = archive_image(directory, name, reference)
        if (
            source_identity
            not in archived_image_metadata(directory / entry["archive"])["identities"]
        ):
            raise ValueError("Infrastruktur-Archiv entspricht nicht dem gepinnten Quellimage.")
        entry["source_reference"] = source
        images[name] = entry
    (directory / "manifest.json").write_text(
        json.dumps(
            {
                "commit": commit,
                "platform": "linux/amd64",
                "images": images,
                "infrastructure": configuration,
                "database_contract": configuration["database_contract"],
            },
            indent=2,
        )
        + "\n"
    )
    verify(directory, commit, infrastructure)


def verify_archive(directory: Path, name: str, entry: dict, reference: str) -> dict:
    if entry["archive"] != f"{name}.tar":
        raise ValueError("Ungültiger Archivname.")
    archive = directory / entry["archive"]
    if checksum(archive) != entry["sha256"]:
        raise ValueError(f"Prüfsumme stimmt für {name} nicht überein.")
    metadata = archived_image_metadata(archive)
    if (
        metadata["config_digest"] != entry.get("config_digest")
        or entry["image_id"] not in metadata["identities"]
    ):
        raise ValueError(f"Archiv enthält nicht die erwartete Image-ID für {name}.")
    if entry["reference"] != reference:
        raise ValueError("Unerwartete Image-Referenz.")
    docker("load", "--input", str(archive))
    actual = inspect_image(reference)
    if actual["Id"] not in metadata["identities"]:
        raise ValueError(f"Image-ID stimmt für {name} nicht mit dem Archiv überein.")
    return actual


def verify_database_environment(actual: dict, configuration: dict) -> None:
    # These are upstream image settings, not labels from a custom database build.
    expected = {
        "PG_MAJOR": configuration["postgres_version"].split(".", 1)[0],
        "PG_VERSION": configuration["postgres_version"],
        "PGDATA": "/var/lib/postgresql/data",
    }
    entries = actual["Config"].get("Env")
    if not isinstance(entries, list) or any(not isinstance(item, str) for item in entries):
        raise ValueError("PostgreSQL-Image enthält keine gültige Laufzeitkonfiguration.")
    for name, value in expected.items():
        matching = [item for item in entries if item.startswith(name + "=")]
        if matching != [f"{name}={value}"]:
            raise ValueError(f"PostgreSQL-Image weicht bei {name} vom geprüften Stand ab.")


def verify(directory: Path, commit: str, infrastructure: Path | None = None) -> dict:
    configuration = load_infrastructure(infrastructure)
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest.get("commit") != commit or manifest.get("platform") != "linux/amd64":
        raise ValueError("Image-Artefakt gehört nicht zum geprüften Commit/Plattform.")
    if manifest.get("infrastructure") != configuration:
        raise ValueError("Image-Artefakt entspricht nicht den geprüften Infrastruktur-Pins.")
    if manifest.get("database_contract") != configuration["database_contract"]:
        raise ValueError(
            "PostgreSQL-Kompatibilitätsvertrag stimmt nicht mit Infrastruktur überein."
        )
    if set(manifest.get("images", {})) != {"app", "nginx", "db"}:
        raise ValueError("Die freigegebene Image-Kombination ist unvollständig.")
    for name, entry in manifest["images"].items():
        reference = f"repairhub-app:{commit}"
        if name != "app":
            source = configuration["nginx_image" if name == "nginx" else "postgres_image"]
            if entry.get("source_reference") != source:
                raise ValueError("Infrastruktur-Quelle stimmt nicht mit dem geprüften Pin überein.")
            reference = infrastructure_reference(name, source)
        actual = verify_archive(directory, name, entry, reference)
        if name == "app":
            if (
                actual["Config"].get("Labels", {}).get("org.opencontainers.image.revision")
                != commit
            ):
                raise ValueError("Commit-Label fehlt für app.")
        elif name == "db":
            verify_database_environment(actual, configuration)
    return manifest


def validate_repository(repository: str) -> None:
    if not re.fullmatch(r"[a-z0-9_.-]+/[a-z0-9_.-]+", repository):
        raise ValueError("Ungültiger GHCR-Namespace.")


def publish_archive(directory: Path, entry: dict, image_name: str, tag: str) -> str:
    reference = f"{image_name}:{tag}"
    docker("tag", entry["reference"], reference)
    docker("push", reference)
    candidates = inspect_image(reference).get("RepoDigests", [])
    matches = [item for item in candidates if item.startswith(f"{image_name}@")]
    if len(matches) != 1 or not DIGEST.fullmatch(matches[0].split("@", 1)[1]):
        raise ValueError("Registry-Digest konnte nicht eindeutig ermittelt werden.")
    # Docker IDs can represent config, platform manifest or an OCI index.
    docker("pull", "--platform", "linux/amd64", matches[0])
    metadata = archived_image_metadata(directory / entry["archive"])
    if inspect_image(matches[0])["Id"] not in metadata["identities"]:
        raise ValueError("Registry-Image entspricht nicht dem gescannten Image.")
    return matches[0]


def publish(
    directory: Path, commit: str, repository: str, infrastructure: Path | None = None
) -> dict:
    validate_repository(repository)
    manifest = verify(directory, commit, infrastructure)
    configuration = manifest["infrastructure"]
    app_image = publish_archive(
        directory, manifest["images"]["app"], f"ghcr.io/{repository}/app", commit
    )
    released = {
        "commit": commit,
        "images": {
            "app": app_image,
            "nginx": configuration["nginx_image"],
            "db": configuration["postgres_image"],
        },
        "infrastructure": configuration,
        "database_contract": configuration["database_contract"],
    }
    (directory / "release.json").write_text(json.dumps(released, indent=2) + "\n")
    if "GITHUB_OUTPUT" in os.environ:
        with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
            output.write(f"app_image={app_image}\n")
    return released


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("build", "verify", "publish"))
    parser.add_argument("--directory", type=Path, default=Path("artifacts/images"))
    parser.add_argument("--infrastructure", type=Path)
    parser.add_argument("--commit", default=os.environ.get("GITHUB_SHA", ""))
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", "").lower())
    args = parser.parse_args()
    if not SHA.fullmatch(args.commit):
        parser.error("Ein vollständiger Commit-SHA ist erforderlich.")
    if args.operation == "build":
        build(args.directory, args.commit, args.infrastructure)
    elif args.operation == "verify":
        verify(args.directory, args.commit, args.infrastructure)
    else:
        publish(args.directory, args.commit, args.repository, args.infrastructure)
