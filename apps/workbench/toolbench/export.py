from __future__ import annotations

import csv
import io
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_RESULTS_ROOT = Path("results")


@dataclass(frozen=True)
class StoredRun:
    path: Path
    run: dict[str, Any]

    @property
    def run_id(self) -> str:
        return str(self.run.get("run_id") or self.path.name)


def discover_runs(
    root: str | Path = DEFAULT_RESULTS_ROOT,
) -> list[StoredRun]:
    root = Path(root)
    if not root.is_dir():
        return []
    runs: list[StoredRun] = []
    for path in sorted(root.glob("*/run.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, dict):
            runs.append(StoredRun(path=path.parent, run=value))
    runs.sort(key=lambda item: str(item.run.get("started_at") or ""))
    return runs


def run_zip_bytes(run_dir: str | Path) -> bytes:
    run_dir = Path(run_dir)
    if not run_dir.is_dir():
        raise FileNotFoundError(run_dir)
    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "README.txt",
            "MediLacra SHN Workbench execution evidence.\n"
            "Credential values and Authorization header values are excluded.\n",
        )
        for path in sorted(run_dir.rglob("*")):
            if path.is_file() and "export" not in path.parts:
                archive.write(path, path.relative_to(run_dir).as_posix())
    return buffer.getvalue()


def _transactions(run: StoredRun) -> list[dict[str, Any]]:
    path = run.path / "transactions.jsonl"
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


def _events(run: StoredRun) -> list[dict[str, Any]]:
    path = run.path / "events.jsonl"
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


def collection_zip_bytes(
    runs: Iterable[StoredRun],
) -> tuple[bytes, dict[str, Any]]:
    runs = list(runs)
    transactions: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    run_rows: list[dict[str, Any]] = []

    for stored in runs:
        tx = _transactions(stored)
        ev = _events(stored)
        transactions.extend(tx)
        events.extend(ev)
        run_rows.append(
            {
                "run_id": stored.run_id,
                "testscript_id": stored.run.get("testscript_id"),
                "system_id": stored.run.get("system_id"),
                "credential_profile_id": stored.run.get("credential_profile_id"),
                "status": stored.run.get("status"),
                "passed": stored.run.get("passed"),
                "started_at": stored.run.get("started_at"),
                "completed_at": stored.run.get("completed_at"),
                "duration_ms": stored.run.get("duration_ms"),
                "transaction_count": len(tx),
                "event_count": len(ev),
            }
        )

    events.sort(
        key=lambda event: (
            str(event.get("timestamp") or ""),
            str(event.get("run_id") or ""),
            int(event.get("sequence") or 0),
        )
    )
    for index, event in enumerate(events, start=1):
        event["collection_sequence"] = index

    collection_id = (
        "toolbench-transaction-logs-"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )
    manifest = {
        "collection_id": collection_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "run_count": len(runs),
            "transaction_count": len(transactions),
            "event_count": len(events),
            "passed_runs": sum(row["passed"] is True for row in run_rows),
            "failed_runs": sum(row["passed"] is False for row in run_rows),
        },
        "runs": run_rows,
    }

    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "README.txt",
            "MediLacra SHN Workbench multi-run evidence bundle.\n"
            "Preparing this archive sends no network traffic.\n",
        )
        archive.writestr(
            "collection.json",
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        )
        archive.writestr(
            "transactions.jsonl",
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in transactions),
        )
        archive.writestr(
            "events.jsonl",
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in events),
        )
        archive.writestr(
            "transactions.csv",
            _transactions_csv(transactions),
        )
        for stored in runs:
            prefix = Path("runs") / stored.run_id
            for path in sorted(stored.path.rglob("*")):
                if path.is_file():
                    archive.write(
                        path,
                        (prefix / path.relative_to(stored.path)).as_posix(),
                    )

        if runs:
            comparisons_dir = runs[0].path.parent / "comparisons"
            if comparisons_dir.is_dir():
                for path in sorted(comparisons_dir.glob("*.json")):
                    archive.write(
                        path,
                        (Path("comparisons") / path.name).as_posix(),
                    )
    return buffer.getvalue(), manifest


def _transactions_csv(rows: list[dict[str, Any]]) -> str:
    columns = [
        "run_id",
        "testscript_id",
        "system_id",
        "action_id",
        "section",
        "test_name",
        "method",
        "url",
        "status_code",
        "elapsed_ms",
        "correlation_id",
        "response_correlation_id",
        "leg_id",
        "trace_url",
        "error",
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=columns,
        extrasaction="ignore",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()
