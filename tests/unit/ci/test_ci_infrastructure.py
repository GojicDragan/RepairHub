"""Official infrastructure references must remain immutable and complete."""

import json

import pytest

from scripts.ci import images, infrastructure


@pytest.fixture
def configuration():
    return {
        "schema_version": 1,
        "nginx_image": "nginx:synthetic@sha256:" + "a" * 64,
        "postgres_image": "example/db@sha256:" + "b" * 64,
        "database_contract": "synthetic-contract",
        "postgres_version": "17.11",
    }


def test_missing_database_pin_blocks_normal_build_without_fallback(
    tmp_path, configuration, monkeypatch
):
    configuration["postgres_image"] = ""
    path = tmp_path / "infrastructure.json"
    path.write_text(json.dumps(configuration))
    monkeypatch.setattr(images, "docker", lambda *args: pytest.fail("No image may be built"))
    with pytest.raises(ValueError, match="festen Digest"):
        images.build(tmp_path / "artifacts", "a" * 40, path)
    assert not (tmp_path / "artifacts").exists()


@pytest.mark.parametrize("field", ["nginx_image", "postgres_image"])
@pytest.mark.parametrize(
    "reference", [None, "", "nginx:latest", "example/db:17.11", "bad@sha256:123"]
)
def test_mutable_or_invalid_image_references_are_rejected(
    tmp_path, configuration, field, reference
):
    configuration[field] = reference
    path = tmp_path / "infrastructure.json"
    path.write_text(json.dumps(configuration))
    with pytest.raises(ValueError):
        infrastructure.load(path)


def test_local_fixture_can_select_explicit_infrastructure_file(
    tmp_path, configuration, monkeypatch
):
    path = tmp_path / "infrastructure.json"
    path.write_text(json.dumps(configuration))
    monkeypatch.setenv("REPAIRHUB_INFRASTRUCTURE_FILE", str(path))
    assert infrastructure.load() == configuration


@pytest.mark.parametrize("version", [None, True, 0, 2, "1"])
def test_unknown_or_malformed_pin_schema_is_rejected(tmp_path, configuration, version):
    configuration["schema_version"] = version
    path = tmp_path / "infrastructure.json"
    path.write_text(json.dumps(configuration))
    with pytest.raises(ValueError, match="Infrastruktur-Konfiguration"):
        infrastructure.load(path)
