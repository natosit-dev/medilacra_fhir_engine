"""Focused regression checks for the SHN test harness's epistemic boundaries."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from connectathon.shn_medilacra_crd import (
    build_crd_case,
    build_crd_order_sign_request,
)
from connectathon.shn_mvp0 import build_reality
from connectathon.shn_provider.client import SHNProviderClient
from connectathon.shn_provider.reference_suite import (
    OperationResult, ReferenceRunResult, ReferenceSuiteRunner,
)
from connectathon.shn_provider.summaries import (
    CRD_COVERAGE_INFORMATION, summarize_crd, summarize_pas,
)
from connectathon.shn_provider.timing import assess_timing, load_timing_config


def _crd_response(covered_values: list[str]) -> dict:
    actions = []
    for index, covered in enumerate(covered_values):
        actions.append({
            "type": "update",
            "resource": {
                "resourceType": "ServiceRequest",
                "id": f"order-{index}",
                "extension": [{
                    "url": CRD_COVERAGE_INFORMATION,
                    "extension": [
                        {"url": "covered", "valueCode": covered},
                        {"url": "doc-needed", "valueCode": "clinical"},
                    ],
                }],
            },
        })
    return {"cards": [], "systemActions": actions}


def test_crd_summary_retains_each_coverage_block_and_does_not_overwrite():
    summary = summarize_crd(_crd_response(["covered", "not-covered"]))
    assert len(summary["coverage_information"]) == 2
    assert [entry["source_resource"]["id"] for entry in summary["coverage_information"]] == [
        "order-0", "order-1",
    ]
    assert summary["coverage_information"][0]["extension"]["extension"][0]["valueCode"] == "covered"
    assert summary["coverage_information"][1]["extension"]["extension"][0]["valueCode"] == "not-covered"
    assert summary["covered"] is None
    assert summary["doc-needed"] == "clinical"
    assert "covered" in summary["ambiguous_fields"]


def test_crd_conflicting_none_cannot_pass_expectation_of_none():
    summary = summarize_crd(
        _crd_response(["covered", "not-covered"]),
        expected={"covered": None},
    )
    assert summary["expected_checks"]["covered"] is False
    assert summary["behavior_match"] is False


def test_crd_repeated_agreeing_values_keep_legacy_scalar_output():
    summary = summarize_crd(
        _crd_response(["covered", "covered"]),
        expected={"covered": "covered", "doc-needed": "clinical"},
    )
    assert summary["covered"] == "covered"
    assert summary["behavior_match"] is True


def test_unknown_and_empty_expected_assertions_never_pass_silently():
    response = _crd_response(["covered"])
    with pytest.raises(ValueError, match="unknown CRD assertion"):
        summarize_crd(response, expected={"covred": "covered"})
    with pytest.raises(ValueError, match="must not be empty"):
        summarize_crd(response, expected={})
    with pytest.raises(ValueError, match="unknown PAS assertion"):
        summarize_pas({"resourceType": "Bundle", "entry": []}, expected={"autherization": True})
    with pytest.raises(ValueError, match="must not be empty"):
        summarize_pas({"resourceType": "Bundle", "entry": []}, expected={})


def test_crd_live_invocations_are_unique_but_offline_fixtures_are_reproducible():
    reality = build_reality(seed=43)
    first = build_crd_order_sign_request(reality)
    second = build_crd_order_sign_request(reality)
    assert first["hookInstance"] != second["hookInstance"]
    assert uuid.UUID(first["hookInstance"]).version == 4
    assert uuid.UUID(second["hookInstance"]).version == 4

    fixture_a = build_crd_case(seed=43)
    fixture_b = build_crd_case(seed=43)
    assert fixture_a == fixture_b
    assert uuid.UUID(fixture_a["crd_request"]["hookInstance"]).version == 5


def test_configurable_timing_disabled_and_non_normative_defaults():
    config = load_timing_config()
    assert config["enabled"] is False
    assert config["rules"]["/cds-services/shn-order-sign"]["fail_ms"] is None
    assessment = assess_timing(
        "/cds-services/shn-order-sign",
        elapsed_ms=15000,
        request_elapsed_ms=5000,
        config=config,
    )
    assert assessment["status"] == "DISABLED"


def test_timing_warn_and_fail_independently_from_total_elapsed():
    config = {
        "enabled": True,
        "source": "unit test",
        "rules": {
            "/cds-services/shn-order-sign": {
                "metric": "request_elapsed_ms",
                "warn_ms": 100,
                "fail_ms": 200,
            }
        },
    }
    def check(request_ms: float) -> str:
        return assess_timing(
            "/cds-services/shn-order-sign",
            elapsed_ms=5000,
            request_elapsed_ms=request_ms,
            config=config,
        )["status"]
    assert check(90) == "PASS"
    assert check(150) == "WARN"
    assert check(250) == "FAIL"


def test_bad_timing_configuration_is_rejected(tmp_path: Path):
    config = {
        "enabled": True,
        "rules": {
            "/cds-services/shn-order-sign": {
                "metric": "elapsed_ms", "warn_ms": 500, "fail_ms": 400
            }
        },
    }
    path = tmp_path / "timing.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="warn_ms cannot exceed"):
        load_timing_config(path)


def test_client_captures_request_time_without_exposing_credentials(tmp_path: Path):
    creds = tmp_path / "creds.json"
    creds.write_text(json.dumps({"client_id": "test", "client_secret": "TOP-SECRET"}))
    config = {
        "enabled": False, "source": "test", "rules": {
            "/cds-services/shn-order-sign": {
                "metric": "request_elapsed_ms", "warn_ms": None, "fail_ms": None,
            }
        },
    }
    client = SHNProviderClient(client_file=creds, timing_config=config)

    def fake_open(request):
        if request.full_url.endswith("/oauth/token"):
            return 200, {"access_token": "TEST-TOKEN", "expires_in": 300}, {}
        return 200, {"cards": []}, {}

    client._open = fake_open
    result = client.crd({"hook": "order-sign"}, correlation_prefix="unit-test")
    transport = result.transport_dict()
    assert transport["request_elapsed_ms"] >= 0
    assert transport["elapsed_ms"] >= transport["request_elapsed_ms"]
    assert transport["timing_assessment"]["status"] == "DISABLED"
    serialized = json.dumps(transport)
    assert "TOP-SECRET" not in serialized
    assert "TEST-TOKEN" not in serialized


def test_reference_suite_timing_can_fail_without_changing_http_expectation():
    runner = ReferenceSuiteRunner(client=None, persist_artifacts=False)
    result = ReferenceRunResult(
        test_id="TP-01", label="test", kind="positive",
        run_id="test-run", started_at="2026-10-31T00:00:00Z",
    )
    operation = OperationResult(
        operation_id="crd", operation_type="crd",
        expected={"http_status": 200}, observed={"http_status": 200},
        transport={"timing_assessment": {
            "status": "FAIL", "metric": "request_elapsed_ms",
            "observed_ms": 250, "fail_ms": 200, "warn_ms": 100,
        }},
    )
    runner._record(result, operation)
    assert operation.observed["http_status"] == 200
    assert operation.observed["checks"]["http_status"] is True
    assert operation.observed["checks"]["timing.direct"] is False
    assert operation.passed is False
