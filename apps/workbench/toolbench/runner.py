from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .assertions import (
    ERROR,
    FAIL,
    PASS,
    SKIP,
    UNSUPPORTED,
    AssertionResult,
    evaluate_assertion,
)
from .auth import AuthManager
from .credentials import CredentialProfile
from .fixtures import FixtureStore
from .logging import RunLogger, sha256_file, utc_now, write_json, write_jsonl
from .safety import (
    sanitize_jsonish_text,
    sanitize_system_config,
    sanitize_testscript_source,
    sanitize_value,
)
from .systems import TestSystem
from .testscript import LoadedTestScript, ScriptAction
from .transport import TransportClient, TransportResult
from .validation import BasicFHIRValidator, ValidationResult, Validator


DEFAULT_RESULTS_ROOT = Path("results")


@dataclass
class ActionResult:
    action_id: str
    section: str
    test_name: str | None
    kind: str
    label: str
    state: str
    transport: dict[str, Any] | None = None
    assertion: dict[str, Any] | None = None
    validation: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TestRunResult:
    run_id: str
    testscript_id: str
    testscript_name: str
    system_id: str
    system_name: str
    credential_profile_id: str
    started_at: str
    completed_at: str | None = None
    duration_ms: float | None = None
    status: str = "RUNNING"
    passed: bool = False
    unsupported_elements: list[str] = field(default_factory=list)
    actions: list[ActionResult] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    execution_context: dict[str, Any] = field(default_factory=dict)
    artifact_dir: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "testscript_id": self.testscript_id,
            "testscript_name": self.testscript_name,
            "system_id": self.system_id,
            "system_name": self.system_name,
            "credential_profile_id": self.credential_profile_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "passed": self.passed,
            "unsupported_elements": self.unsupported_elements,
            "actions": [action.as_dict() for action in self.actions],
            "events": self.events,
            "execution_context": self.execution_context,
            "artifact_dir": self.artifact_dir,
        }


