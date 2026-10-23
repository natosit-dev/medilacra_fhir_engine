from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

from toolbench.assertions import PASS, UNSUPPORTED, evaluate_assertion
from toolbench.credentials import CredentialProfile, ValueSource
from toolbench.fhir import deep_get
from toolbench.runner import TestScriptRunner as WorkbenchRunner
from toolbench.systems import TestSystem as WorkbenchSystem, get_system, list_systems
from toolbench.testscript import AssertionDef, list_testscripts, load_testscript
from toolbench.transport import TransportClient, TransportResult
from toolbench.export import collection_zip_bytes, discover_runs, run_zip_bytes
from toolbench.regression import compare_runs, save_comparison


def test_builtin_systems_load():
    systems = {system.id: system for system in list_systems()}
    assert "shn-provider-test" in systems
    assert "iris-fhir-local" in systems
    assert systems["shn-provider-test"].configured is True
    assert systems["shn-provider-test"].correlation.request_header == "X-Correlation-Id"


def test_testscript_examples_load_without_unsupported_elements():
    scripts = [load_testscript(path) for path in list_testscripts()]
    names = {script.name for script in scripts}
    assert "SHNProviderConnectivity" in names
    assert "IRISCapabilityStatement" in names
    assert "IRISPatientCRUD" in names
    assert all(script.unsupported_elements == () for script in scripts)


def test_piqitt_style_deep_get_and_choice_values():
    resource = {
        "resourceType": "Observation",
        "category": [
            {"coding": [{"code": "laboratory"}]}
        ],
        "valueQuantity": {"value": 13.4, "unit": "g/dL"},
    }
    assert deep_get(resource, "category*.coding*.code") == ["laboratory"]
    assert deep_get(resource, "value[x]") == [
        {"value": 13.4, "unit": "g/dL"}
    ]


def test_assertion_engine_status_resource_and_path():
    response = TransportResult(
        method="GET",
        url="https://example.test/Patient/p1",
        status_code=200,
        reason="OK",
        request_headers={},
        request_body=None,
        response_headers={"Content-Type": "application/fhir+json"},
        response_text=json.dumps(
            {
                "resourceType": "Patient",
                "id": "p1",
            }
        ),
        elapsed_ms=1.0,
    )

    status = evaluate_assertion(
        AssertionDef(
            id="status",
            label="status",
            response_code="200",
        ),
        response,
    )
    resource = evaluate_assertion(
        AssertionDef(
            id="resource",
            label="resource",
            resource="Patient",
        ),
        response,
    )
    path = evaluate_assertion(
        AssertionDef(
            id="path",
            label="path",
            path="id",
            value="p1",
        ),
        response,
    )
    assert status.state == PASS
    assert resource.state == PASS
    assert path.state == PASS


class FakeResponse:
    def __init__(self, status_code=200, body=None, headers=None, reason="OK"):
        self.status_code = status_code
        self._body = body if body is not None else {}
        self.text = json.dumps(self._body)
        self.headers = headers or {"Content-Type": "application/json"}
        self.reason = reason

    def json(self):
        return self._body


def test_runner_executes_real_testscript_shape_without_shn_workflow(
    monkeypatch,
    tmp_path,
):
    def fake_request(method, url, **kwargs):
        assert method == "GET"
        assert url.endswith("/cds-services")
        return FakeResponse(
            body={
                "services": [
                    {
                        "id": "shn-order-sign",
                        "hook": "order-sign",
                    }
                ]
            }
        )

    monkeypatch.setattr("requests.request", fake_request)

    script = load_testscript("testscripts/shn/provider-connectivity.json")
    system = get_system("shn-provider-test")
    profile = CredentialProfile(
        id="none-for-test",
        name="None",
        type="none",
    )
    result = WorkbenchRunner(
        results_root=tmp_path,
        execution_mode="pytest",
    ).run(script, system, profile)

    assert result.status == PASS
    assert result.passed is True
    assert [action.state for action in result.actions] == [PASS, PASS, PASS]
    assert (Path(result.artifact_dir) / "run.json").is_file()
    assert (Path(result.artifact_dir) / "events.jsonl").is_file()
    assert (Path(result.artifact_dir) / "transactions.jsonl").is_file()


