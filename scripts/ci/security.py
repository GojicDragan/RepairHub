"""Alle Pflichtscanner ausführen; bereinigte Berichte speichern und bei Fehlern sperren."""

import argparse
import json
import os
import subprocess
from pathlib import Path

POSTGRES_GOSU_IMAGE = (
    "postgres:17.11-alpine3.24@sha256:"
    "f02121de6f74d30d8a94cd1d9584125e2178d7e6c377d8130112d4e52d867995"
)
POSTGRES_GOSU_EXCEPTIONS = (
    Path(__file__).resolve().parents[2] / "deploy/security/postgres-gosu.trivyignore.yaml"
)


def assess_report(kind: str, report: object, *, ignored_source: str | None = None) -> bool:
    """True sperrt die Freigabe bei Befunden oder unvollständigen/ungültigen Berichten."""
    if kind == "pip-audit":
        if not isinstance(report, dict) or not isinstance(report.get("dependencies"), list):
            return True
        dependencies = report["dependencies"]
        return not dependencies or any(
            not isinstance(item, dict)
            or not isinstance(item.get("name"), str)
            or not item["name"]
            or not isinstance(item.get("version"), str)
            or not item["version"]
            or "skip_reason" in item
            or not isinstance(item.get("vulns"), list)
            or bool(item["vulns"])
            for item in dependencies
        )
    if kind == "bandit":
        if not isinstance(report, dict) or not isinstance(report.get("results"), list):
            return True
        if not isinstance(report.get("errors"), list) or report["errors"]:
            return True
        metrics = report.get("metrics", {})
        if not isinstance(metrics, dict) or not isinstance(metrics.get("_totals"), dict):
            return True
        loc = metrics["_totals"].get("loc")
        if not isinstance(loc, int) or loc <= 0:
            return True
        levels = {"LOW", "MEDIUM", "HIGH"}
        for item in report["results"]:
            if not isinstance(item, dict):
                return True
            if (
                item.get("issue_severity") not in levels
                or item.get("issue_confidence") not in levels
            ):
                return True
            if not item.get("test_id") or not item.get("filename"):
                return True
            if item["issue_severity"] in {"MEDIUM", "HIGH"} and item["issue_confidence"] in {
                "MEDIUM",
                "HIGH",
            }:
                return True
        return False
    if kind == "gitleaks":
        return not isinstance(report, list) or bool(report)
    if kind in {"trivy", "trivy-source"}:
        if not isinstance(report, dict) or report.get("SchemaVersion") != 2:
            return True
        expected_type = "filesystem" if kind == "trivy-source" else "container_image"
        if report.get("ArtifactType") != expected_type or not report.get("ArtifactName"):
            return True
        if not isinstance(report.get("Results"), list) or not report["Results"]:
            return True
        if kind == "trivy-source" and any(
            not isinstance(r, dict)
            or r.get("Type") != "cargo"
            or not isinstance(r.get("Packages"), list)
            or len(r["Packages"]) < 100
            for r in report["Results"]
        ):
            return True
        levels = {"UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL"}
        for result in report["Results"]:
            if (
                not isinstance(result, dict)
                or not result.get("Target")
                or result.get("Class") not in {"os-pkgs", "lang-pkgs"}
                or not result.get("Type")
            ):
                return True
            modified = result.get("ExperimentalModifiedFindings", [])
            if not isinstance(modified, list):
                return True
            for item in modified:
                # Trivy prüft CVE, Pfad, PURL und Ablaufdatum. Nur ausdrücklich
                # ausgewiesene Ausnahmen akzeptieren, keine fremden Unterdrückungen.
                if (
                    ignored_source is None
                    or not isinstance(item, dict)
                    or item.get("Type") != "vulnerability"
                    or item.get("Status") != "ignored"
                    or item.get("Source") != ignored_source
                    or not item.get("Statement")
                    or result["Target"] != "usr/local/bin/gosu"
                ):
                    return True
                finding = item.get("Finding")
                if (
                    not isinstance(finding, dict)
                    or finding.get("Severity") not in levels
                    or not finding.get("VulnerabilityID")
                    or finding.get("PkgName") != "stdlib"
                    or finding.get("InstalledVersion") != "v1.24.6"
                    or not isinstance(finding.get("PkgIdentifier"), dict)
                    or finding.get("PkgIdentifier", {}).get("PURL") != "pkg:golang/stdlib@v1.24.6"
                ):
                    return True
            vulnerabilities = result.get("Vulnerabilities", [])
            if vulnerabilities is None:
                vulnerabilities = []
            if not isinstance(vulnerabilities, list):
                return True
            for item in vulnerabilities:
                if (
                    not isinstance(item, dict)
                    or item.get("Severity") not in levels
                    or not item.get("VulnerabilityID")
                ):
                    return True
                if item["Severity"] in {"HIGH", "CRITICAL"}:
                    return True
        return False
    raise ValueError(f"Unbekannter Scanner: {kind}")


