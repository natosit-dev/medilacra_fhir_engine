from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_CREDENTIAL_DIR = Path("config/credentials")


@dataclass(frozen=True)
class ValueSource:
    source: str
    env: str | None = None
    path: str | None = None
    key: str | None = None

    @classmethod
    def from_dict(
        cls,
        value: dict[str, Any] | None,
    ) -> "ValueSource | None":
        if not value:
            return None
        return cls(
            source=str(value.get("source") or ""),
            env=value.get("env"),
            path=value.get("path"),
            key=value.get("key"),
        )

    def resolve(self) -> str:
        if self.source == "env":
            if not self.env:
                raise ValueError("env source requires env")
            value = os.getenv(self.env)
            if value is None:
                raise ValueError(f"environment variable {self.env} is not set")
            return value

        if self.source == "json_file":
            # An optional environment variable names the file path, not a
            # credential value. Prefer it to the profile's fallback path.
            configured_path = os.getenv(self.env) if self.env else None
            selected_path = configured_path or self.path
            if not selected_path or not self.key:
                raise ValueError("json_file source requires path and key")
            path = Path(os.path.expandvars(selected_path)).expanduser()
            data = json.loads(path.read_text(encoding="utf-8"))
            value = data.get(self.key)
            if value is None:
                raise ValueError(f"{path}: missing key {self.key}")
            return str(value)

        raise ValueError(f"unsupported value source {self.source!r}")


@dataclass(frozen=True)
class CredentialProfile:
    id: str
    name: str
    type: str
    token_url: str | None = None
    auth_style: str = "basic"
    scope: str | None = None
    client_id: ValueSource | None = None
    client_secret: ValueSource | None = None
    username: ValueSource | None = None
    password: ValueSource | None = None
    bearer_token: ValueSource | None = None
    token_extra_fields: dict[str, str] = field(default_factory=dict)
    notes: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CredentialProfile":
        return cls(
            id=str(value["id"]),
            name=str(value.get("name") or value["id"]),
            type=str(value.get("type") or "none"),
            token_url=value.get("token_url"),
            auth_style=str(value.get("auth_style") or "basic"),
            scope=value.get("scope"),
            client_id=ValueSource.from_dict(value.get("client_id")),
            client_secret=ValueSource.from_dict(value.get("client_secret")),
            username=ValueSource.from_dict(value.get("username")),
            password=ValueSource.from_dict(value.get("password")),
            bearer_token=ValueSource.from_dict(value.get("bearer_token")),
            token_extra_fields={
                str(key): str(val)
                for key, val in (value.get("token_extra_fields") or {}).items()
            },
            notes=tuple(str(note) for note in value.get("notes") or []),
        )


def load_profile(path: str | Path) -> CredentialProfile:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: credential profile must be a JSON object")
    return CredentialProfile.from_dict(raw)


def list_profiles(
    root: str | Path = DEFAULT_CREDENTIAL_DIR,
) -> list[CredentialProfile]:
    root = Path(root)
    if not root.is_dir():
        return []
    paths = list(sorted(root.glob("*.json")))
    examples = root / "examples"
    if examples.is_dir():
        paths.extend(sorted(examples.glob("*.json")))
    local = root / "local"
    if local.is_dir():
        paths.extend(sorted(local.glob("*.json")))
    by_id: dict[str, CredentialProfile] = {}
    for path in paths:
        profile = load_profile(path)
        by_id[profile.id] = profile
    return sorted(by_id.values(), key=lambda item: item.name.lower())


def get_profile(
    profile_id: str,
    root: str | Path = DEFAULT_CREDENTIAL_DIR,
) -> CredentialProfile:
    for profile in list_profiles(root):
        if profile.id == profile_id:
            return profile
    raise KeyError(f"unknown CredentialProfile {profile_id!r}")
