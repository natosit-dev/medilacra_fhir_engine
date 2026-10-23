from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_TESTSCRIPT_DIR = Path("testscripts")


@dataclass(frozen=True)
class FixtureDef:
    id: str
    reference: str | None
    autocreate: bool = False
    autodelete: bool = False


@dataclass(frozen=True)
class OperationDef:
    id: str
    label: str
    method: str
    url: str
    type_code: str | None = None
    resource: str | None = None
    params: str | None = None
    explicit_url: bool = False
    source_id: str | None = None
    request_id: str | None = None
    response_id: str | None = None
    target_id: str | None = None
    accept: str | None = None
    content_type: str | None = None
    headers: tuple[tuple[str, str], ...] = ()
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AssertionDef:
    id: str
    label: str
    source_id: str | None = None
    response: str | None = None
    response_code: str | None = None
    resource: str | None = None
    content_type: str | None = None
    header_field: str | None = None
    operator: str = "equals"
    value: str | None = None
    path: str | None = None
    expression: str | None = None
    validate_profile_id: str | None = None
    direction: str = "response"
    request_method: str | None = None
    request_url: str | None = None
    warning_only: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScriptAction:
    id: str
    section: str
    test_name: str | None
    operation: OperationDef | None = None
    assertion: AssertionDef | None = None


@dataclass(frozen=True)
class LoadedTestScript:
    path: Path
    source: dict[str, Any]
    url: str | None
    name: str
    description: str | None
    fixtures: tuple[FixtureDef, ...]
    profiles: dict[str, str]
    actions: tuple[ScriptAction, ...]
    unsupported_elements: tuple[str, ...]

    @property
    def id(self) -> str:
        return self.url or self.name or self.path.stem


_OPERATION_METHODS = {
    "read": "GET",
    "vread": "GET",
    "search": "GET",
    "history": "GET",
    "create": "POST",
    "update": "PUT",
    "updatecreate": "PUT",
    "patch": "PATCH",
    "delete": "DELETE",
    "deletecondsingle": "DELETE",
    "deletecondmultiple": "DELETE",
    "batch": "POST",
    "transaction": "POST",
    "capabilities": "GET",
}


def _method(operation: dict[str, Any]) -> str:
    if operation.get("method"):
        return str(operation["method"]).upper()
    type_value = operation.get("type") or {}
    code = str(type_value.get("code") or "").lower()
    if code in _OPERATION_METHODS:
        return _OPERATION_METHODS[code]
    return "UNSUPPORTED"


def _media_type(value: str | None) -> str | None:
    if value is None:
        return None
    mapping = {
        "json": "application/fhir+json",
        "xml": "application/fhir+xml",
        "ttl": "text/turtle",
    }
    return mapping.get(str(value).lower(), str(value))


