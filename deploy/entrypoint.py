"""MediLacra container entrypoint: initialize writable seeds and JSON stdout.

This is operational logging; it deliberately does not transform test evidence or
promise that arbitrary third-party tracebacks cannot contain sensitive content.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import uuid

SOURCE_ROOT = Path("/opt/medilacra")
SEED_ROOT = Path("/opt/medilacra_seed")

# Do not output lines with obvious credential material. This is a defensive
# filter, not a substitute for preventing credentials/payloads being logged.
CREDENTIAL_MARKERS = re.compile(
    r"(?i)(authorization\s*[:=]|bearer\s+[a-z0-9._~-]+|"
    r"access[_-]?token|client[_-]?secret|private[_-]?key|"
    r"password\s*[:=]|set-cookie\s*[:=])"
)


def emit(event_type: str, data: dict | None = None) -> dict:
    event = {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "service": "medilacra",
        "instance_id": os.getenv("MEDILACRA_INSTANCE_ID", "unknown"),
        "host_port": os.getenv("MEDILACRA_HOST_PORT", "unknown"),
        "source_ref": os.getenv("MEDILACRA_SOURCE_REF", "unknown"),
        "data": data or {},
    }
    print(json.dumps(event, ensure_ascii=False, sort_keys=True), flush=True)
    return event


def initialize_seeds() -> None:
    """Populate empty bind-mounted cache/input paths without replacing edits."""
    for relative in ("apps/mvp0/input", "apps/mvp0/data"):
        source = SEED_ROOT / relative
        target = SOURCE_ROOT / relative
        if not source.exists():
            continue
        target.mkdir(parents=True, exist_ok=True)
        for file in source.rglob("*"):
            if not file.is_file() or file.is_symlink():
                continue
            dest = target / file.relative_to(source)
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file, dest)


def safe_line(raw: str) -> str:
    return "[suppressed: potential credential material]" if CREDENTIAL_MARKERS.search(raw) else raw.rstrip("\r\n")[:2000]


def main() -> int:
    initialize_seeds()
    command = [sys.executable, "-m", "streamlit", "run", "app.py",
               "--server.address", "0.0.0.0", "--server.port", "8501",
               "--server.headless", "true", "--browser.gatherUsageStats", "false"]
    emit("instance.starting", {"command": "streamlit", "internal_port": 8501})
    child = subprocess.Popen(command, cwd=SOURCE_ROOT, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, bufsize=1)

    def terminate(sig: int, _frame) -> None:
        emit("instance.stopping", {"signal": sig})
        if child.poll() is None:
            child.send_signal(sig)

    signal.signal(signal.SIGTERM, terminate)
    signal.signal(signal.SIGINT, terminate)
    assert child.stdout is not None
    for line in child.stdout:
        emit("process.output", {"message": safe_line(line)})
    rc = child.wait()
    emit("instance.stopped", {"exit_code": rc})
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