def redact_report(kind: str, report: object) -> object:
    if kind == "gitleaks" and isinstance(report, list):
        # Keine Fundtexte, Codeausschnitte, Geheimnisse oder Autorenadressen in Artefakten.
        fields = ("RuleID", "File", "StartLine", "EndLine", "Fingerprint", "Commit")
        return [{key: finding.get(key) for key in fields} for finding in report]
    if kind == "bandit" and isinstance(report, dict):
        for finding in report.get("results", []):
            finding.pop("code", None)
            finding.pop("issue_text", None)
    return report


def error_category(stderr: str, returncode: int) -> str:
    """Nützliche Fehlerkategorien erhalten, ohne vom Scanner gelieferte Quelltexte auszugeben."""
    message = stderr.lower()
    if returncode == 127:
        return "scanner_unavailable"
    for category, fragments in (
        ("scanner_timeout", ("timeout", "deadline exceeded", "timed out")),
        ("database_download_failed", ("download", "failed to fetch", "unexpected status code")),
        ("scanner_cache_locked", ("database is locked", "cache lock", "locked by")),
        ("permission_denied", ("permission denied", "access denied")),
        ("invalid_scanner_input", ("unknown flag", "unrecognized arguments", "no such file")),
    ):
        if any(fragment in message for fragment in fragments):
            return category
    return "scanner_failed" if returncode else "invalid_or_missing_report"


def run_scan(
    kind: str,
    command: list[str],
    report_path: Path,
    *,
    trivy_ignorefile: Path | None = None,
) -> dict:
    """Ein Prozessfehler darf niemals als erfolgreicher Scan ohne Befunde gelten."""
    # Ein fehlgeschlagener Neustart darf keinen alten grünen Bericht wiederverwenden.
    report_path.unlink(missing_ok=True)
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
        )
        returncode = result.returncode
        category = error_category(result.stderr, returncode)
    except OSError:
        returncode = 127
        category = "scanner_unavailable"
    suppressed_ids: list[str] = []
    try:
        report = json.loads(report_path.read_text())
        blocked = assess_report(
            kind, report, ignored_source=str(trivy_ignorefile) if trivy_ignorefile else None
        )
        if kind == "trivy":
            suppressed_ids = sorted(
                {
                    item["Finding"]["VulnerabilityID"]
                    for result in report["Results"]
                    for item in result.get("ExperimentalModifiedFindings", [])
                }
            )
        report_path.write_text(json.dumps(redact_report(kind, report), indent=2) + "\n")
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        blocked = True
        report_path.write_text(
            json.dumps(
                {
                    "error": "Kein gültiger Scannerbericht.",
                    "category": category,
                    "exit_code": returncode,
                }
            )
            + "\n"
        )
    passed = returncode == 0 and not blocked
    print(f"{report_path.stem}: {'bestanden' if passed else 'blockiert'} (Exit {returncode})")
    summary = {
        "scanner": kind,
        "report": report_path.name,
        "exit_code": returncode,
        "passed": passed,
        "error_category": None if passed else category,
    }
    if kind == "trivy":
        summary["suppressed_vulnerability_ids"] = suppressed_ids
        summary["suppressed_vulnerability_count"] = len(suppressed_ids)
        summary["exception_file"] = str(trivy_ignorefile) if trivy_ignorefile else None
    return summary


