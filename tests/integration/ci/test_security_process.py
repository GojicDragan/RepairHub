"""Scannerprüfungen scheitern bei echten Prozessfehlern und synthetischen Sperrbefunden."""

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file()
)
SCRIPT = ROOT / "scripts" / "ci" / "security.py"
spec = importlib.util.spec_from_file_location("security_gate", SCRIPT)
security = importlib.util.module_from_spec(spec)
spec.loader.exec_module(security)

CLEAN = {
    "pip-audit": {"dependencies": [{"name": "synthetic", "version": "1", "vulns": []}]},
    "bandit": {"results": [], "errors": [], "metrics": {"_totals": {"loc": 1}}},
    "gitleaks": [],
    "trivy": {
        "SchemaVersion": 2,
        "ArtifactType": "container_image",
        "ArtifactName": "synthetic",
        "Results": [
            {"Target": "synthetic", "Class": "os-pkgs", "Type": "alpine", "Vulnerabilities": []}
        ],
    },
}
BLOCKING = copy.deepcopy(CLEAN)
BLOCKING["pip-audit"]["dependencies"][0]["vulns"] = [{"id": "TEST-0001"}]
BLOCKING["bandit"]["results"] = [
    {
        "issue_severity": "HIGH",
        "issue_confidence": "HIGH",
        "test_id": "B000",
        "filename": "synthetic.py",
    }
]
BLOCKING["gitleaks"] = [{"RuleID": "synthetic-finding", "File": "synthetic.txt", "StartLine": 1}]
BLOCKING["trivy"]["Results"][0]["Vulnerabilities"] = [
    {"Severity": "CRITICAL", "VulnerabilityID": "TEST-0001"}
]


def fake_command(path, payload, exit_code):
    return [
        sys.executable,
        "-c",
        "import json,sys; from pathlib import Path; "
        "Path(sys.argv[1]).write_text(sys.argv[2]); sys.exit(int(sys.argv[3]))",
        str(path),
        json.dumps(payload),
        str(exit_code),
    ]


@pytest.mark.parametrize("kind", CLEAN)
def test_clean_scanner_process_passes(kind, tmp_path):
    report = tmp_path / f"{kind}.json"
    assert security.run_scan(kind, fake_command(report, CLEAN[kind], 0), report)["passed"]


@pytest.mark.parametrize("kind", CLEAN)
@pytest.mark.parametrize("returncode", [1, 2, 127])
def test_scanner_error_with_clean_report_still_blocks(kind, returncode, tmp_path):
    report = tmp_path / f"{kind}.json"
    assert not security.run_scan(kind, fake_command(report, CLEAN[kind], returncode), report)[
        "passed"
    ]


@pytest.mark.parametrize("kind", BLOCKING)
def test_blocking_finding_even_with_zero_exit_blocks(kind, tmp_path):
    report = tmp_path / f"{kind}.json"
    assert not security.run_scan(kind, fake_command(report, BLOCKING[kind], 0), report)["passed"]


@pytest.mark.parametrize("kind", CLEAN)
def test_missing_or_malformed_report_blocks(kind, tmp_path):
    report = tmp_path / f"{kind}.json"
    assert not security.run_scan(kind, [sys.executable, "-c", "pass"], report)["passed"]
    assert not security.run_scan(kind, fake_command(report, "invalid", 0), report)["passed"]


def test_unavailable_scanner_blocks(tmp_path):
    report = tmp_path / "absent.json"
    assert not security.run_scan("gitleaks", [str(tmp_path / "missing-binary")], report)["passed"]


@pytest.mark.parametrize(
    ("kind", "report"),
    [
        ("bandit", {"results": [{}], "errors": [], "metrics": {"_totals": {"loc": 1}}}),
        ("bandit", {"results": [], "errors": []}),
        (
            "trivy",
            {
                "SchemaVersion": 2,
                "ArtifactType": "container_image",
                "ArtifactName": "synthetic",
                "Results": [{}],
            },
        ),
        ("pip-audit", {"dependencies": [{"vulns": []}]}),
    ],
)
def test_incomplete_report_shapes_block(kind, report, tmp_path):
    output = tmp_path / f"{kind}.json"
    assert not security.run_scan(kind, fake_command(output, report, 0), output)["passed"]


