"""Run original Streamlit entrypoints without changing their source yet.

Compatibility layer for M-003, NOT the final execution architecture.
Streamlit pages in both apps rely on root-relative paths and absolute imports.
We preserve those assumptions only while each page is executing.

Warning: os.chdir() is process-wide. Concurrent sessions and background workers
can interfere with it. This launcher is intended for single-user local use
until path handling is refactored. It does not provide process isolation.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import sys
import threading
from typing import Iterator


ROOT = Path(__file__).resolve().parents[1]
_APP_ROOTS = (ROOT / "apps" / "workbench", ROOT / "apps" / "mvp0")
_PAGE_LOCK = threading.RLock()


def configure_import_paths() -> None:
    """Give bundled applications priority over the frozen source harvest.

    Specifically, MVP-0's original connectathon/ and hl7_demo/ modules must
    win over the byte-identical compatibility harvest under src/. This is a
    deliberate first-stage behavior and will be removed after E-001 parity.
    """
    for directory in reversed(_APP_ROOTS):
        path = str(directory)
        if path in sys.path:
            sys.path.remove(path)
        sys.path.insert(0, path)


@contextmanager
def page_directory(directory: Path) -> Iterator[None]:
    """Restore the original working directory even on a Streamlit rerun/error."""
    directory = directory.resolve()
    with _PAGE_LOCK:
        previous = Path.cwd()
        try:
            os.chdir(directory)
            yield
        finally:
            os.chdir(previous)


def execute_existing_page(relative_source: str) -> None:
    """Execute an original app/page in its owning application's environment."""
    source = (ROOT / relative_source).resolve()
    if not source.is_relative_to(ROOT / "apps") or not source.is_file():
        raise FileNotFoundError(f"Not a registered original application file: {relative_source}")

    if relative_source.startswith("apps/workbench/"):
        app_root = ROOT / "apps" / "workbench"
    elif relative_source.startswith("apps/mvp0/"):
        app_root = ROOT / "apps" / "mvp0"
    else:
        raise ValueError(f"Unsupported legacy page root: {relative_source}")

    configure_import_paths()
    code = compile(source.read_bytes(), str(source), "exec")
    namespace = {
        "__name__": "__main__",
        "__file__": str(source),
        "__package__": None,
    }
    with page_directory(app_root):
        exec(code, namespace)