class TestScriptRunner:
    def __init__(
        self,
        *,
        results_root: str | Path = DEFAULT_RESULTS_ROOT,
        persist_artifacts: bool = True,
        execution_mode: str = "python",
        validator: Validator | None = None,
    ) -> None:
        self.results_root = Path(results_root)
        self.persist_artifacts = persist_artifacts
        self.execution_mode = execution_mode
        self.validator = validator or BasicFHIRValidator()

    def run(
        self,
        script: LoadedTestScript,
        system: TestSystem,
        profile: CredentialProfile | None = None,
        *,
        through_action_id: str | None = None,
    ) -> TestRunResult:
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        run_id = (
            f"{_slug(script.name)}-{system.id}-{stamp}-"
            f"{uuid.uuid4().hex[:8]}"
        )
        started_at = utc_now()
        started = time.monotonic()
        logger = RunLogger(
            run_id=run_id,
            testscript_id=script.id,
            system_id=system.id,
            execution_mode=self.execution_mode,
        )
        result = TestRunResult(
            run_id=run_id,
            testscript_id=script.id,
            testscript_name=script.name,
            system_id=system.id,
            system_name=system.name,
            credential_profile_id=(profile.id if profile is not None else "none"),
            started_at=started_at,
            unsupported_elements=list(script.unsupported_elements),
            execution_context=logger.context,
        )

        logger.emit(
            "run.started",
            "run",
            {
                "testscript_name": script.name,
                "system_name": system.name,
                "started_at": started_at,
            },
        )
        logger.emit(
            "system.selected",
            "configuration",
            {
                "system_id": system.id,
                "name": system.name,
                "base_url": system.base_url,
                "protocol": system.protocol,
                "fhir_version": system.fhir_version,
                "credential_profile": system.credential_profile,
            },
        )
        logger.emit(
            "credential.selected",
            "configuration",
            {
                "profile_id": profile.id if profile is not None else "none",
                "auth_type": profile.type if profile is not None else "none",
            },
        )
        logger.emit(
            "testscript.loaded",
            "configuration",
            {
                "path": str(script.path),
                "url": script.url,
                "name": script.name,
                "fixture_count": len(script.fixtures),
                "action_count": len(script.actions),
                "unsupported_elements": list(script.unsupported_elements),
            },
        )
        for element in script.unsupported_elements:
            logger.emit(
                "testscript.unsupported",
                "configuration",
                {"element": element},
            )

        fixtures = FixtureStore(script)
        for fixture_id in fixtures.available_ids():
            logger.emit(
                "fixture.loaded",
                "fixture",
                {"fixture_id": fixture_id},
            )

        auth = AuthManager(
            system,
            profile,
            event_sink=logger.emit,
        )
        transport = TransportClient(
            system,
            auth,
            event_sink=logger.emit,
        )

        last_response: TransportResult | None = None
        responses: dict[str, TransportResult] = {}
        operation_records: list[tuple[ActionResult, TransportResult]] = []

        actions_to_run = list(script.actions)
        if through_action_id is not None:
            ids = [action.id for action in actions_to_run]
            if through_action_id not in ids:
                raise KeyError(
                    f"TestScript has no action {through_action_id!r}"
                )
            actions_to_run = actions_to_run[: ids.index(through_action_id) + 1]

        for action in actions_to_run:
            logger.set_operation(action.id)
            if action.operation is not None:
                action_result, response = self._run_operation(
                    action,
                    fixtures,
                    transport,
                    logger,
                )
                result.actions.append(action_result)
                operation_records.append((action_result, response))
                last_response = response
                operation = action.operation
                for evidence_id in (
                    operation.request_id,
                    operation.response_id,
                ):
                    if evidence_id:
                        responses[evidence_id] = response
                if operation.response_id:
                    try:
                        fixtures.put(
                            operation.response_id,
                            response.json_body(),
                        )
                    except Exception:
                        fixtures.put(
                            operation.response_id,
                            response.response_text,
                        )
            elif action.assertion is not None:
                response = (
                    responses.get(action.assertion.source_id)
                    if action.assertion.source_id
                    else last_response
                )
                if response is None and action.assertion.source_id:
                    try:
                        fixture_value = fixtures.get(
                            action.assertion.source_id
                        )
                    except Exception:
                        fixture_value = None
                    if fixture_value is not None:
                        response = _fixture_transport(
                            fixture_value,
                            action.assertion.source_id,
                        )
                assertion_result = evaluate_assertion(
                    action.assertion,
                    response,
                    profiles=script.profiles,
                )
                logger.emit(
                    "assertion.evaluated",
                    "assertion",
                    assertion_result.as_dict(),
                )
                result.actions.append(
                    ActionResult(
                        action_id=action.id,
                        section=action.section,
                        test_name=action.test_name,
                        kind="assertion",
                        label=action.assertion.label,
                        state=assertion_result.state,
                        assertion=assertion_result.as_dict(),
                    )
                )

        logger.set_operation(None)
        result.status = _overall_status(
            result.actions,
            result.unsupported_elements,
        )
        result.passed = result.status == PASS
        result.completed_at = utc_now()
        result.duration_ms = round(
            (time.monotonic() - started) * 1000.0,
            1,
        )

        run_dir = None
        if self.persist_artifacts:
            run_dir = self.results_root / result.run_id
            result.artifact_dir = str(run_dir)
            self._persist_configuration(
                run_dir,
                script,
                system,
                profile,
                logger,
            )
            self._persist_operations(
                run_dir,
                operation_records,
                logger,
            )

        logger.emit(
            "run.completed",
            "run",
            {
                "status": result.status,
                "passed": result.passed,
                "completed_at": result.completed_at,
                "duration_ms": result.duration_ms,
                "action_count": len(result.actions),
                "through_action_id": through_action_id,
            },
        )
        result.events = list(logger.events)

        if run_dir is not None:
            write_jsonl(run_dir / "events.jsonl", result.events)
            write_jsonl(
                run_dir / "transactions.jsonl",
                [
                    _transaction_row(result, action_result, response)
                    for action_result, response in operation_records
                ],
            )
            write_json(run_dir / "run.json", result.as_dict())

        return result

    def _run_operation(
        self,
        action: ScriptAction,
        fixtures: FixtureStore,
        transport: TransportClient,
        logger: RunLogger,
    ) -> tuple[ActionResult, TransportResult]:
        operation = action.operation
        assert operation is not None
        logger.emit(
            "operation.started",
            "operation",
            {
                "label": operation.label,
                "section": action.section,
                "test_name": action.test_name,
                "method": operation.method,
                "url": operation.url,
                "source_id": operation.source_id,
            },
        )

        try:
            resolved_url = _resolve_operation_url(
                operation,
                fixtures,
            )
        except UnsupportedOperationError as exc:
            response = TransportResult(
                method=operation.method,
                url=operation.url,
                status_code=None,
                reason=None,
                request_headers={},
                request_body=None,
                response_headers={},
                response_text="",
                elapsed_ms=0.0,
                error=str(exc),
            )
            action_result = ActionResult(
                action_id=action.id,
                section=action.section,
                test_name=action.test_name,
                kind="operation",
                label=operation.label,
                state=UNSUPPORTED,
                transport=response.as_dict(),
                error=str(exc),
            )
            logger.emit(
                "operation.completed",
                "operation",
                {
                    "state": UNSUPPORTED,
                    "error": str(exc),
                },
            )
            return action_result, response
        except Exception as exc:
            response = TransportResult(
                method=operation.method,
                url=operation.url,
                status_code=None,
                reason=None,
                request_headers={},
                request_body=None,
                response_headers={},
                response_text="",
                elapsed_ms=0.0,
                error=str(exc),
            )
            action_result = ActionResult(
                action_id=action.id,
                section=action.section,
                test_name=action.test_name,
                kind="operation",
                label=operation.label,
                state=ERROR,
                transport=response.as_dict(),
                error=str(exc),
            )
            logger.emit(
                "operation.completed",
                "operation",
                {
                    "state": ERROR,
                    "error": str(exc),
                },
            )
            return action_result, response

        body = None
        if operation.source_id:
            try:
                source = fixtures.get(operation.source_id)
                body = (
                    json.dumps(source)
                    if isinstance(source, (dict, list))
                    else str(source)
                )
            except Exception as exc:
                response = TransportResult(
                    method=operation.method,
                    url=operation.url,
                    status_code=None,
                    reason=None,
                    request_headers={},
                    request_body=None,
                    response_headers={},
                    response_text="",
                    elapsed_ms=0.0,
                    error=str(exc),
                )
                action_result = ActionResult(
                    action_id=action.id,
                    section=action.section,
                    test_name=action.test_name,
                    kind="operation",
                    label=operation.label,
                    state=ERROR,
                    transport=response.as_dict(),
                    error=str(exc),
                )
                logger.emit(
                    "operation.completed",
                    "operation",
                    action_result.as_dict(),
                )
                return action_result, response

        headers = dict(operation.headers)
        if operation.accept:
            headers["Accept"] = operation.accept
        elif transport.system.protocol == "fhir":
            headers.setdefault("Accept", "application/fhir+json")

        if body is not None:
            headers["Content-Type"] = (
                operation.content_type or "application/fhir+json"
            )

        response = transport.request(
            operation.method,
            resolved_url,
            headers=headers,
            body=body,
        )

        logger.emit(
            "validation.started",
            "validation",
            {"response_status": response.status_code},
        )
        validation_results = self.validator.validate(response)
        for validation in validation_results:
            logger.emit(
                "validation.completed",
                "validation",
                validation.as_dict(),
            )

        state = ERROR if response.error else PASS
        action_result = ActionResult(
            action_id=action.id,
            section=action.section,
            test_name=action.test_name,
            kind="operation",
            label=operation.label,
            state=state,
            transport=response.as_dict(),
            validation=[
                item.as_dict()
                for item in validation_results
            ],
            error=response.error,
        )
        logger.emit(
            "operation.completed",
            "operation",
            {
                "state": state,
                "status_code": response.status_code,
                "elapsed_ms": response.elapsed_ms,
                "error": response.error,
            },
        )
        return action_result, response

    def _persist_configuration(
        self,
        run_dir: Path,
        script: LoadedTestScript,
        system: TestSystem,
        profile: CredentialProfile | None,
        logger: RunLogger,
    ) -> None:
        config_dir = run_dir / "configuration"
        testscript_path = config_dir / "testscript.json"
        system_path = config_dir / "system.json"
        credential_path = config_dir / "credential-profile.json"

        write_json(
            testscript_path,
            sanitize_testscript_source(
                script.source,
                set(system.sensitive_headers),
            ),
        )
        write_json(
            system_path,
            sanitize_system_config(system.as_dict()),
        )

        if profile is None:
            profile_data: dict[str, Any] = {
                "id": "none",
                "name": "No authentication",
                "type": "none",
            }
        else:
            profile_data = {
                "id": profile.id,
                "name": profile.name,
                "type": profile.type,
                "token_url": profile.token_url,
                "auth_style": profile.auth_style,
                "scope": profile.scope,
                "client_id_source": _source_descriptor(profile.client_id),
                "client_secret_source": _source_descriptor(profile.client_secret),
                "username_source": _source_descriptor(profile.username),
                "password_source": _source_descriptor(profile.password),
                "bearer_token_source": _source_descriptor(profile.bearer_token),
                "token_extra_field_names": sorted(profile.token_extra_fields),
            }
        write_json(
            credential_path,
            sanitize_value(profile_data),
        )

        for role, path in (
            ("testscript", testscript_path),
            ("system", system_path),
            ("credential_profile", credential_path),
        ):
            record = _artifact_record(path, run_dir, role)
            logger.emit(
                "artifact.written",
                "persistence",
                record,
                artifact_refs=[record["path"]],
                operation_id=None,
            )

    def _persist_operations(
        self,
        run_dir: Path,
        records: list[tuple[ActionResult, TransportResult]],
        logger: RunLogger,
    ) -> None:
        for index, (action, response) in enumerate(records, start=1):
            operation_dir = (
                run_dir
                / "operations"
                / f"{index:02d}-{_slug(action.action_id)}"
            )
            files: list[tuple[str, Path, Any, bool]] = [
                (
                    "request_headers",
                    operation_dir / "request-headers.json",
                    response.request_headers,
                    True,
                ),
                (
                    "response_headers",
                    operation_dir / "response-headers.json",
                    response.response_headers,
                    True,
                ),
                (
                    "result",
                    operation_dir / "result.json",
                    action.as_dict(),
                    True,
                ),
            ]
            for role, path, value, is_json in files:
                if is_json:
                    write_json(path, value)
                logger.emit(
                    "artifact.written",
                    "persistence",
                    _artifact_record(path, run_dir, role),
                    operation_id=action.action_id,
                    artifact_refs=[path.relative_to(run_dir).as_posix()],
                )

            for role, filename, text in (
                (
                    "request",
                    "request.txt",
                    sanitize_jsonish_text(response.request_body) or "",
                ),
                (
                    "response",
                    "response.txt",
                    sanitize_jsonish_text(response.response_text) or "",
                ),
            ):
                path = operation_dir / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
                logger.emit(
                    "artifact.written",
                    "persistence",
                    _artifact_record(path, run_dir, role),
                    operation_id=action.action_id,
                    artifact_refs=[path.relative_to(run_dir).as_posix()],
                )


