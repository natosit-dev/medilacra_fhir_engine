from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import uuid
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOG_SCHEMA_VERSION = "0.1"

BLOCKED_KEYS = {
    "authorization_header",
    "authorization_value",
    "http_authorization",
    "client_secret",
    "access_token",
    "bearer_token",
    "basic_credential",
    "private_key",
    "client_assertion",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalized_key(key: Any) -> str:
    return str(key).strip().lower().replace("-", "_")


def assert_no_sensitive_keys(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if _normalized_key(key) in BLOCKED_KEYS:
                if child == "<redacted>":
                    continue
                raise ValueError(
                    f"sensitive key {key!r} cannot be persisted at {path}"
                )
            assert_no_sensitive_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_no_sensitive_keys(child, f"{path}[{index}]")


def write_json(path: str | Path, value: Any) -> Path:
    path = Path(path)
    assert_no_sensitive_keys(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return path


def write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> Path:
    path = Path(path)
    assert_no_sensitive_keys(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
    return path


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(args: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except Exception:
        return None
    value = completed.stdout.strip()
    return value or None


def execution_context(mode: str) -> dict[str, Any]:
    status = _git(["status", "--porcelain"])
    return {
        "execution_mode": mode,
        "git_branch": _git(["rev-parse", "--abbrev-ref", "HEAD"]),
        "git_commit": _git(["rev-parse", "HEAD"]),
        "git_dirty": bool(status) if status is not None else None,
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform_system": platform.system(),
        "platform_release": platform.release(),
        "log_schema_version": LOG_SCHEMA_VERSION,
    }


@dataclass
class RunLogger:
    run_id: str
    testscript_id: str
    system_id: str
    execution_mode: str = "python"

    def __post_init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.sequence = 0
        self.operation_id: str | None = None
        self.context = execution_context(self.execution_mode)

    def set_operation(self, operation_id: str | None) -> None:
        self.operation_id = operation_id

    def emit(
        self,
        event_type: str,
        phase: str,
        data: dict[str, Any] | None = None,
        *,
        operation_id: str | None = None,
        artifact_refs: list[str] | None = None,
    ) -> dict[str, Any]:
        self.sequence += 1
        event = {
            "schema_version": LOG_SCHEMA_VERSION,
            "event_id": str(uuid.uuid4()),
            "run_id": self.run_id,
            "sequence": self.sequence,
            "timestamp": utc_now(),
            "event_type": event_type,
            "testscript_id": self.testscript_id,
            "system_id": self.system_id,
            "operation_id": (
                self.operation_id
                if operation_id is None
                else operation_id
            ),
            "phase": phase,
            "data": deepcopy(data or {}),
            "artifact_refs": list(artifact_refs or []),
        }
        assert_no_sensitive_keys(event)
        self.events.append(event)
        return event