def test_transport_redacts_auth_and_identity_headers(
    monkeypatch,
):
    monkeypatch.setenv("TEST_BASIC_USER", "user")
    monkeypatch.setenv("TEST_BASIC_PASSWORD", "SECRET-PASSWORD")

    system = WorkbenchSystem.from_dict(
        {
            "id": "redaction",
            "name": "Redaction",
            "base_url": "https://example.test",
            "identity": {
                "user_key_header": "X-User-Key",
                "user_key": "SECRET-USER-KEY",
            },
        }
    )
    profile = CredentialProfile(
        id="basic",
        name="Basic",
        type="basic",
        username=ValueSource(source="env", env="TEST_BASIC_USER"),
        password=ValueSource(source="env", env="TEST_BASIC_PASSWORD"),
    )

    captured = {}

    def fake_request(method, url, **kwargs):
        captured.update(kwargs["headers"])
        return FakeResponse(body={"ok": True})

    monkeypatch.setattr("requests.request", fake_request)

    from toolbench.auth import AuthManager

    result = TransportClient(
        system,
        AuthManager(system, profile),
    ).request("GET", "/")

    assert captured["Authorization"].startswith("Basic ")
    assert captured["X-User-Key"] == "SECRET-USER-KEY"
    assert result.request_headers["Authorization"].startswith("<redacted:")
    assert result.request_headers["X-User-Key"] == "<redacted>"
    evidence = json.dumps(result.as_dict())
    assert "SECRET-PASSWORD" not in evidence
    assert "SECRET-USER-KEY" not in evidence


def test_validate_profile_id_is_not_approximated_by_declared_profile():
    response = TransportResult(
        method="GET",
        url="https://example.test/Patient/p1",
        status_code=200,
        reason="OK",
        request_headers={},
        request_body=None,
        response_headers={"Content-Type": "application/fhir+json"},
        response_text=json.dumps(
            {
                "resourceType": "Patient",
                "id": "p1",
                "meta": {
                    "profile": [
                        "http://example.org/StructureDefinition/patient"
                    ]
                },
            }
        ),
        elapsed_ms=1.0,
    )
    result = evaluate_assertion(
        AssertionDef(
            id="profile",
            label="profile",
            validate_profile_id="patient-profile",
        ),
        response,
        profiles={
            "patient-profile": (
                "http://example.org/StructureDefinition/patient"
            )
        },
    )
    assert result.state == UNSUPPORTED
    assert "actual StructureDefinition validation" in (result.message or "")


