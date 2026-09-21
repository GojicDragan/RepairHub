"""DAST must fail closed and retain only safe report metadata."""

import copy
import json
import subprocess
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.ci import dast

COMMIT = "a" * 40
SYNTHETIC_SECRET = "synthetic-response-secret-placeholder"
MISSING = object()


@pytest.fixture
def clean_report():
    return {
        "@version": dast.ZAP_VERSION,
        "site": [
            {
                "@name": dast.TARGET,
                "@host": "nginx",
                "@port": "8443",
                "@ssl": "true",
                "alerts": [],
            }
        ],
    }


@pytest.fixture
def alert_report(clean_report):
    clean_report["site"][0]["alerts"] = [
        {
            "pluginid": "10021",
            "riskcode": "1",
            "confidence": "2",
            "instances": [{"uri": dast.TARGET + "/", "method": "GET"}],
        }
    ]
    return clean_report


@pytest.mark.parametrize("report", [None, [], "not a report", {}, 42, True])
def test_malformed_top_level_report_blocks(report):
    result = dast.assess_report(report, 0)
    assert result["passed"] is False
    assert result["error_category"] == "invalid_report"


@pytest.mark.parametrize("version", [MISSING, None, "2.16.1", "", 217])
def test_unexpected_or_missing_scanner_version_blocks(clean_report, version):
    if version is MISSING:
        del clean_report["@version"]
    else:
        clean_report["@version"] = version
    assert dast.assess_report(clean_report, 0)["passed"] is False


@pytest.mark.parametrize("sites", [MISSING, None, {}, [], [None], [{}, {}]])
def test_missing_or_ambiguous_target_coverage_blocks(clean_report, sites):
    if sites is MISSING:
        del clean_report["site"]
    else:
        clean_report["site"] = sites
    result = dast.assess_report(clean_report, 0)
    assert result["passed"] is False
    assert result["error_category"] == "invalid_target_coverage"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("@name", "https://production.invalid"),
        ("@name", dast.TARGET + "/other"),
        ("@name", "http://nginx:8443"),
        ("@host", "another-container"),
        ("@port", "443"),
        ("@ssl", "false"),
        ("alerts", None),
        ("alerts", {}),
        ("alerts", "no alerts"),
        ("@name", MISSING),
        ("@host", MISSING),
        ("@port", MISSING),
        ("@ssl", MISSING),
        ("alerts", MISSING),
    ],
)
def test_untrusted_target_fields_cannot_supply_a_green_report(clean_report, field, value):
    if value is MISSING:
        del clean_report["site"][0][field]
    else:
        clean_report["site"][0][field] = value
    assert dast.assess_report(clean_report, 0)["passed"] is False


@pytest.mark.parametrize("alert", [None, [], "invalid", 42, {}])
def test_malformed_alert_blocks_even_when_scanner_exits_successfully(clean_report, alert):
    clean_report["site"][0]["alerts"] = [alert]
    result = dast.assess_report(clean_report, 0)
    assert result["passed"] is False
    assert result["error_category"] == "invalid_report"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("pluginid", MISSING),
        ("pluginid", None),
        ("pluginid", ""),
        ("pluginid", "-1"),
        ("pluginid", "100000000"),
        ("pluginid", "1e5"),
        ("pluginid", SYNTHETIC_SECRET),
        ("pluginid", True),
        ("riskcode", MISSING),
        ("riskcode", None),
        ("riskcode", -1),
        ("riskcode", "4"),
        ("riskcode", "Medium"),
        ("riskcode", 1.5),
        ("riskcode", True),
        ("confidence", MISSING),
        ("confidence", None),
        ("confidence", -1),
        ("confidence", "5"),
        ("confidence", "High"),
        ("confidence", True),
        ("instances", MISSING),
        ("instances", None),
        ("instances", []),
        ("instances", {}),
    ],
)
def test_invalid_finding_metadata_blocks_and_is_not_echoed(alert_report, field, value):
    alert = alert_report["site"][0]["alerts"][0]
    if value is MISSING:
        del alert[field]
    else:
        alert[field] = value
    result = dast.assess_report(alert_report, 0)
    assert result["passed"] is False
    assert result["error_category"] == "invalid_report"
    assert SYNTHETIC_SECRET not in json.dumps(result)


