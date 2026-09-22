"""Garage-Quellinventar bleibt an den Digest gebunden und schliesst Testwurzeln aus."""

import json
from types import SimpleNamespace

import pytest

from scripts.ci import garage_inventory, security


def test_runtime_closure_keeps_build_optional_and_transitive_but_not_dev_roots():
    documents = {
        "Cargo.toml": (
            '[workspace]\nmembers=["garage"]\n[workspace.dependencies]\n'
            'alias={package="normal",version="1"}'
        ),
        "garage/Cargo.toml": (
            '[package]\nname="garage"\n[dependencies]\n'
            'alias={workspace=true}\noptional={version="1",optional=true}\n'
            '[build-dependencies]\nbuild="1"\n[dev-dependencies]\ntestonly="1"'
        ),
        "Cargo.lock": "\n".join(
            f'[[package]]\nname="{name}"\nversion="1.0.0"\ndependencies={json.dumps(deps)}'
            for name, deps in [
                ("garage", ["normal", "optional", "build", "testonly"]),
                ("normal", ["transitive"]),
                ("optional", []),
                ("build", []),
                ("testonly", []),
                ("transitive", []),
            ]
        ),
    }
    assert {p["name"] for p in garage_inventory.runtime_packages(documents)} == {
        "garage",
        "normal",
        "optional",
        "build",
        "transitive",
    }


def test_unapproved_image_cannot_use_source_inventory(tmp_path):
    with pytest.raises(ValueError, match="Image-Digest"):
        garage_inventory.prepare(tmp_path, "unapproved-image")


@pytest.mark.parametrize("result", [None, {}, {"Type": "cargo", "Packages": []}])
def test_source_inventory_requires_complete_cargo_packages(result):
    assert security.assess_report(
        "trivy-source",
        {
            "SchemaVersion": 2,
            "ArtifactType": "filesystem",
            "ArtifactName": "source",
            "Results": [result],
        },
    )


@pytest.mark.parametrize(
    "vulnerabilities,blocked",
    [([], False), ([{"Severity": "HIGH", "VulnerabilityID": "synthetic"}], True)],
)
def test_source_vulnerabilities_still_block(vulnerabilities, blocked):
    assert (
        security.assess_report(
            "trivy-source",
            {
                "SchemaVersion": 2,
                "ArtifactType": "filesystem",
                "ArtifactName": "source",
                "Results": [
                    {
                        "Target": "Cargo.lock",
                        "Class": "lang-pkgs",
                        "Type": "cargo",
                        "Packages": [{}] * 100,
                        "Vulnerabilities": vulnerabilities,
                    }
                ],
            },
        )
        is blocked
    )


@pytest.mark.parametrize(
    "image_id,source_passed,expected",
    [("wrong", True, False), ("pinned", False, False), ("pinned", True, True)],
)
def test_scratch_image_requires_matching_image_and_successful_source_scan(
    tmp_path, monkeypatch, image_id, source_passed, expected
):
    report = tmp_path / "image.json"

    def run(*args, **kwargs):
        report.write_text(
            json.dumps(
                {
                    "SchemaVersion": 2,
                    "ArtifactType": "container_image",
                    "ArtifactName": "garage",
                    "Metadata": {"ImageID": image_id, "Layers": ["layer"]},
                }
            )
        )
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(security.subprocess, "run", run)
    monkeypatch.setattr(
        garage_inventory,
        "prepare",
        lambda *args: {"source_commit": "commit", "runtime_package_count": 497},
    )
    monkeypatch.setattr(security, "run_scan", lambda *args, **kwargs: {"passed": source_passed})
    results = security.scan_garage(
        [],
        report,
        {"image_id": "pinned", "config_digest": "config", "source_reference": "source"},
        tmp_path,
        tmp_path,
    )
    assert results[-1]["passed"] is expected


def test_changed_source_manifest_blocks_inventory(tmp_path, monkeypatch):
    from io import BytesIO

    specification = tmp_path / "source.json"
    specification.write_text(
        json.dumps(
            {
                "image": "pinned",
                "commit": "a" * 40,
                "files": {"Cargo.toml": "0" * 64},
            }
        )
    )
    monkeypatch.setattr(garage_inventory, "SOURCE", specification)
    monkeypatch.setattr(
        garage_inventory.urllib.request, "urlopen", lambda *a, **k: BytesIO(b"changed")
    )
    with pytest.raises(ValueError, match="Quellmanifest"):
        garage_inventory.prepare(tmp_path / "inventory", "pinned")
    assert not (tmp_path / "inventory").exists()
