from __future__ import annotations

import json
from typing import Any

from jsonpath_ng.ext import parse as parse_jsonpath


def deep_get(obj: Any, path: str) -> list[Any]:
    if not path:
        return [obj]

    current: list[Any] = [obj]
    for raw_part in path.split("."):
        if raw_part.endswith("[x]"):
            stem = raw_part[:-3]
            next_values: list[Any] = []
            for node in current:
                if isinstance(node, dict):
                    next_values.extend(
                        value
                        for key, value in node.items()
                        if key.startswith(stem) and key != stem
                    )
            current = next_values
            continue

        star = raw_part.endswith("*")
        key = raw_part[:-1] if star else raw_part
        next_values = []
        for node in current:
            if isinstance(node, dict) and key in node:
                value = node[key]
                if star and isinstance(value, list):
                    next_values.extend(value)
                else:
                    next_values.append(value)
            elif isinstance(node, list):
                for item in node:
                    if isinstance(item, dict) and key in item:
                        value = item[key]
                        if star and isinstance(value, list):
                            next_values.extend(value)
                        else:
                            next_values.append(value)
        current = next_values
    return current


def parse_json(text: str) -> Any:
    return json.loads(text)


def parse_fhir_resource(text: str) -> dict[str, Any]:
    value = parse_json(text)
    if not isinstance(value, dict):
        raise ValueError("FHIR response is not a JSON object")
    resource_type = value.get("resourceType")
    if not isinstance(resource_type, str) or not resource_type:
        raise ValueError("JSON object has no FHIR resourceType")
    return value


def meta_profiles(resource: dict[str, Any]) -> list[str]:
    meta = resource.get("meta") or {}
    profiles = meta.get("profile") or []
    if isinstance(profiles, str):
        return [profiles]
    return [str(profile) for profile in profiles]


class UnsupportedPathError(ValueError):
    pass


def jsonpath_values(obj: Any, path: str) -> list[Any]:
    """Evaluate the JSONPath subset used by TestScript.path.

    FHIR TestScript.path may be XPath or JSONPath. The Workbench v0.1
    intentionally supports JSONPath only; XPath is surfaced as unsupported
    instead of being reinterpreted through the PIQITT dotted-path helper.
    """
    expression = (path or "").strip()
    if not expression:
        return []
    if (
        expression.startswith("/")
        or expression.startswith("//")
        or "f:" in expression
        or "@value" in expression
    ):
        raise UnsupportedPathError(
            "XPath TestScript.path is not implemented in v0.1"
        )
    if not expression.startswith("$"):
        expression = "$." + expression.lstrip(".")
    try:
        parsed = parse_jsonpath(expression)
    except Exception as exc:
        raise UnsupportedPathError(
            f"unsupported/invalid JSONPath: {path}"
        ) from exc
    return [match.value for match in parsed.find(obj)]