def test_exported_run_does_not_contain_auth_or_identity_secret_values(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("EXPORT_USER", "user")
    monkeypatch.setenv("EXPORT_PASSWORD", "EXPORT-SECRET-PASSWORD")

    system = WorkbenchSystem.from_dict(
        {
            "id": "export-redaction",
            "name": "Export Redaction",
            "base_url": "https://example.test",
            "identity": {
                "organization_key_header": "X-Org-Key",
                "organization_key": "EXPORT-SECRET-ORG-KEY",
            },
        }
    )
    profile = CredentialProfile(
        id="basic",
        name="Basic",
        type="basic",
        username=ValueSource(source="env", env="EXPORT_USER"),
        password=ValueSource(source="env", env="EXPORT_PASSWORD"),
    )

    def fake_request(method, url, **kwargs):
        return FakeResponse(
            body={"services": [{"id": "one"}]},
            headers={"Content-Type": "application/json"},
        )

    monkeypatch.setattr("requests.request", fake_request)
    script = load_testscript("testscripts/shn/provider-connectivity.json")
    result = WorkbenchRunner(results_root=tmp_path).run(
        script,
        system,
        profile,
    )
    payload = run_zip_bytes(result.artifact_dir)
    assert b"EXPORT-SECRET-PASSWORD" not in payload
    assert b"EXPORT-SECRET-ORG-KEY" not in payload
    assert b"Authorization: Basic" not in payload


def test_response_code_in_operator_and_request_direction_assertions():
    response = TransportResult(
        method="GET",
        url="https://example.test/fhir/Patient/p1?foo=bar",
        status_code=204,
        reason="No Content",
        request_headers={"Accept": "application/fhir+json"},
        request_body=None,
        response_headers={},
        response_text="",
        elapsed_ms=1.0,
    )

    code_result = evaluate_assertion(
        AssertionDef(
            id="code-in",
            label="code in",
            response_code="200,204",
            operator="in",
        ),
        response,
    )
    method_result = evaluate_assertion(
        AssertionDef(
            id="request-method",
            label="request method",
            direction="request",
            request_method="GET",
        ),
        response,
    )
    url_result = evaluate_assertion(
        AssertionDef(
            id="request-url",
            label="request URL",
            direction="request",
            request_url="/fhir/Patient/p1?foo=bar",
        ),
        response,
    )

    assert code_result.state == PASS
    assert method_result.state == PASS
    assert url_result.state == PASS


def test_bundled_testscripts_include_r4_required_execution_flags():
    for path in list_testscripts():
        source = json.loads(path.read_text(encoding="utf-8"))

        actions = []
        actions.extend((source.get("setup") or {}).get("action") or [])
        for test in source.get("test") or []:
            actions.extend(test.get("action") or [])
        actions.extend((source.get("teardown") or {}).get("action") or [])

        for action in actions:
            if "operation" in action:
                assert action["operation"].get("encodeRequestUrl") is True
            if "assert" in action:
                assert action["assert"].get("warningOnly") is False


def test_oauth_failure_does_not_echo_secret_or_token_endpoint_body(
    monkeypatch,
):
    monkeypatch.setenv("OAUTH_TEST_CLIENT_ID", "client")
    monkeypatch.setenv("OAUTH_TEST_SECRET", "OAUTH-SENTINEL-SECRET")

    system = WorkbenchSystem.from_dict(
        {
            "id": "oauth-failure",
            "name": "OAuth Failure",
            "base_url": "https://example.test",
        }
    )
    profile = CredentialProfile(
        id="oauth",
        name="OAuth",
        type="oauth2_client_credentials",
        token_url="/oauth/token",
        client_id=ValueSource(
            source="env",
            env="OAUTH_TEST_CLIENT_ID",
        ),
        client_secret=ValueSource(
            source="env",
            env="OAUTH_TEST_SECRET",
        ),
    )

    class TokenFailure:
        status_code = 401
        text = "reflected OAUTH-SENTINEL-SECRET"

        def json(self):
            return {
                "error": "invalid_client",
                "debug": "OAUTH-SENTINEL-SECRET",
            }

    monkeypatch.setattr("requests.post", lambda *args, **kwargs: TokenFailure())

    from toolbench.auth import AuthManager

    response = TransportClient(
        system,
        AuthManager(system, profile),
    ).request("GET", "/Patient")

    assert response.status_code is None
    assert response.error is not None
    assert "authentication failed" in response.error
    assert "OAUTH-SENTINEL-SECRET" not in response.error
    assert "OAUTH-SENTINEL-SECRET" not in json.dumps(response.as_dict())


def test_collection_export_includes_saved_regression_artifacts(
    monkeypatch,
    tmp_path,
):
    def fake_request(method, url, **kwargs):
        return FakeResponse(body={"services": [{"id": "one"}]})

    monkeypatch.setattr("requests.request", fake_request)

    script = load_testscript("testscripts/shn/provider-connectivity.json")
    system = get_system("shn-provider-test")
    profile = CredentialProfile(id="none", name="None", type="none")
    runner = WorkbenchRunner(results_root=tmp_path)

    baseline = runner.run(script, system, profile)
    current = runner.run(script, system, profile)

    assert baseline.credential_profile_id == "none"
    comparison = compare_runs(
        baseline.as_dict(),
        current.as_dict(),
    )
    comparison_path = save_comparison(
        comparison,
        tmp_path / "comparisons",
    )
    assert comparison_path.is_file()

    runs = discover_runs(tmp_path)
    payload, manifest = collection_zip_bytes(runs)
    assert manifest["summary"]["run_count"] == 2

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        assert any(
            name.startswith("comparisons/") and name.endswith(".json")
            for name in archive.namelist()
        )


def test_target_fixture_request_id_and_static_fixture_assertions(
    monkeypatch,
    tmp_path,
):
    fixture_path = tmp_path / "patient.json"
    fixture_path.write_text(
        json.dumps(
            {
                "resourceType": "Patient",
                "id": "p1",
            }
        ),
        encoding="utf-8",
    )
    script_path = tmp_path / "target-read.json"
    script_path.write_text(
        json.dumps(
            {
                "resourceType": "TestScript",
                "id": "target-read",
                "name": "TargetRead",
                "status": "draft",
                "fixture": [
                    {
                        "id": "patient-fixture",
                        "autocreate": False,
                        "autodelete": False,
                        "resource": {"reference": "patient.json"},
                    }
                ],
                "setup": {
                    "action": [
                        {
                            "id": "fixture-id",
                            "assert": {
                                "label": "Fixture id",
                                "sourceId": "patient-fixture",
                                "path": "$.id",
                                "operator": "equals",
                                "value": "p1",
                                "direction": "response",
                                "warningOnly": False,
                            },
                        }
                    ]
                },
                "test": [
                    {
                        "name": "Read target fixture",
                        "action": [
                            {
                                "id": "read-patient",
                                "operation": {
                                    "label": "Read Patient",
                                    "type": {
                                        "system": (
                                            "http://terminology.hl7.org/"
                                            "CodeSystem/testscript-operation-codes"
                                        ),
                                        "code": "read",
                                    },
                                    "resource": "Patient",
                                    "targetId": "patient-fixture",
                                    "requestId": "read-request",
                                    "responseId": "read-response",
                                    "accept": "json",
                                    "encodeRequestUrl": True,
                                },
                            },
                            {
                                "id": "request-method",
                                "assert": {
                                    "label": "GET was sent",
                                    "sourceId": "read-request",
                                    "direction": "request",
                                    "requestMethod": "get",
                                    "warningOnly": False,
                                },
                            },
                            {
                                "id": "request-url",
                                "assert": {
                                    "label": "Patient URL",
                                    "sourceId": "read-request",
                                    "direction": "request",
                                    "requestURL": "/Patient/p1",
                                    "warningOnly": False,
                                },
                            },
                            {
                                "id": "response-status",
                                "assert": {
                                    "label": "HTTP 200",
                                    "sourceId": "read-response",
                                    "direction": "response",
                                    "responseCode": "200",
                                    "warningOnly": False,
                                },
                            },
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    def fake_request(method, url, **kwargs):
        assert method == "GET"
        assert url.endswith("/Patient/p1")
        assert kwargs["headers"]["Accept"] == "application/fhir+json"
        return FakeResponse(
            body={"resourceType": "Patient", "id": "p1"},
            headers={"Content-Type": "application/fhir+json"},
        )

    monkeypatch.setattr("requests.request", fake_request)

    script = load_testscript(script_path)
    assert script.unsupported_elements == ()
    system = WorkbenchSystem.from_dict(
        {
            "id": "target-test",
            "name": "Target Test",
            "base_url": "https://example.test/fhir",
            "protocol": "fhir",
        }
    )
    result = WorkbenchRunner(
        results_root=tmp_path / "results",
    ).run(
        script,
        system,
        CredentialProfile(id="none", name="None", type="none"),
    )

    assert result.status == PASS
    assert all(action.state == PASS for action in result.actions)


def test_xpath_testscript_path_is_explicitly_unsupported():
    response = TransportResult(
        method="GET",
        url="https://example.test/Patient/p1",
        status_code=200,
        reason="OK",
        request_headers={},
        request_body=None,
        response_headers={"Content-Type": "application/fhir+json"},
        response_text=json.dumps({"resourceType": "Patient", "id": "p1"}),
        elapsed_ms=1.0,
    )
    result = evaluate_assertion(
        AssertionDef(
            id="xpath",
            label="XPath",
            path="/f:Patient/f:id/@value",
            value="p1",
        ),
        response,
    )
    assert result.state == UNSUPPORTED
    assert "XPath" in (result.message or "")


def test_json_body_credentials_are_redacted_from_persisted_evidence(
    monkeypatch,
    tmp_path,
):
    fixture = tmp_path / "secret-payload.json"
    fixture.write_text(
        json.dumps(
            {
                "client_id": "safe-client-id",
                "client_secret": "BODY-SENTINEL-SECRET",
            }
        ),
        encoding="utf-8",
    )
    script_path = tmp_path / "body-redaction.json"
    script_path.write_text(
        json.dumps(
            {
                "resourceType": "TestScript",
                "id": "body-redaction",
                "name": "BodyRedaction",
                "status": "draft",
                "fixture": [
                    {
                        "id": "secret-body",
                        "autocreate": False,
                        "autodelete": False,
                        "resource": {"reference": "secret-payload.json"},
                    }
                ],
                "test": [
                    {
                        "name": "Echo",
                        "action": [
                            {
                                "id": "post-secret",
                                "operation": {
                                    "label": "POST secret-shaped JSON",
                                    "method": "POST",
                                    "url": "/echo",
                                    "sourceId": "secret-body",
                                    "contentType": "application/json",
                                    "accept": "application/json",
                                    "encodeRequestUrl": True,
                                },
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    captured = {}

    def fake_request(method, url, **kwargs):
        captured["body"] = kwargs.get("data")
        return FakeResponse(
            body={
                "access_token": "BODY-SENTINEL-TOKEN",
                "status": "ok",
            },
            headers={"Content-Type": "application/json"},
        )

    monkeypatch.setattr("requests.request", fake_request)

    script = load_testscript(script_path)
    system = WorkbenchSystem.from_dict(
        {
            "id": "body-redaction",
            "name": "Body Redaction",
            "base_url": "https://example.test",
            "protocol": "mixed",
        }
    )
    result = WorkbenchRunner(
        results_root=tmp_path / "results",
    ).run(
        script,
        system,
        CredentialProfile(id="none", name="None", type="none"),
    )

    # The real request still receives the real test input in memory.
    assert "BODY-SENTINEL-SECRET" in captured["body"]

    payload = run_zip_bytes(result.artifact_dir)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        uncompressed = b"\n".join(
            archive.read(name)
            for name in archive.namelist()
            if not name.endswith("/")
        )
    assert b"BODY-SENTINEL-SECRET" not in uncompressed
    assert b"BODY-SENTINEL-TOKEN" not in uncompressed
    assert b"<redacted>" in uncompressed



def test_json_file_credential_source_env_path_override(tmp_path, monkeypatch):
    from toolbench.credentials import ValueSource

    default = tmp_path / "default-client.json"
    selected = tmp_path / "selected-client.json"
    default.write_text('{"client_id":"DEFAULT_ID","client_secret":"DEFAULT_SECRET"}')
    selected.write_text('{"client_id":"ENV_ID","client_secret":"ENV_SECRET"}')
    source = ValueSource(
        source="json_file", env="SHN_CLIENT_FILE",
        path=str(default), key="client_id",
    )

    monkeypatch.delenv("SHN_CLIENT_FILE", raising=False)
    assert source.resolve() == "DEFAULT_ID"

    monkeypatch.setenv("SHN_CLIENT_FILE", str(selected))
    assert source.resolve() == "ENV_ID"