def suppressed_gosu_report():
    report = copy.deepcopy(CLEAN["trivy"])
    report["Results"][0] = {
        "Target": "usr/local/bin/gosu",
        "Class": "lang-pkgs",
        "Type": "gobinary",
        "ExperimentalModifiedFindings": [
            {
                "Type": "vulnerability",
                "Status": "ignored",
                "Source": str(security.POSTGRES_GOSU_EXCEPTIONS),
                "Statement": "Explicit temporary acceptance for the practice project.",
                "Finding": {
                    "VulnerabilityID": "CVE-2025-68121",
                    "Severity": "CRITICAL",
                    "PkgName": "stdlib",
                    "InstalledVersion": "v1.24.6",
                    "PkgIdentifier": {"PURL": "pkg:golang/stdlib@v1.24.6"},
                },
            }
        ],
    }
    return report


def test_native_exception_is_retained_and_summarized(tmp_path):
    report = tmp_path / "trivy-db.json"
    payload = suppressed_gosu_report()
    result = security.run_scan(
        "trivy",
        fake_command(report, payload, 0),
        report,
        trivy_ignorefile=security.POSTGRES_GOSU_EXCEPTIONS,
    )
    assert result["passed"]
    assert result["suppressed_vulnerability_ids"] == ["CVE-2025-68121"]
    assert result["suppressed_vulnerability_count"] == 1
    assert json.loads(report.read_text()) == payload


@pytest.mark.parametrize("exit_code", [1, 2, 127])
def test_scanner_failure_still_blocks_with_accepted_findings(tmp_path, exit_code):
    report = tmp_path / "trivy-db.json"
    assert not security.run_scan(
        "trivy",
        fake_command(report, suppressed_gosu_report(), exit_code),
        report,
        trivy_ignorefile=security.POSTGRES_GOSU_EXCEPTIONS,
    )["passed"]


def test_suppressed_findings_without_explicit_exception_block(tmp_path):
    report = tmp_path / "trivy-app.json"
    assert not security.run_scan(
        "trivy", fake_command(report, suppressed_gosu_report(), 0), report
    )["passed"]


def test_new_unaccepted_finding_blocks_despite_accepted_gosu_findings(tmp_path):
    payload = suppressed_gosu_report()
    payload["Results"][0]["Vulnerabilities"] = [
        {"VulnerabilityID": "CVE-2099-99999", "Severity": "HIGH"}
    ]
    report = tmp_path / "trivy-db.json"
    assert not security.run_scan(
        "trivy",
        fake_command(report, payload, 0),
        report,
        trivy_ignorefile=security.POSTGRES_GOSU_EXCEPTIONS,
    )["passed"]


@pytest.mark.parametrize("change", ["path", "purl", "version", "source", "missing_purl"])
def test_out_of_scope_suppression_blocks(tmp_path, change):
    payload = suppressed_gosu_report()
    result = payload["Results"][0]
    modified = result["ExperimentalModifiedFindings"][0]
    finding = modified["Finding"]
    if change == "path":
        result["Target"] = "usr/local/bin/another-program"
    elif change == "purl":
        finding["PkgIdentifier"]["PURL"] = "pkg:golang/stdlib@v1.25.0"
    elif change == "version":
        finding["InstalledVersion"] = "v1.25.0"
    elif change == "source":
        modified["Source"] = "/tmp/unapproved-ignorefile.yaml"
    else:
        finding["PkgIdentifier"] = None
    report = tmp_path / "trivy-db.json"
    assert not security.run_scan(
        "trivy",
        fake_command(report, payload, 0),
        report,
        trivy_ignorefile=security.POSTGRES_GOSU_EXCEPTIONS,
    )["passed"]
