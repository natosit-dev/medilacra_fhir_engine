"""Configurable experimental timing assessment (not a normative SLA)."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "timing.json"
METRICS = {"request_elapsed_ms", "elapsed_ms"}


def load_timing_config(path: str | Path | None = None) -> dict[str, Any]:
    source = Path(path or os.getenv("SHN_TIMING_CONFIG", str(DEFAULT_CONFIG_PATH)))
    config = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or not isinstance(config.get("enabled"), bool):
        raise ValueError("timing configuration requires boolean enabled")
    rules = config.get("rules")
    if not isinstance(rules, dict):
        raise ValueError("timing configuration requires rules object")
    for name, rule in rules.items():
        if not isinstance(rule, dict) or rule.get("metric") not in METRICS:
            raise ValueError(f"invalid timing rule/metric for {name!r}")
        for key in ("warn_ms", "fail_ms"):
            value = rule.get(key)
            if value is not None and (type(value) not in (int, float) or value < 0):
                raise ValueError(f"{name}.{key} must be nonnegative or null")
        warn, fail = rule.get("warn_ms"), rule.get("fail_ms")
        if warn is not None and fail is not None and warn > fail:
            raise ValueError(f"{name}: warn_ms cannot exceed fail_ms")
    return config


def assess_timing(
    path: str,
    *,
    elapsed_ms: float,
    request_elapsed_ms: float | None,
    config: dict[str, Any],
) -> dict[str, Any]:
    rule = (config.get("rules") or {}).get(path)
    if rule is None:
        return {"status": "DISABLED", "path": path, "reason": "no configured rule"}
    metric = rule["metric"]
    measured = (
        request_elapsed_ms if metric == "request_elapsed_ms" else elapsed_ms
    )
    if not config.get("enabled"):
        status = "DISABLED"
    elif measured is None:
        status = "NOT_MEASURED"
    elif rule.get("fail_ms") is not None and measured > rule["fail_ms"]:
        status = "FAIL"
    elif rule.get("warn_ms") is not None and measured > rule["warn_ms"]:
        status = "WARN"
    else:
        status = "PASS"
    return {
        "status": status,
        "path": path,
        "metric": metric,
        "observed_ms": round(measured, 1) if measured is not None else None,
        "warn_ms": rule.get("warn_ms"),
        "fail_ms": rule.get("fail_ms"),
        "source": config.get("source", "local experiment configuration"),
    }
