"""Aktiver ZAP-Scan ausschliesslich gegen die wegwerfbare CI-Anwendung."""

import argparse
import json
import os
import re
import subprocess
import tempfile
import uuid
from pathlib import Path

if __package__:
    from .images import SHA, docker, verify
    from .isolated_runtime import isolated_runtime
else:
    from images import SHA, docker, verify
    from isolated_runtime import isolated_runtime

# Offizielles Release mit eingebauten Add-ons; keine Updates während des Scans.
# https://www.zaproxy.org/docs/automate/automation-framework/
ZAP_VERSION = "2.17.0"
ZAP_IMAGE = (
    "ghcr.io/zaproxy/zaproxy:2.17.0@"
    "sha256:781a2bdaea47324e7bab583e2263f21d257b0aee61ed51521a5be45f5f5081ef"
)
TARGET = "https://nginx:8443"
SCAN_TIMEOUT_SECONDS = 1200
REQUIRED_PATHS = ("/", "/health/ready", "/static/app.css")


def automation_plan() -> dict:
    """Keine frei wählbare Ziel-URL: aktive Angriffe bleiben im eigenen Testnetz."""
    return {
        "env": {
            "contexts": [
                {
                    "name": "repairhub-ci",
                    "urls": [TARGET],
                    "includePaths": [r"https://nginx:8443/.*"],
                }
            ],
            "parameters": {
                "failOnError": True,
                "failOnWarning": True,
                "continueOnFailure": False,
                "progressToStdout": False,
            },
        },
        "jobs": [
            {
                "type": "passiveScan-config",
                "parameters": {"scanOnlyInScope": True},
            },
            {
                "type": "requestor",
                "requests": [
                    {"url": TARGET + path, "method": "GET", "responseCode": 200}
                    for path in REQUIRED_PATHS
                ],
            },
            {
                "type": "spider",
                "parameters": {"context": "repairhub-ci", "url": TARGET + "/", "maxDuration": 0},
                "tests": [
                    {
                        "type": "stats",
                        "statistic": "automation.spider.urls.added",
                        "operator": ">=",
                        "value": 1,
                        "onFail": "error",
                    }
                ],
            },
            {
                "type": "activeScan",
                "parameters": {
                    "context": "repairhub-ci",
                    "threadPerHost": 2,
                    "addQueryParam": True,
                    "scanHeadersAllRequests": True,
                    # Ein äusseres Timeout ist ein Fehler, kein verkürzter grüner Scan.
                    "maxScanDurationInMins": 0,
                    "maxRuleDurationInMins": 0,
                },
                "policyDefinition": {"defaultStrength": "Medium", "defaultThreshold": "Medium"},
                "tests": [
                    {
                        "type": "stats",
                        "statistic": statistic,
                        "operator": operator,
                        "value": value,
                        "onFail": "error",
                    }
                    for statistic, operator, value in (
                        ("stats.ascan.started", ">=", 1),
                        ("stats.ascan.urls", ">", 0),
                        ("stats.ascan.time", ">", 0),
                        ("stats.ascan.stopped", "==", 0),
                    )
                ],
            },
            {"type": "passiveScan-wait", "parameters": {"maxDuration": 0}},
            {
                "type": "report",
                "alwaysRun": True,
                "parameters": {
                    "template": "traditional-json",
                    "reportDir": "/zap/wrk",
                    "reportFile": "raw-report.json",
                    "displayReport": False,
                },
            },
        ],
    }


def assess_report(report: object, returncode: int) -> dict:
    """Nur geprüfte Metadaten veröffentlichen, keine Antworten, Tokens oder Payloads."""
    result = {"passed": False, "exit_code": returncode, "findings": []}
    if not isinstance(report, dict) or report.get("@version") != ZAP_VERSION:
        return {**result, "error_category": "invalid_report"}
    sites = report.get("site")
    if not isinstance(sites, list) or len(sites) != 1:
        return {**result, "error_category": "invalid_target_coverage"}
    site = sites[0]
    if (
        not isinstance(site, dict)
        or site.get("@name") != TARGET
        or site.get("@host") != "nginx"
        or str(site.get("@port")) != "8443"
        or str(site.get("@ssl")).lower() != "true"
        or not isinstance(site.get("alerts"), list)
    ):
        return {**result, "error_category": "invalid_target_coverage"}
    findings = []
    for alert in site["alerts"]:
        if (
            not isinstance(alert, dict)
            or not re.fullmatch(r"[0-9]{1,8}", str(alert.get("pluginid", "")))
            or str(alert.get("riskcode")) not in {"0", "1", "2", "3"}
            or str(alert.get("confidence")) not in {"0", "1", "2", "3", "4"}
            or not isinstance(alert.get("instances"), list)
            or not alert["instances"]
            or any(
                not isinstance(instance, dict)
                or not isinstance(instance.get("uri"), str)
                or not (instance["uri"] == TARGET or instance["uri"].startswith(TARGET + "/"))
                or not re.fullmatch(r"[A-Z]{1,20}", str(instance.get("method", "")))
                for instance in alert.get("instances", [])
            )
        ):
            return {**result, "error_category": "invalid_report"}
        findings.append(
            {
                "rule_id": int(alert["pluginid"]),
                "risk": int(alert["riskcode"]),
                "confidence": int(alert["confidence"]),
                "instances": len(alert["instances"]),
            }
        )
    blocked = any(finding["risk"] >= 2 for finding in findings)
    category = "scanner_failed" if returncode else "blocking_findings" if blocked else None
    return {
        **result,
        "passed": returncode == 0 and not blocked,
        "findings": findings,
        "error_category": category,
    }


