from __future__ import annotations

import json
from copy import deepcopy
from typing import Any


SENSITIVE_BODY_KEYS = {
    "client_secret",
    "access_token",
    "refresh_token",
    "id_token",
    "bearer_token",
    "client_assertion",
    "private_key",
    "password",
    "api_key",
    "apikey",
}


def normalized_key(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_")


def sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[Any, Any] = {}
        for key, child in value.items():
            if normalized_key(key) in SENSITIVE_BODY_KEYS:
                out[key] = "<redacted>"
            else:
                out[key] = sanitize_value(child)
        return out
    if isinstance(value, list):
        return [sanitize_value(item) for item in value]
    return deepcopy(value)


def sanitize_jsonish_text(value: str | None) -> str | None:
    if value is None or not value.strip():
        return value
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value
    sanitized = sanitize_value(parsed)
    if sanitized == parsed:
        return value
    return json.dumps(sanitized, separators=(",", ":"), sort_keys=True)


def body_was_redacted(value: str | None) -> bool:
    if value is None:
        return False
    return sanitize_jsonish_text(value) != value


def sanitize_testscript_source(
    source: dict[str, Any],
    sensitive_headers: set[str] | None = None,
) -> dict[str, Any]:
    sanitized = sanitize_value(source)
    sensitive = {
        "authorization",
        "proxy-authorization",
        "cookie",
        *(header.lower() for header in (sensitive_headers or set())),
    }

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            request_headers = node.get("requestHeader")
            if isinstance(request_headers, list):
                for header in request_headers:
                    if not isinstance(header, dict):
                        continue
                    field = str(header.get("field") or "").lower()
                    if field in sensitive and "value" in header:
                        header["value"] = "<redacted>"
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(sanitized)
    return sanitized


def sanitize_system_config(
    value: dict[str, Any],
) -> dict[str, Any]:
    sanitized = deepcopy(value)
    identity = sanitized.get("identity")
    if isinstance(identity, dict):
        for key in ("user_key", "organization_key"):
            if identity.get(key) is not None:
                identity[key] = "<redacted>"

    sensitive = {
        "authorization",
        "proxy-authorization",
        "cookie",
        *(
            str(header).lower()
            for header in sanitized.get("sensitive_headers") or []
        ),
    }
    headers = sanitized.get("default_headers")
    if isinstance(headers, dict):
        for key in list(headers):
            if str(key).lower() in sensitive:
                headers[key] = "<redacted>"
    return sanitize_value(sanitized)