@pytest.mark.parametrize(
    "instance",
    [
        None,
        "malformed instance",
        {},
        {"uri": dast.TARGET + "/"},
        {"method": "GET"},
        {"uri": None, "method": "GET"},
        {"uri": 42, "method": "GET"},
        {"uri": "https://production.invalid/", "method": "GET"},
        {"uri": dast.TARGET + ".outside.invalid/", "method": "GET"},
        {"uri": "http://nginx:8443/", "method": "GET"},
        {"uri": dast.TARGET + "/", "method": None},
        {"uri": dast.TARGET + "/", "method": 42},
        {"uri": dast.TARGET + "/", "method": ""},
        {"uri": dast.TARGET + "/", "method": "get"},
        {"uri": dast.TARGET + "/", "method": "GET "},
        {"uri": dast.TARGET + "/", "method": "A" * 21},
        {"uri": SYNTHETIC_SECRET, "method": "GET"},
    ],
)
def test_malformed_or_out_of_scope_alert_instances_block(alert_report, instance):
    alert_report["site"][0]["alerts"][0]["instances"] = [instance]
    result = dast.assess_report(alert_report, 0)
    assert result["passed"] is False
    assert result["error_category"] == "invalid_report"
    assert SYNTHETIC_SECRET not in json.dumps(result)


@pytest.mark.parametrize("uri", [dast.TARGET, dast.TARGET + "/health/ready"])
def test_exact_target_and_its_paths_are_valid_alert_instances(alert_report, uri):
    alert_report["site"][0]["alerts"][0]["instances"] = [{"uri": uri, "method": "GET"}]
    assert dast.assess_report(alert_report, 0)["passed"] is True


@pytest.mark.parametrize("risk", [2, 3])
@pytest.mark.parametrize("confidence", range(5))
def test_medium_and_high_findings_block_for_every_confidence(alert_report, risk, confidence):
    alert_report["site"][0]["alerts"][0].update(riskcode=risk, confidence=confidence)
    result = dast.assess_report(alert_report, 0)
    assert result["passed"] is False
    assert result["error_category"] == "blocking_findings"
    assert result["findings"][0]["risk"] == risk


@pytest.mark.parametrize("risk", [0, 1])
def test_low_and_informational_findings_pass_with_safe_numeric_metadata(alert_report, risk):
    alert_report["site"][0]["alerts"][0]["riskcode"] = str(risk)
    result = dast.assess_report(alert_report, 0)
    assert result["passed"] is True
    assert result["findings"] == [{"rule_id": 10021, "risk": risk, "confidence": 2, "instances": 1}]


@pytest.mark.parametrize("returncode", [1, 2, 127, -9])
def test_scanner_failure_blocks_even_with_a_clean_report(clean_report, returncode):
    result = dast.assess_report(clean_report, returncode)
    assert result["passed"] is False
    assert result["error_category"] == "scanner_failed"
    assert result["exit_code"] == returncode


def test_evidence_response_bodies_and_request_uris_are_not_published(alert_report):
    uri = dast.TARGET + "/?token=" + SYNTHETIC_SECRET
    alert = alert_report["site"][0]["alerts"][0]
    alert.update(name=SYNTHETIC_SECRET, desc=SYNTHETIC_SECRET, solution=SYNTHETIC_SECRET)
    alert["instances"] = [
        {
            "uri": uri,
            "method": "GET",
            "evidence": SYNTHETIC_SECRET,
            "attack": SYNTHETIC_SECRET,
            "request-header": "Authorization: Bearer " + SYNTHETIC_SECRET,
            "response-body": SYNTHETIC_SECRET,
        }
    ]
    alert_report["untrusted-diagnostic"] = SYNTHETIC_SECRET
    original = copy.deepcopy(alert_report)
    result = dast.assess_report(alert_report, 0)
    assert result["passed"] is True
    assert SYNTHETIC_SECRET not in json.dumps(result)
    assert uri not in json.dumps(result)
    assert set(result["findings"][0]) == {"rule_id", "risk", "confidence", "instances"}
    assert alert_report == original