class UnsupportedOperationError(ValueError):
    pass


def _resolve_operation_url(
    operation,
    fixtures: FixtureStore,
) -> str:
    url = operation.url

    if operation.method == "UNSUPPORTED":
        type_value = operation.raw.get("type") or {}
        type_code = type_value.get("code")
        raise UnsupportedOperationError(
            f"TestScript operation type {type_code or 'unknown'} is not implemented in v0.1"
        )

    if operation.raw.get("encodeRequestUrl") is False:
        raise UnsupportedOperationError(
            "encodeRequestUrl=false is not implemented in v0.1"
        )
    for field_name in ("origin", "destination"):
        if operation.raw.get(field_name) is not None:
            raise UnsupportedOperationError(
                f"operation-level {field_name} routing is not implemented in v0.1"
            )
    if any(
        "${" in str(value)
        for _key, value in operation.headers
    ):
        raise UnsupportedOperationError(
            "TestScript variable expansion in request headers is not implemented in v0.1"
        )

    if "${" in url or (operation.params and "${" in operation.params):
        raise UnsupportedOperationError(
            "TestScript variable expansion is not implemented in v0.1"
        )

    if not operation.target_id or operation.explicit_url:
        return url

    target = fixtures.get(operation.target_id)
    if not isinstance(target, dict):
        raise ValueError(
            f"target fixture {operation.target_id!r} is not a FHIR JSON object"
        )

    resource_type = (
        target.get("resourceType")
        or operation.resource
    )
    resource_id = target.get("id")
    if not resource_type or not resource_id:
        raise ValueError(
            f"target fixture {operation.target_id!r} needs resourceType and id"
        )

    code = (operation.type_code or "").lower()
    if code == "vread":
        version_id = (target.get("meta") or {}).get("versionId")
        if not version_id:
            raise ValueError(
                f"target fixture {operation.target_id!r} has no meta.versionId for vread"
            )
        return f"/{resource_type}/{resource_id}/_history/{version_id}"

    if code in {
        "read",
        "update",
        "updatecreate",
        "patch",
        "delete",
    }:
        suffix = operation.params or ""
        return f"/{resource_type}/{resource_id}{suffix}"

    raise UnsupportedOperationError(
        f"targetId URL resolution is not implemented for operation type {code or 'unspecified'}"
    )


