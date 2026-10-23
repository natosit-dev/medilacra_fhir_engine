"""Plain-language descriptions of the actual Workbench TestScript semantics.

Results here document what the existing implementation checks; they are not
a statement of complete FHIR conformance or certification.
"""
from __future__ import annotations
from typing import Any


ACTION_STATES = {
    "EXECUTED": "The HTTP operation completed without a transport error. This does not establish HTTP success, valid content, or business correctness; the underlying operation state is PASS.",
    "PASS": "An explicit TestScript assertion met its expectation. A successful operation is displayed as EXECUTED instead.",
    "FAIL": "An explicit assertion or an automatic validation check did not match its expected value.",
    "ERROR": "The step could not be completed or evaluated, for example because of missing credentials, a transport error or unparseable JSON.",
    "UNSUPPORTED": "The TestScript requested functionality not implemented by this runner. No passing result is claimed.",
    "SKIP": "An inapplicable or unimplemented check was not performed. Currently most visible SKIPs come from automatic FHIR validation.",
}

VALIDATION_STATES = {
    "PASS": "A basic FHIR response check passed (e.g., JSON parsing or a declared resourceType/profile). This is not full StructureDefinition conformance validation.",
    "FAIL": "A basic FHIR check found a mismatch against its configured expectation.",
    "ERROR": "The response looked like FHIR JSON, but the basic validator could not parse it.",
    "SKIP": "FHIR checking was not applicable or was unimplemented: ordinary CDS Hooks JSON is not FHIR JSON, and FHIR XML validation is not implemented.",
    "None / blank": "No validation result was produced for this row. Assertion rows and operations that stopped early normally have no automatic validation.",
}

EVENT_PHASES = {
    "run": "The whole test run started or finished.",
    "configuration": "The system, credential profile, script or feature-support setting was recorded.",
    "fixture": "A file or resource needed as test input was loaded.",
    "authentication": "Credentials or a token were requested, acquired, reused, expired or rejected.",
    "transport": "An HTTP request was sent/blocked, a response arrived, or a retry was scheduled.",
    "operation": "A TestScript HTTP operation started or completed.",
    "validation": "The basic FHIR response validator started or reported a result.",
    "assertion": "An expected-vs-observed check defined by the TestScript was evaluated.",
    "persistence": "An evidence file or a configuration snapshot was written.",
}



def action_label(action: Any) -> str:
    """Return a display label from the nested operation/assertion definition.

    ScriptAction itself has no 'label' field. The original TestScript runner
    has always used these nested labels, including its step selector.
    """
    operation = getattr(action, "operation", None)
    if operation is not None:
        return operation.label
    assertion = getattr(action, "assertion", None)
    if assertion is not None:
        return assertion.label
    return getattr(action, "id", "Unnamed action")

def describe_action(action: Any) -> str:
    """Describe precisely the operation or assertion loaded from a TestScript."""
    operation = getattr(action, "operation", None)
    assertion = getattr(action, "assertion", None)

    if operation is not None:
        method, path = operation.method, operation.url
        if method == "GET" and path.rstrip("/") == "/cds-services":
            return (
                "Retrieve the CDS Hooks service listing from the endpoint. "
                "This does not test whether any individual CDS service returns "
                "a correct clinical decision."
            )
        if method == "GET" and path.rstrip("/") == "/metadata":
            return (
                "Request the FHIR CapabilityStatement (advertised server capabilities). "
                "This does not prove that each advertised capability works."
            )
        payload = " using its configured input fixture" if operation.source_id else ""
        return (
            f"Send HTTP {method} to {path}{payload} and capture the response. "
            "Executing the request alone is not an assertion that the result is correct."
        )

    if assertion is None:
        return "This action has no supported request or assertion."
    direction = assertion.direction or "response"
    operator = assertion.operator or "equals"
    if assertion.warning_only:
        return "Warning-only assertions are not implemented in this runner (UNSUPPORTED)."
    if assertion.expression:
        return "FHIRPath expression assertions are not implemented in this runner (UNSUPPORTED)."
    if assertion.validate_profile_id:
        return "Full StructureDefinition profile validation is not implemented (UNSUPPORTED)."
    if assertion.request_method is not None:
        return f"Compare the outgoing HTTP method with {assertion.request_method} using '{operator}'."
    if assertion.request_url is not None:
        return f"Compare the outgoing request URL with {assertion.request_url} using '{operator}'."
    if assertion.response_code is not None:
        return f"Check the HTTP response status against {assertion.response_code} using '{operator}'."
    if assertion.response is not None:
        return f"Check the HTTP response status against the named TestScript outcome '{assertion.response}'."
    if assertion.content_type is not None:
        return f"Check the {direction} Content-Type against {assertion.content_type} using '{operator}'."
    if assertion.header_field is not None:
        if assertion.value is None:
            return f"Check that the {direction} includes header '{assertion.header_field}'."
        return f"Check the {direction} header '{assertion.header_field}' against its expected value."
    if assertion.resource is not None:
        return f"Check that the {direction} JSON resourceType is {assertion.resource} using '{operator}'."
    if assertion.path is not None:
        field = assertion.path
        if assertion.value is None and operator not in {"empty", "notEmpty"}:
            return (
                f"Check that JSON field/path '{field}' is present. "
                "This does not assert that a list is nonempty or that its contents are valid."
            )
        if assertion.value is None:
            return f"Check JSON field/path '{field}' using '{operator}'."
        return f"Compare JSON field/path '{field}' to the expected value using '{operator}'."
    return (
        "Evaluate this TestScript assertion; inspect its assertion details "
        "for the precise expected and observed values."
    )


def describe_scope(script: Any) -> str:
    operations = sum(a.operation is not None for a in script.actions)
    checks = sum(a.assertion is not None for a in script.actions)
    return (
        f"This script defines {operations} HTTP operation(s) and {checks} explicit "
        "assertion(s). A passing result applies only to the checks actually "
        "performed; it is not certification of the whole endpoint."
    )


# What the "Acquire/Prepare Credentials" button actually does.
# Authentication acceptance is a separate check made by a protected endpoint.
AUTH_PREPARATION_HELP = {
    "none": (
        "No credentials are needed. Prepares an unauthenticated request; "
        "does not contact the server."
    ),
    "basic": (
        "Reads the configured username and password and prepares an HTTP Basic "
        "Authorization header. Does not verify the server accepts them."
    ),
    "bearer": (
        "Reads an existing bearer token and prepares an Authorization header. "
        "Does not request a new token or verify access."
    ),
    "oauth2_client_credentials": (
        "Reads the client ID and secret from the configured source, requests "
        "a fresh OAuth access token, and keeps it in memory. This does not "
        "test access to protected API operations."
    ),
}
