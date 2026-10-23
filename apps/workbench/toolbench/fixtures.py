from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .testscript import LoadedTestScript


class FixtureStore:
    def __init__(self, script: LoadedTestScript) -> None:
        self.script = script
        self._static: dict[str, Any] = {}
        self._dynamic: dict[str, Any] = {}
        self._load_static()

    def _load_static(self) -> None:
        base = self.script.path.parent
        for fixture in self.script.fixtures:
            if not fixture.reference:
                continue
            reference = fixture.reference
            if reference.startswith(("http://", "https://")):
                # Remote fixture acquisition is intentionally not implicit.
                continue
            path = (base / reference).resolve()
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            try:
                value = json.loads(text)
            except json.JSONDecodeError:
                value = text
            self._static[fixture.id] = value

    def get(self, fixture_id: str | None) -> Any:
        if not fixture_id:
            return None
        if fixture_id in self._dynamic:
            return self._dynamic[fixture_id]
        if fixture_id in self._static:
            return self._static[fixture_id]
        raise KeyError(f"fixture {fixture_id!r} is not available")

    def put(self, fixture_id: str | None, value: Any) -> None:
        if fixture_id:
            self._dynamic[fixture_id] = value

    def available_ids(self) -> list[str]:
        return sorted(set(self._static) | set(self._dynamic))
