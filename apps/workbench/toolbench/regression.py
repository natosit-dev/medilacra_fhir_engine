from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Difference:
    path: str
    baseline: Any
    current: Any

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "baseline": self.baseline,
            "current": self.current,
        }


def compare_runs(
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, Any]:
    differences: list[Difference] = []

    _compare_value(
        differences,
        "status",
        baseline.get("status"),
        current.get("status"),
    )

    baseline_actions = {
        str(action.get("action_id")): action
        for action in baseline.get("actions") or []
        if isinstance(action, dict) and action.get("action_id")
    }
    current_actions = {
        str(action.get("action_id")): action
        for action in current.get("actions") or []
        if isinstance(action, dict) and action.get("action_id")
    }

    all_ids = sorted(set(baseline_actions) | set(current_actions))
    for action_id in all_ids:
        old = baseline_actions.get(action_id)
        new = current_actions.get(action_id)
        if old is None or new is None:
            differences.append(
                Difference(
                    f"actions.{action_id}",
                    old,
                    new,
                )
            )
            continue

        _compare_value(
            differences,
            f"actions.{action_id}.state",
            old.get("state"),
            new.get("state"),
        )

        old_transport = old.get("transport") or {}
        new_transport = new.get("transport") or {}
        _compare_value(
            differences,
            f"actions.{action_id}.http_status",
            old_transport.get("status_code"),
            new_transport.get("status_code"),
        )

        old_assertion = old.get("assertion") or {}
        new_assertion = new.get("assertion") or {}
        _compare_value(
            differences,
            f"actions.{action_id}.assertion.state",
            old_assertion.get("state"),
            new_assertion.get("state"),
        )
        _compare_value(
            differences,
            f"actions.{action_id}.assertion.observed",
            old_assertion.get("observed"),
            new_assertion.get("observed"),
        )

        old_validation = {
            str(row.get("name")): row
            for row in old.get("validation") or []
            if isinstance(row, dict)
        }
        new_validation = {
            str(row.get("name")): row
            for row in new.get("validation") or []
            if isinstance(row, dict)
        }
        for name in sorted(set(old_validation) | set(new_validation)):
            _compare_value(
                differences,
                f"actions.{action_id}.validation.{name}",
                old_validation.get(name),
                new_validation.get(name),
            )

    latency = []
    for action_id in all_ids:
        old = baseline_actions.get(action_id) or {}
        new = current_actions.get(action_id) or {}
        old_ms = (old.get("transport") or {}).get("elapsed_ms")
        new_ms = (new.get("transport") or {}).get("elapsed_ms")
        if isinstance(old_ms, (int, float)) and isinstance(new_ms, (int, float)):
            latency.append(
                {
                    "action_id": action_id,
                    "baseline_ms": old_ms,
                    "current_ms": new_ms,
                    "delta_ms": round(new_ms - old_ms, 1),
                }
            )

    return {
        "baseline_run_id": baseline.get("run_id"),
        "current_run_id": current.get("run_id"),
        "difference_count": len(differences),
        "differences": [difference.as_dict() for difference in differences],
        "latency": latency,
    }


def _compare_value(
    differences: list[Difference],
    path: str,
    baseline: Any,
    current: Any,
) -> None:
    if baseline != current:
        differences.append(Difference(path, baseline, current))


def save_comparison(
    comparison: dict[str, Any],
    root: str | Path = "results/comparisons",
) -> Path:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    baseline = _slug(str(comparison.get("baseline_run_id") or "baseline"))
    current = _slug(str(comparison.get("current_run_id") or "current"))
    path = root / f"{baseline}-vs-{current}.json"
    path.write_text(
        json.dumps(comparison, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return path


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-").lower() or "run"