@pytest.fixture
def fake_scanner(monkeypatch, clean_report):
    """Simulate scanner I/O without starting Docker or making HTTP requests."""
    calls = []
    state = {
        "report": clean_report,
        "returncode": 0,
        "exception": None,
        "raw": None,
        "cleanup_returncode": 0,
        "cleanup_exception": None,
    }

    def run(command, **kwargs):
        calls.append((command, kwargs))
        if command[:2] == ["docker", "rm"]:
            if state["cleanup_exception"]:
                raise state["cleanup_exception"]
            return subprocess.CompletedProcess(
                command, state["cleanup_returncode"], b"", SYNTHETIC_SECRET.encode()
            )
        assert command[:2] == ["docker", "run"]
        mounts = [
            dict(field.split("=", 1) for field in command[index + 1].split(","))
            for index, argument in enumerate(command)
            if argument == "--mount"
        ]
        workspace = next(
            mount for mount in mounts if mount["type"] == "bind" and mount["dst"] == "/zap/wrk"
        )
        directory = Path(workspace["src"])
        state["directory"] = directory
        state["plan"] = json.loads((directory / "plan.yaml").read_text())
        if state["exception"]:
            raise state["exception"]
        if state["raw"] is not None:
            (directory / "raw-report.json").write_text(state["raw"])
        elif state["report"] is not None:
            (directory / "raw-report.json").write_text(json.dumps(state["report"]))
        return subprocess.CompletedProcess(
            command, state["returncode"], SYNTHETIC_SECRET.encode(), SYNTHETIC_SECRET.encode()
        )

    monkeypatch.setattr(dast.subprocess, "run", run)
    return state, calls


def assert_scanner_was_cleaned_up(state, calls):
    launch = calls[0][0]
    name = launch[launch.index("--name") + 1]
    assert calls[-1][0] == ["docker", "rm", "--force", name]
    assert not state["directory"].exists()


def test_scan_uses_only_the_isolated_network_and_cleans_up_after_success(fake_scanner):
    state, calls = fake_scanner
    result = dast.scan("synthetic-private-network")
    assert result["passed"] is True
    command, arguments = calls[0]
    assert command[command.index("--network") + 1] == "synthetic-private-network"
    assert dast.ZAP_IMAGE in command
    assert "--privileged" not in command
    assert "--publish" not in command
    assert arguments["timeout"] == dast.SCAN_TIMEOUT_SECONDS
    assert arguments["capture_output"] is True
    assert state["plan"]["env"]["contexts"][0]["urls"] == [dast.TARGET]
    assert SYNTHETIC_SECRET not in json.dumps(result)
    assert_scanner_was_cleaned_up(state, calls)


@pytest.mark.parametrize("returncode", [1, 2, 127])
def test_scan_process_failure_cannot_be_hidden_by_clean_json(fake_scanner, returncode):
    state, calls = fake_scanner
    state["returncode"] = returncode
    result = dast.scan("synthetic-private-network")
    assert result["passed"] is False
    assert result["error_category"] == "scanner_failed"
    assert SYNTHETIC_SECRET not in json.dumps(result)
    assert_scanner_was_cleaned_up(state, calls)


@pytest.mark.parametrize("raw", [None, "not-json", "{", "[]"])
def test_missing_or_corrupt_scan_report_blocks_and_cleans_up(fake_scanner, raw):
    state, calls = fake_scanner
    state.update(report=None, raw=raw)
    result = dast.scan("synthetic-private-network")
    assert result["passed"] is False
    assert_scanner_was_cleaned_up(state, calls)


def test_scan_timeout_blocks_and_removes_its_container_and_temporary_reports(fake_scanner):
    state, calls = fake_scanner
    state["exception"] = subprocess.TimeoutExpired(
        ["synthetic-scanner"],
        1,
        output=SYNTHETIC_SECRET,
        stderr=SYNTHETIC_SECRET,
    )
    result = dast.scan("synthetic-private-network")
    assert result["passed"] is False
    assert result["error_category"] == "scanner_timeout"
    assert SYNTHETIC_SECRET not in json.dumps(result)
    assert_scanner_was_cleaned_up(state, calls)