def source_scans(reports: Path, binary_dir: Path) -> list[dict]:
    """Gemeinsame Prüfungen für gesperrte Abhängigkeiten, Python-Code und Geheimnisse."""
    reports.mkdir(parents=True, exist_ok=True)
    scans = []
    requirements = reports / "requirements-audit.txt"
    subprocess.run(
        [
            "uv",
            "export",
            "--locked",
            "--all-groups",
            "--no-emit-project",
            "--output-file",
            str(requirements),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    definitions = [
        (
            "pip-audit",
            [
                "pip-audit",
                "--require-hashes",
                "--disable-pip",
                "--no-deps",
                "-r",
                str(requirements),
                "-f",
                "json",
                "-o",
            ],
            "dependencies.json",
        ),
        (
            "bandit",
            [
                "bandit",
                "-r",
                "app",
                "scripts",
                "deploy/ansible/roles/docker_host/files",
                "--severity-level",
                "medium",
                "--confidence-level",
                "medium",
                "-f",
                "json",
                "-o",
            ],
            "bandit.json",
        ),
        (
            "gitleaks",
            [
                str(binary_dir / "gitleaks"),
                "git",
                ".",
                "--log-opts=--all",
                "--redact=100",
                "--no-banner",
                "--report-format=json",
                "--report-path",
            ],
            "gitleaks.json",
        ),
    ]
    for kind, command, filename in definitions:
        path = reports / filename
        scans.append(run_scan(kind, [*command, str(path)], path))
    return scans


def scan_garage(command, report_path, entry, reports, binary_dir):
    """Scratch-Image und verifizierte Rust-Laufzeitabhängigkeiten gemeinsam verlangen."""
    if __package__:
        from .garage_inventory import prepare
    else:
        from garage_inventory import prepare

    report_path.unlink(missing_ok=True)
    result = {
        "scanner": "trivy",
        "report": report_path.name,
        "passed": False,
        "coverage": "pinned scratch image plus verified upstream runtime lockfile",
    }
    scans = []
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        result["exit_code"] = completed.returncode
        report = json.loads(report_path.read_text())
        metadata = report.get("Metadata", {})
        if (
            completed.returncode != 0
            or report.get("SchemaVersion") != 2
            or report.get("ArtifactType") != "container_image"
            or not report.get("ArtifactName")
            or metadata.get("ImageID") not in {entry["image_id"], entry["config_digest"]}
        ):
            raise ValueError("Garage-Imageprüfung unvollständig.")
        if report.get("Results"):
            if assess_report("trivy", report):
                raise ValueError("Garage-Imageprüfung blockiert.")
        elif metadata.get("OS") or not metadata.get("Layers"):
            raise ValueError("Fehlendes Inventar ausserhalb des geprüften Scratch-Images.")
        # Fehlende Binary-Metadaten allein gelten nicht als bestanden. Erst das an
        # genau diesen Image-Digest gebundene Quellinventar vervollständigt die Prüfung.
        source_dir = reports / "garage-source"
        evidence = prepare(source_dir, entry["source_reference"])
        source_report = reports / "trivy-garage-source.json"
        source = run_scan(
            "trivy-source",
            [
                str(binary_dir / "trivy"),
                "fs",
                "--scanners",
                "vuln",
                "--severity",
                "HIGH,CRITICAL",
                "--exit-code",
                "1",
                "--format",
                "json",
                "--list-all-pkgs",
                "--ignorefile",
                os.devnull,
                "--output",
                str(source_report),
                "--timeout",
                "15m",
                "--no-progress",
                str(source_dir),
            ],
            source_report,
        )
        scans.append(source)
        result["source_commit"] = evidence["source_commit"]
        result["runtime_package_count"] = evidence["runtime_package_count"]
        result["passed"] = source["passed"]
        result["error_category"] = None if source["passed"] else "source_dependencies_blocked"
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        result["error_category"] = "garage_image_or_source_inventory_invalid"
    print(f"trivy-garage: {'bestanden' if result['passed'] else 'blockiert'}")
    return [*scans, result]


def main(artifact_dir: Path, reports: Path, binary_dir: Path) -> int:
    scans = source_scans(reports, binary_dir)
    manifest = json.loads((artifact_dir / "manifest.json").read_text())
    for name, entry in manifest["images"].items():
        path = reports / f"trivy-{name}.json"
        ignorefile = (
            POSTGRES_GOSU_EXCEPTIONS
            if name == "db" and entry.get("source_reference") == POSTGRES_GOSU_IMAGE
            else None
        )
        command = [
            str(binary_dir / "trivy"),
            "image",
            "--input",
            str(artifact_dir / entry["archive"]),
            "--scanners",
            "vuln",
            "--severity",
            "HIGH,CRITICAL",
            "--exit-code",
            "1",
            "--format",
            "json",
            "--show-suppressed",
            "--ignorefile",
            str(ignorefile) if ignorefile else os.devnull,
            "--output",
            str(path),
            "--timeout",
            "15m",
            "--no-progress",
        ]
        if name == "garage":
            scans.extend(scan_garage(command, path, entry, reports, binary_dir))
        else:
            scans.append(run_scan("trivy", command, path, trivy_ignorefile=ignorefile))
    summary = {"commit": manifest["commit"], "images": manifest["images"], "scans": scans}
    (reports / "security-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return 0 if all(item["passed"] for item in scans) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts/images"))
    parser.add_argument("--reports", type=Path, default=Path("reports/security"))
    parser.add_argument(
        "--binaries",
        type=Path,
        default=Path(os.environ.get("RUNNER_TEMP", ".qa")) / "repairhub-scanners",
    )
    args = parser.parse_args()
    raise SystemExit(main(args.artifacts, args.reports, args.binaries))
