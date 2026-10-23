"""SHN client-file selection shared by the unified local Streamlit pages.

The user selects a path on the machine running Streamlit, not the browser.
The app retains only a path in session state, never the JSON or credentials.
No process-global environment changes are made from UI interactions.
"""
from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
SHN_CLIENT_PATH_KEY = "_medilacra_shn_client_json_path"
SHN_CLIENT_INPUT_KEY = "_medilacra_shn_client_json_path_widget"

# Workbench local credentials and the historical MVP-0 default are both
# gitignored and deliberately NOT loaded into the repository.
WORKBENCH_DEFAULT = ROOT / "apps/workbench/config/credentials/local/secrets/shn-client.json"
MVP0_DEFAULT = ROOT / "apps/mvp0/connectathon/shn_live_baseline_00301/client.json"


def _normalize(path: str | Path) -> Path:
    candidate = Path(os.path.expandvars(str(path))).expanduser()
    # Legacy pages temporarily change the working directory. Interpret a
    # relative UI path from the stable repository root, never page-by-page.
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return candidate.resolve()


def default_shn_client_path() -> Path:
    """Honor deployment env, then existing local installs, then suggest a path."""
    configured = os.getenv("SHN_CLIENT_FILE")
    if configured:
        return _normalize(configured)
    if WORKBENCH_DEFAULT.is_file():
        return WORKBENCH_DEFAULT
    if MVP0_DEFAULT.is_file():
        return MVP0_DEFAULT
    return WORKBENCH_DEFAULT


def selected_shn_client_path(state: Mapping[str, Any]) -> Path:
    return _normalize(state.get(SHN_CLIENT_PATH_KEY) or default_shn_client_path())


def inspect_shn_client(path: str | Path) -> tuple[bool, str]:
    """Return only validity/status, never the contents of the secret JSON."""
    path = _normalize(path)
    if not path.is_file():
        return False, "File not found on the Streamlit server."
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False, "Unable to read a valid JSON object at this path."
    if not isinstance(data, dict) or not data.get("client_id") or not data.get("client_secret"):
        return False, "JSON must contain non-empty client_id and client_secret fields."
    return True, "Client JSON found with both required keys. OAuth has not been tested."


def with_shn_client_path(profile: Any, path: str | Path) -> Any:
    """Override SHN profile sources only; leave other auth methods untouched."""
    if getattr(profile, "id", None) != "shn-provider-client-secret":
        return profile
    if profile.client_id is None or profile.client_secret is None:
        raise ValueError("SHN profile must define both client_id and client_secret sources")
    absolute = str(_normalize(path))
    return replace(
        profile,
        client_id=replace(profile.client_id, source="json_file", env=None, path=absolute, key="client_id"),
        client_secret=replace(profile.client_secret, source="json_file", env=None, path=absolute, key="client_secret"),
    )
