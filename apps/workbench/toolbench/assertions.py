from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlsplit

from .fhir import UnsupportedPathError, jsonpath_values
from .testscript import AssertionDef
from .transport import TransportResult


PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"
UNSUPPORTED = "UNSUPPORTED"
ERROR = "ERROR"


@dataclass(frozen=True)
class AssertionResult:
    assertion_id: str
    label: str
    state: str
    expected: Any = None
    observed: Any = None
    message: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


_RESPONSE_CODES = {
    "okay": 200,
    "created": 201,
    "noContent": 204,
    "notModified": 304,
    "bad": 400,
    "forbidden": 403,
    "notFound": 404,
    "methodNotAllowed": 405,
    "conflict": 409,
    "gone": 410,
    "preconditionFailed": 412,
    "unprocessable": 422,
}


def _compare(
    observed: Any,
    expected: Any,
    operator: str,
) -> bool:
    operator = operator or "equals"
    if operator == "equals":
        return observed == expected
    if operator == "notEquals":
        return observed != expected
    if operator == "contains":
        if isinstance(observed, (list, tuple, set)):
            return expected in observed
        return str(expected) in str(observed)
    if operator == "notContains":
        if isinstance(observed, (list, tuple, set)):
            return expected not in observed
        return str(expected) not in str(observed)
    if operator == "in":
        values = (
            list(expected)
            if isinstance(expected, (list, tuple, set))
            else [item.strip() for item in str(expected).split(",")]
        )
        return observed in values or str(observed) in {str(item) for item in values}
    if operator == "notIn":
        values = (
            list(expected)
            if isinstance(expected, (list, tuple, set))
            else [item.strip() for item in str(expected).split(",")]
        )
        return observed not in values and str(observed) not in {str(item) for item in values}
    if operator == "greaterThan":
        return float(observed) > float(expected)
    if operator == "lessThan":
        return float(observed) < float(expected)
    if operator == "notEmpty":
        return observed not in (None, "", [], {})
    if operator == "empty":
        return observed in (None, "", [], {})
    raise ValueError(f"unsupported assertion operator {operator!r}")


def _json_body(response: TransportResult) -> tuple[Any, str | None]:
    try:
        return response.json_body(), None
    except Exception as exc:
        return None, str(exc)