def scan(network: str) -> dict:
    name = "repairhub-zap-" + uuid.uuid4().hex[:12]
    with tempfile.TemporaryDirectory(prefix="repairhub-zap-") as temporary:
        directory = Path(temporary)
        # JSON ist gültiges YAML und hält diesen Runner frei von weiteren Paketen.
        (directory / "plan.yaml").write_text(json.dumps(automation_plan()))
        command = [
            "docker",
            "run",
            "--name",
            name,
            "--network",
            network,
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges:true",
            "--memory=2g",
            "--cpus=2",
            "--read-only",
            "--mount",
            "type=tmpfs,dst=/tmp,tmpfs-mode=1777,tmpfs-size=536870912",
            "--mount",
            f"type=bind,src={directory},dst=/zap/wrk",
            "--env",
            "_JAVA_OPTIONS=-Djava.util.prefs.userRoot=/zap/wrk/prefs",
            ZAP_IMAGE,
            "zap.sh",
            "-Xmx1024m",
            "-cmd",
            "-dir",
            "/zap/wrk/home",
            "-config",
            "start.checkForUpdates=false",
            "-config",
            "start.checkAddonUpdates=false",
            "-config",
            "start.installAddonUpdates=false",
            "-config",
            "start.installScannerRules=false",
            "-config",
            "start.downloadNewRelease=false",
            "-autorun",
            "/zap/wrk/plan.yaml",
        ]
        try:
            completed = subprocess.run(
                command, capture_output=True, timeout=SCAN_TIMEOUT_SECONDS, check=False
            )
            report = json.loads((directory / "raw-report.json").read_text())
            return assess_report(report, completed.returncode)
        except subprocess.TimeoutExpired:
            return {"passed": False, "findings": [], "error_category": "scanner_timeout"}
        except (OSError, ValueError):
            return {"passed": False, "findings": [], "error_category": "invalid_or_missing_report"}
        finally:
            # Weder rohe Scannerlogs noch HTTP-Antworten gelangen ins Artefakt.
            cleanup = subprocess.run(
                ["docker", "rm", "--force", name], capture_output=True, check=False, timeout=15
            )
            if cleanup.returncode:
                raise RuntimeError("ZAP-Testcontainer konnte nicht entfernt werden.")


def main(artifacts: Path, reports: Path, commit: str) -> int:
    reports.mkdir(parents=True, exist_ok=True)
    summary = {
        "commit": commit,
        "scanner": "ZAP",
        "version": ZAP_VERSION,
        "image": ZAP_IMAGE,
        "target": TARGET,
        "mode": "active",
        "passed": False,
    }
    try:
        manifest = verify(artifacts, commit)
        summary["images"] = manifest["images"]
        docker("pull", ZAP_IMAGE, capture=True)
        with isolated_runtime(manifest) as runtime:
            summary.update(scan(runtime.network))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        summary.update(passed=False, error_category="scan_setup_or_cleanup_failed")
    finally:
        (reports / "zap.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"ZAP DAST: {'bestanden' if summary['passed'] else 'blockiert'}")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts/images"))
    parser.add_argument("--reports", type=Path, default=Path("reports/security"))
    parser.add_argument("--commit", default=os.environ.get("GITHUB_SHA", ""))
    args = parser.parse_args()
    if not SHA.fullmatch(args.commit):
        parser.error("Ein vollständiger Commit-SHA ist erforderlich.")
    raise SystemExit(main(args.artifacts, args.reports, args.commit))
