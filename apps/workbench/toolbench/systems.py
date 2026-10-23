from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_SYSTEM_DIR = Path("config/systems")


def _expand(value: Any) -> Any:
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, list):
        return [_expand(item) for item in value]
    if isinstance(value, dict):
        return {key: _expand(item) for key, item in value.items()}
    return value


@dataclass(frozen=True)
class TLSConfig:
    verify: bool = True
    ca_bundle: str | None = None
    client_cert: str | None = None
    client_key: str | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "TLSConfig":
        value = value or {}
        return cls(
            verify=bool(value.get("verify", True)),
            ca_bundle=value.get("ca_bundle"),
            client_cert=value.get("client_cert"),
            client_key=value.get("client_key"),
        )

    @property
    def requests_verify(self) -> bool | str:
        return self.ca_bundle or self.verify

    @property
    def requests_cert(self) -> str | tuple[str, str] | None:
        if self.client_cert and self.client_key:
            return (self.client_cert, self.client_key)
        return self.client_cert


@dataclass(frozen=True)
class CorrelationConfig:
    request_header: str | None = None
    response_header: str | None = None
    leg_header: str | None = None
    trace_url_template: str | None = None
    generate_uuid: bool = False

    @classmethod
    def from_dict(
        cls,
        value: dict[str, Any] | None,
    ) -> "CorrelationConfig":
        value = value or {}
        return cls(
            request_header=value.get("request_header"),
            response_header=value.get("response_header"),
            leg_header=value.get("leg_header"),
            trace_url_template=value.get("trace_url_template"),
            generate_uuid=bool(value.get("generate_uuid", False)),
        )


@dataclass(frozen=True)
class RetryConfig:
    max_retries: int = 0
    statuses: tuple[int, ...] = (429,)
    default_retry_after_seconds: int = 65

    @classmethod
    def from_dict(
        cls,
        value: dict[str, Any] | None,
    ) -> "RetryConfig":
        value = value or {}
        return cls(
            max_retries=int(value.get("max_retries", 0)),
            statuses=tuple(
                int(status)
                for status in (value.get("statuses") or [429])
            ),
            default_retry_after_seconds=int(
                value.get("default_retry_after_seconds", 65)
            ),
        )


@dataclass(frozen=True)
class TestSystem:
    id: str
    name: str
    base_url: str
    protocol: str = "fhir"
    fhir_version: str | None = None
    format: str = "json"
    credential_profile: str | None = None
    test_path: str = "/metadata"
    tls: TLSConfig = field(default_factory=TLSConfig)
    identity: dict[str, Any] = field(default_factory=dict)
    default_headers: dict[str, str] = field(default_factory=dict)
    sensitive_headers: tuple[str, ...] = ()
    correlation: CorrelationConfig = field(default_factory=CorrelationConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    notes: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TestSystem":
        data = _expand(value)
        identity = dict(data.get("identity") or {})
        sensitive = {
            str(header).lower()
            for header in (data.get("sensitive_headers") or [])
        }
        for key_name, header_name in (
            ("user_key", identity.get("user_key_header")),
            ("organization_key", identity.get("organization_key_header")),
        ):
            if identity.get(key_name) and header_name:
                sensitive.add(str(header_name).lower())

        return cls(
            id=str(data["id"]),
            name=str(data.get("name") or data["id"]),
            base_url=str(data.get("base_url") or "").rstrip("/"),
            protocol=str(data.get("protocol") or "fhir"),
            fhir_version=(
                str(data["fhir_version"])
                if data.get("fhir_version") is not None
                else None
            ),
            format=str(data.get("format") or "json"),
            credential_profile=data.get("credential_profile"),
            test_path=str(data.get("test_path") or "/metadata"),
            tls=TLSConfig.from_dict(data.get("tls")),
            identity=identity,
            default_headers={
                str(key): str(val)
                for key, val in (data.get("default_headers") or {}).items()
            },
            sensitive_headers=tuple(sorted(sensitive)),
            correlation=CorrelationConfig.from_dict(
                data.get("correlation")
            ),
            retry=RetryConfig.from_dict(data.get("retry")),
            notes=tuple(str(note) for note in data.get("notes") or []),
        )

    @property
    def configured(self) -> bool:
        return bool(self.base_url) and "${" not in self.base_url

    def headers(self) -> dict[str, str]:
        headers = dict(self.default_headers)
        user_key = self.identity.get("user_key")
        user_header = self.identity.get("user_key_header")
        org_key = self.identity.get("organization_key")
        org_header = self.identity.get("organization_key_header")
        if user_key and user_header:
            headers[str(user_header)] = str(user_key)
        if org_key and org_header:
            headers[str(org_header)] = str(org_key)
        return headers

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["sensitive_headers"] = list(self.sensitive_headers)
        value["notes"] = list(self.notes)
        return value


def load_system(path: str | Path) -> TestSystem:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: system config must be a JSON object")
    return TestSystem.from_dict(raw)


def list_systems(
    root: str | Path = DEFAULT_SYSTEM_DIR,
) -> list[TestSystem]:
    root = Path(root)
    if not root.is_dir():
        return []
    systems = [load_system(path) for path in sorted(root.glob("*.json"))]
    local = root / "local"
    if local.is_dir():
        systems.extend(load_system(path) for path in sorted(local.glob("*.json")))
    by_id: dict[str, TestSystem] = {}
    for system in systems:
        by_id[system.id] = system
    return sorted(by_id.values(), key=lambda item: item.name.lower())


def get_system(
    system_id: str,
    root: str | Path = DEFAULT_SYSTEM_DIR,
) -> TestSystem:
    for system in list_systems(root):
        if system.id == system_id:
            return system
    raise KeyError(f"unknown TestSystem {system_id!r}")