def evaluate_assertion(
    assertion: AssertionDef,
    response: TransportResult | None,
    *,
    profiles: dict[str, str] | None = None,
) -> AssertionResult:
    if response is None:
        return AssertionResult(
            assertion.id,
            assertion.label,
            ERROR,
            message="no response is available for this assertion",
        )

    if assertion.warning_only:
        return AssertionResult(
            assertion.id,
            assertion.label,
            UNSUPPORTED,
            expected=True,
            message="warningOnly=true semantics are not implemented in v0.1",
        )

    unsupported_fields = [
        key
        for key in (
            "compareToSourceId",
            "compareToSourceExpression",
            "compareToSourcePath",
            "minimumId",
            "navigationLinks",
        )
        if assertion.raw.get(key) not in (None, False)
    ]
    if unsupported_fields:
        return AssertionResult(
            assertion.id,
            assertion.label,
            UNSUPPORTED,
            expected=unsupported_fields,
            message=(
                "assertion uses TestScript semantics not implemented in v0.1: "
                + ", ".join(unsupported_fields)
            ),
        )

    direction = (assertion.direction or "response").lower()
    if direction not in {"request", "response"}:
        return AssertionResult(
            assertion.id,
            assertion.label,
            UNSUPPORTED,
            expected=assertion.direction,
            message="unsupported assertion direction",
        )

    if assertion.request_method is not None:
        observed = response.method.upper()
        expected = str(assertion.request_method).upper()
        try:
            passed = _compare(observed, expected, assertion.operator)
        except ValueError as exc:
            return AssertionResult(
                assertion.id,
                assertion.label,
                UNSUPPORTED,
                expected=assertion.operator,
                observed=observed,
                message=str(exc),
            )
        return AssertionResult(
            assertion.id,
            assertion.label,
            PASS if passed else FAIL,
            expected=expected,
            observed=observed,
            message="request method",
        )

    if assertion.request_url is not None:
        if response.request_target:
            observed = response.request_target
        else:
            parts = urlsplit(response.url)
            observed = parts.path + (f"?{parts.query}" if parts.query else "")
        expected = str(assertion.request_url)
        try:
            passed = _compare(observed, expected, assertion.operator)
        except ValueError as exc:
            return AssertionResult(
                assertion.id,
                assertion.label,
                UNSUPPORTED,
                expected=assertion.operator,
                observed=observed,
                message=str(exc),
            )
        return AssertionResult(
            assertion.id,
            assertion.label,
            PASS if passed else FAIL,
            expected=expected,
            observed=observed,
            message="request URL",
        )

    if assertion.expression:
        return AssertionResult(
            assertion.id,
            assertion.label,
            UNSUPPORTED,
            expected=assertion.expression,
            message="FHIRPath expression assertions are not implemented in v0.1",
        )

    if assertion.validate_profile_id:
        expected_profile = (profiles or {}).get(assertion.validate_profile_id)
        return AssertionResult(
            assertion.id,
            assertion.label,
            UNSUPPORTED,
            expected=expected_profile or assertion.validate_profile_id,
            message=(
                "validateProfileId requires actual StructureDefinition validation; "
                "v0.1 will not approximate it with meta.profile declaration checking"
            ),
        )

    if assertion.response_code is not None:
        if direction != "response":
            return AssertionResult(
                assertion.id,
                assertion.label,
                UNSUPPORTED,
                expected=assertion.response_code,
                message="responseCode applies to response assertions",
            )
        expected_codes = [
            int(item.strip())
            for item in str(assertion.response_code).split(",")
            if item.strip().isdigit()
        ]
        observed = response.status_code
        operator = assertion.operator or "equals"
        if operator == "equals":
            if len(expected_codes) != 1:
                return AssertionResult(
                    assertion.id,
                    assertion.label,
                    UNSUPPORTED,
                    expected=expected_codes,
                    observed=observed,
                    message="multiple responseCode values require operator=in or notIn",
                )
            passed = observed == expected_codes[0]
        elif operator == "in":
            passed = observed in expected_codes
        elif operator == "notIn":
            passed = observed not in expected_codes
        else:
            return AssertionResult(
                assertion.id,
                assertion.label,
                UNSUPPORTED,
                expected=operator,
                observed=observed,
                message="unsupported responseCode operator",
            )
        return AssertionResult(
            assertion.id,
            assertion.label,
            PASS if passed else FAIL,
            expected=expected_codes,
            observed=observed,
            message="HTTP response code",
        )

    if assertion.response is not None:
        expected_code = _RESPONSE_CODES.get(assertion.response)
        if expected_code is None:
            return AssertionResult(
                assertion.id,
                assertion.label,
                UNSUPPORTED,
                expected=assertion.response,
                observed=response.status_code,
                message="unsupported TestScript response code name",
            )
        try:
            passed = _compare(
                response.status_code,
                expected_code,
                assertion.operator,
            )
        except ValueError as exc:
            return AssertionResult(
                assertion.id,
                assertion.label,
                UNSUPPORTED,
                expected=assertion.operator,
                observed=response.status_code,
                message=str(exc),
            )
        return AssertionResult(
            assertion.id,
            assertion.label,
            PASS if passed else FAIL,
            expected=expected_code,
            observed=response.status_code,
            message=f"FHIR TestScript response={assertion.response}",
        )

    if assertion.content_type is not None:
        observed = ""
        headers = (
            response.request_headers
            if direction == "request"
            else response.response_headers
        )
        for key, value in headers.items():
            if key.lower() == "content-type":
                observed = value
                break
        observed_media = observed.split(";", 1)[0].strip()
        try:
            passed = _compare(
                observed_media.lower(),
                assertion.content_type.lower(),
                assertion.operator,
            )
        except ValueError as exc:
            return AssertionResult(
                assertion.id,
                assertion.label,
                UNSUPPORTED,
                expected=assertion.operator,
                observed=observed_media,
                message=str(exc),
            )
        return AssertionResult(
            assertion.id,
            assertion.label,
            PASS if passed else FAIL,
            expected=assertion.content_type,
            observed=observed_media,
            message=f"{direction} Content-Type",
        )

    if assertion.header_field is not None:
        observed = None
        headers = (
            response.request_headers
            if direction == "request"
            else response.response_headers
        )
        for key, value in headers.items():
            if key.lower() == assertion.header_field.lower():
                observed = value
                break
        if assertion.value is None:
            passed = observed is not None
        else:
            try:
                passed = _compare(
                    observed,
                    assertion.value,
                    assertion.operator,
                )
            except ValueError as exc:
                return AssertionResult(
                    assertion.id,
                    assertion.label,
                    UNSUPPORTED,
                    expected=assertion.operator,
                    observed=observed,
                    message=str(exc),
                )
        return AssertionResult(
            assertion.id,
            assertion.label,
            PASS if passed else FAIL,
            expected=(
                assertion.value
                if assertion.value is not None
                else f"header {assertion.header_field} present"
            ),
            observed=observed,
            message=f"{direction} header {assertion.header_field}",
        )

    if assertion.resource is not None:
        if direction == "request":
            try:
                body = json.loads(response.request_body or "")
                error = None
            except Exception as exc:
                body, error = None, str(exc)
        else:
            body, error = _json_body(response)
        observed = body.get("resourceType") if isinstance(body, dict) else None
        try:
            passed = _compare(
                observed,
                assertion.resource,
                assertion.operator,
            )
        except ValueError as exc:
            return AssertionResult(
                assertion.id,
                assertion.label,
                UNSUPPORTED,
                expected=assertion.operator,
                observed=observed,
                message=str(exc),
            )
        return AssertionResult(
            assertion.id,
            assertion.label,
            PASS if passed else FAIL,
            expected=assertion.resource,
            observed=observed,
            message=error or "FHIR resourceType",
        )

    if assertion.path is not None:
        if direction == "request":
            try:
                body = json.loads(response.request_body or "")
                error = None
            except Exception as exc:
                body, error = None, str(exc)
        else:
            body, error = _json_body(response)
        if error:
            return AssertionResult(
                assertion.id,
                assertion.label,
                ERROR,
                expected=assertion.value,
                observed=None,
                message=f"response is not JSON: {error}",
            )
        try:
            values = jsonpath_values(body, assertion.path)
        except UnsupportedPathError as exc:
            return AssertionResult(
                assertion.id,
                assertion.label,
                UNSUPPORTED,
                expected=assertion.path,
                observed=None,
                message=str(exc),
            )
        if assertion.value is None:
            if assertion.operator in {"empty", "notEmpty"}:
                passed = _compare(values, None, assertion.operator)
            else:
                passed = bool(values)
            observed: Any = values
        else:
            try:
                passed = any(
                    _compare(value, assertion.value, assertion.operator)
                    for value in values
                )
            except ValueError as exc:
                return AssertionResult(
                    assertion.id,
                    assertion.label,
                    UNSUPPORTED,
                    expected=assertion.operator,
                    observed=values,
                    message=str(exc),
                )
            observed = values
        return AssertionResult(
            assertion.id,
            assertion.label,
            PASS if passed else FAIL,
            expected=(
                assertion.value
                if assertion.value is not None
                else f"path {assertion.path} exists"
            ),
            observed=observed,
            message=f"path {assertion.path}",
        )

    return AssertionResult(
        assertion.id,
        assertion.label,
        UNSUPPORTED,
        expected=assertion.raw,
        message="assertion shape is valid but not implemented",
    )
