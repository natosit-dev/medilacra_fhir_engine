"""Published Da Vinci DTR output parameter names across supported IG versions.

DTR 2.0.1: PackageBundle, operationOutcome
DTR 2.2.0: packagebundle, outcome

FHIR JSON member names and resourceType values remain case-sensitive.
Only these published operation-parameter literals have explicit aliases.
"""

from __future__ import annotations

from typing import Any

DTR_PACKAGE_NAMES = frozenset({"PackageBundle", "packagebundle"})
DTR_OUTCOME_NAMES = frozenset({"operationOutcome", "outcome"})


def dtr_package_parameters(body: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        param for param in body.get("parameter", [])
        if isinstance(param, dict) and param.get("name") in DTR_PACKAGE_NAMES
    ]


def dtr_package_bundles(body: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        resource for param in dtr_package_parameters(body)
        if isinstance((resource := param.get("resource")), dict)
    ]


def dtr_outcome_parameters(body: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        param for param in body.get("parameter", [])
        if isinstance(param, dict) and param.get("name") in DTR_OUTCOME_NAMES
    ]