def _headers(operation: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    out: list[tuple[str, str]] = []
    for item in operation.get("requestHeader") or []:
        field = item.get("field")
        value = item.get("value")
        if field is not None and value is not None:
            out.append((str(field), str(value)))
    return tuple(out)


def _operation_def(
    operation: dict[str, Any],
    action_id: str,
) -> OperationDef:
    explicit_url = bool(operation.get("url"))
    url = operation.get("url")
    resource = operation.get("resource")
    params = str(operation.get("params") or "")
    type_value = operation.get("type") or {}
    code = str(type_value.get("code") or "").lower() or None

    if not url:
        if code == "capabilities":
            url = "/metadata"
        elif code in {"batch", "transaction"} and not resource:
            url = "/"
        elif resource:
            url = f"/{resource}{params}"
        else:
            # Preserve valid-but-not-yet-executable operation types so the
            # loader can report UNSUPPORTED instead of rejecting the TestScript.
            url = "/"

    return OperationDef(
        id=action_id,
        label=str(operation.get("label") or action_id),
        method=_method(operation),
        url=str(url),
        type_code=code,
        resource=str(resource) if resource is not None else None,
        params=params or None,
        explicit_url=explicit_url,
        source_id=operation.get("sourceId"),
        request_id=operation.get("requestId"),
        response_id=operation.get("responseId"),
        target_id=operation.get("targetId"),
        accept=_media_type(operation.get("accept")),
        content_type=_media_type(operation.get("contentType")),
        headers=_headers(operation),
        raw=dict(operation),
    )


def _assertion_def(
    assertion: dict[str, Any],
    action_id: str,
) -> AssertionDef:
    return AssertionDef(
        id=action_id,
        label=str(
            assertion.get("label")
            or assertion.get("description")
            or action_id
        ),
        source_id=assertion.get("sourceId"),
        response=assertion.get("response"),
        response_code=assertion.get("responseCode"),
        resource=assertion.get("resource"),
        content_type=_media_type(assertion.get("contentType")),
        header_field=assertion.get("headerField"),
        operator=str(assertion.get("operator") or "equals"),
        value=(
            str(assertion["value"])
            if assertion.get("value") is not None
            else None
        ),
        path=assertion.get("path"),
        expression=assertion.get("expression"),
        validate_profile_id=assertion.get("validateProfileId"),
        direction=str(assertion.get("direction") or "response"),
        request_method=assertion.get("requestMethod"),
        request_url=assertion.get("requestURL"),
        warning_only=bool(assertion.get("warningOnly", False)),
        raw=dict(assertion),
    )


def _parse_actions(
    items: list[dict[str, Any]],
    *,
    section: str,
    test_name: str | None = None,
    prefix: str,
) -> list[ScriptAction]:
    actions: list[ScriptAction] = []
    for index, action in enumerate(items, start=1):
        action_id = str(action.get("id") or f"{prefix}-{index:02d}")
        if isinstance(action.get("operation"), dict):
            actions.append(
                ScriptAction(
                    id=action_id,
                    section=section,
                    test_name=test_name,
                    operation=_operation_def(
                        action["operation"],
                        action_id,
                    ),
                )
            )
        elif isinstance(action.get("assert"), dict):
            actions.append(
                ScriptAction(
                    id=action_id,
                    section=section,
                    test_name=test_name,
                    assertion=_assertion_def(
                        action["assert"],
                        action_id,
                    ),
                )
            )
        else:
            raise ValueError(
                f"{action_id}: action has neither operation nor assert"
            )
    return actions


def _unsupported(source: dict[str, Any]) -> list[str]:
    unsupported: list[str] = []
    for key in ("variable", "rule", "ruleset"):
        if source.get(key):
            unsupported.append(key)

    metadata = source.get("metadata") or {}
    if metadata.get("capability"):
        unsupported.append("metadata.capability")

    for index, fixture in enumerate(source.get("fixture") or [], start=1):
        if fixture.get("autocreate"):
            unsupported.append(f"fixture[{index}].autocreate")
        if fixture.get("autodelete"):
            unsupported.append(f"fixture[{index}].autodelete")
        reference = (fixture.get("resource") or {}).get("reference")
        if isinstance(reference, str) and reference.startswith(("http://", "https://")):
            unsupported.append(f"fixture[{index}].remote-resource")

    if len(source.get("origin") or []) > 1:
        unsupported.append("multiple origin")
    if len(source.get("destination") or []) > 1:
        unsupported.append("multiple destination")

    for section_name, actions in _iter_raw_actions(source):
        for index, action in enumerate(actions, start=1):
            operation = action.get("operation")
            assertion = action.get("assert")
            if isinstance(operation, dict):
                type_value = operation.get("type") or {}
                type_code = str(type_value.get("code") or "").lower()
                if (
                    not operation.get("method")
                    and type_code
                    and type_code not in _OPERATION_METHODS
                ):
                    unsupported.append(
                        f"{section_name}.action[{index}].operation.type={type_code}"
                    )
                if (
                    not operation.get("method")
                    and not type_code
                ):
                    unsupported.append(
                        f"{section_name}.action[{index}].operation.method"
                    )
                for key in ("origin", "destination"):
                    if operation.get(key) not in (None, False, 0):
                        unsupported.append(
                            f"{section_name}.action[{index}].operation.{key}"
                        )
                if operation.get("encodeRequestUrl") is False:
                    unsupported.append(
                        f"{section_name}.action[{index}].operation.encodeRequestUrl=false"
                    )
            if isinstance(assertion, dict):
                for key in (
                    "compareToSourceId",
                    "compareToSourceExpression",
                    "compareToSourcePath",
                    "minimumId",
                    "navigationLinks",
                    "warningOnly",
                ):
                    if assertion.get(key) not in (None, False):
                        unsupported.append(
                            f"{section_name}.action[{index}].assert.{key}"
                        )
                if assertion.get("expression"):
                    unsupported.append(
                        f"{section_name}.action[{index}].assert.expression"
                    )
                if assertion.get("validateProfileId"):
                    unsupported.append(
                        f"{section_name}.action[{index}].assert.validateProfileId"
                    )
    return sorted(set(unsupported))


def _iter_raw_actions(
    source: dict[str, Any],
):
    setup = source.get("setup") or {}
    yield "setup", setup.get("action") or []
    for index, test in enumerate(source.get("test") or [], start=1):
        yield f"test[{index}]", test.get("action") or []
    teardown = source.get("teardown") or {}
    yield "teardown", teardown.get("action") or []


def load_testscript(path: str | Path) -> LoadedTestScript:
    path = Path(path)
    source = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(source, dict):
        raise ValueError(f"{path}: TestScript must be a JSON object")
    if source.get("resourceType") != "TestScript":
        raise ValueError(f"{path}: resourceType must be TestScript")

    fixtures: list[FixtureDef] = []
    for index, fixture in enumerate(source.get("fixture") or [], start=1):
        resource = fixture.get("resource") or {}
        fixtures.append(
            FixtureDef(
                id=str(fixture.get("id") or f"fixture-{index}"),
                reference=resource.get("reference"),
                autocreate=bool(fixture.get("autocreate", False)),
                autodelete=bool(fixture.get("autodelete", False)),
            )
        )

    profiles: dict[str, str] = {}
    for index, profile in enumerate(source.get("profile") or [], start=1):
        if not isinstance(profile, dict):
            continue
        profile_id = str(profile.get("id") or f"profile-{index}")
        reference = profile.get("reference")
        if isinstance(reference, dict):
            reference = reference.get("reference")
        if reference:
            profiles[profile_id] = str(reference)

    actions: list[ScriptAction] = []
    setup = source.get("setup") or {}
    actions.extend(
        _parse_actions(
            setup.get("action") or [],
            section="setup",
            prefix="setup",
        )
    )

    for test_index, test in enumerate(source.get("test") or [], start=1):
        test_name = str(test.get("name") or f"test-{test_index}")
        actions.extend(
            _parse_actions(
                test.get("action") or [],
                section="test",
                test_name=test_name,
                prefix=f"test-{test_index}",
            )
        )

    teardown = source.get("teardown") or {}
    actions.extend(
        _parse_actions(
            teardown.get("action") or [],
            section="teardown",
            prefix="teardown",
        )
    )

    return LoadedTestScript(
        path=path,
        source=source,
        url=source.get("url"),
        name=str(source.get("name") or path.stem),
        description=source.get("description"),
        fixtures=tuple(fixtures),
        profiles=profiles,
        actions=tuple(actions),
        unsupported_elements=tuple(_unsupported(source)),
    )


def list_testscripts(
    root: str | Path = DEFAULT_TESTSCRIPT_DIR,
) -> list[Path]:
    root = Path(root)
    if not root.is_dir():
        return []
    paths: list[Path] = []
    for path in sorted(root.rglob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(value, dict) and value.get("resourceType") == "TestScript":
            paths.append(path)
    return paths