def _fixture_transport(
    value: Any,
    fixture_id: str,
) -> TransportResult:
    text = (
        json.dumps(value)
        if isinstance(value, (dict, list))
        else str(value)
    )
    content_type = (
        "application/fhir+json"
        if isinstance(value, dict) and value.get("resourceType")
        else "application/json"
    )
    return TransportResult(
        method="FIXTURE",
        url=f"fixture:{fixture_id}",
        status_code=None,
        reason=None,
        request_headers={"Content-Type": content_type},
        request_body=text,
        response_headers={"Content-Type": content_type},
        response_text=text,
        elapsed_ms=0.0,
    )


def _source_descriptor(source) -> dict[str, Any] | None:
    if source is None:
        return None
    value = asdict(source)
    path_value = value.get("path")
    if path_value:
        path = Path(str(path_value)).expanduser()
        if path.is_absolute():
            value["path"] = path.name
    return value


def _artifact_record(
    path: Path,
    root: Path,
    role: str,
) -> dict[str, Any]:
    return {
        "role": role,
        "path": path.relative_to(root).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def _transaction_row(
    run: TestRunResult,
    action: ActionResult,
    response: TransportResult,
) -> dict[str, Any]:
    return {
        "run_id": run.run_id,
        "testscript_id": run.testscript_id,
        "system_id": run.system_id,
        "action_id": action.action_id,
        "section": action.section,
        "test_name": action.test_name,
        "method": response.method,
        "url": response.url,
        "status_code": response.status_code,
        "elapsed_ms": response.elapsed_ms,
        "correlation_id": response.correlation_id,
        "response_correlation_id": response.response_correlation_id,
        "leg_id": response.leg_id,
        "trace_url": response.trace_url,
        "error": response.error,
    }


def _overall_status(
    actions: list[ActionResult],
    unsupported_elements: list[str],
) -> str:
    states = {action.state for action in actions}
    validation_states = {
        str(validation.get("state"))
        for action in actions
        for validation in action.validation
        if isinstance(validation, dict) and validation.get("state")
    }
    states.update(validation_states)

    if ERROR in states:
        return ERROR
    if FAIL in states:
        return FAIL
    if UNSUPPORTED in states or unsupported_elements:
        return UNSUPPORTED
    return PASS


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-").lower()
    return slug or "run"