def test_unavailable_scanner_blocks_and_attempts_cleanup(fake_scanner):
    state, calls = fake_scanner
    state["exception"] = OSError(SYNTHETIC_SECRET)
    result = dast.scan("synthetic-private-network")
    assert result["passed"] is False
    assert SYNTHETIC_SECRET not in json.dumps(result)
    assert_scanner_was_cleaned_up(state, calls)


def test_cleanup_failure_cannot_turn_a_clean_report_green(fake_scanner):
    state, calls = fake_scanner
    state["cleanup_returncode"] = 1
    with pytest.raises(RuntimeError) as error:
        dast.scan("synthetic-private-network")
    assert SYNTHETIC_SECRET not in str(error.value)
    assert_scanner_was_cleaned_up(state, calls)


def test_cleanup_timeout_is_not_reported_as_success(fake_scanner):
    state, calls = fake_scanner
    state["cleanup_exception"] = subprocess.TimeoutExpired(
        ["synthetic-cleanup"], 1, output=SYNTHETIC_SECRET
    )
    with pytest.raises(subprocess.TimeoutExpired):
        dast.scan("synthetic-private-network")
    assert_scanner_was_cleaned_up(state, calls)
    assert 0 < calls[-1][1]["timeout"] <= dast.SCAN_TIMEOUT_SECONDS


def test_active_scan_plan_requires_actual_scan_completion_and_target_coverage():
    plan = dast.automation_plan()
    jobs = {job["type"]: job for job in plan["jobs"]}
    assert "activeScan" in jobs
    assert "exitStatus" not in jobs  # Do not mask native AF/scanner failures.
    assert plan["env"]["parameters"]["failOnError"] is True
    assert plan["env"]["parameters"]["failOnWarning"] is True
    assert plan["env"]["parameters"]["continueOnFailure"] is False
    requested_urls = {request["url"] for request in jobs["requestor"]["requests"]}
    assert requested_urls == {dast.TARGET + path for path in dast.REQUIRED_PATHS}
    assert all(request["responseCode"] == 200 for request in jobs["requestor"]["requests"])
    completion_tests = {test["statistic"]: test for test in jobs["activeScan"]["tests"]}
    for statistic, operator, value in (
        ("stats.ascan.started", ">=", 1),
        ("stats.ascan.time", ">", 0),
        ("stats.ascan.urls", ">", 0),
        ("stats.ascan.stopped", "==", 0),
    ):
        assert completion_tests[statistic]["operator"] == operator
        assert completion_tests[statistic]["value"] == value
        assert completion_tests[statistic]["onFail"] == "error"
    spider_test = jobs["spider"]["tests"][0]
    assert spider_test["statistic"] == "automation.spider.urls.added"
    assert spider_test["value"] >= 1
    assert spider_test["onFail"] == "error"


@pytest.mark.parametrize("failure_stage", ["artifact", "startup", "cleanup"])
def test_main_records_setup_and_cleanup_failures_without_raw_diagnostics(
    monkeypatch, tmp_path, capsys, failure_stage
):
    manifest = {"images": {"app": {"image_id": "sha256:" + "a" * 64}}}

    def verify(artifacts, commit):
        if failure_stage == "artifact":
            raise ValueError(SYNTHETIC_SECRET)
        return manifest

    @contextmanager
    def runtime(_manifest):
        if failure_stage == "startup":
            raise RuntimeError(SYNTHETIC_SECRET)
        yield SimpleNamespace(network="synthetic-private-network")
        if failure_stage == "cleanup":
            raise RuntimeError(SYNTHETIC_SECRET)

    monkeypatch.setattr(dast, "verify", verify)
    monkeypatch.setattr(dast, "docker", lambda *args, **kwargs: "")
    monkeypatch.setattr(dast, "isolated_runtime", runtime)
    monkeypatch.setattr(dast, "scan", lambda network: {"passed": True, "findings": []})
    reports = tmp_path / "reports"
    assert dast.main(tmp_path / "images", reports, COMMIT) == 1
    published = (reports / "zap.json").read_text()
    result = json.loads(published)
    assert result["passed"] is False
    assert result["commit"] == COMMIT
    assert result["error_category"] == "scan_setup_or_cleanup_failed"
    assert SYNTHETIC_SECRET not in published
    assert SYNTHETIC_SECRET not in capsys.readouterr().out
