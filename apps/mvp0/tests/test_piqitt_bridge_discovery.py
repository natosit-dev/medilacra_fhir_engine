"""PIQITT checkout discovery after embedding MediLacra under apps/mvp0/."""
from __future__ import annotations

from pathlib import Path

import pytest

from connectathon import piqitt_bridge as bridge


def _fake_layout(tmp_path: Path, monkeypatch) -> Path:
    workspace = tmp_path / "workspace"
    bridge_file = (
        workspace / "medilacra_fhir_engine" / "apps" / "mvp0"
        / "connectathon" / "piqitt_bridge.py"
    )
    bridge_file.parent.mkdir(parents=True)
    bridge_file.write_text("# test-only module location\n")
    monkeypatch.setattr(bridge, "__file__", str(bridge_file))
    monkeypatch.delenv("PIQITT_REPO", raising=False)
    return workspace


def _converter(repo: Path) -> Path:
    script = repo / "scripts" / "fhir_convert_backend.py"
    script.parent.mkdir(parents=True)
    script.write_text("def split_messages(text): return []\n")
    return script


def test_discovers_workspace_sibling_checkout(tmp_path, monkeypatch):
    workspace = _fake_layout(tmp_path, monkeypatch)
    script = _converter(workspace / "piqitt")
    assert bridge.default_piqitt_repo() == script.parents[1]
    assert bridge.backend_path() == script


def test_discovers_embedded_checkout_if_no_sibling(tmp_path, monkeypatch):
    workspace = _fake_layout(tmp_path, monkeypatch)
    script = _converter(workspace / "medilacra_fhir_engine" / "piqitt")
    assert bridge.default_piqitt_repo() == script.parents[1]


def test_legacy_apps_checkout_is_still_supported(tmp_path, monkeypatch):
    workspace = _fake_layout(tmp_path, monkeypatch)
    script = _converter(workspace / "medilacra_fhir_engine" / "apps" / "piqitt")
    assert bridge.default_piqitt_repo() == script.parents[1]


def test_explicit_environment_override_has_precedence(tmp_path, monkeypatch):
    workspace = _fake_layout(tmp_path, monkeypatch)
    _converter(workspace / "piqitt")
    custom = workspace / "custom-piqitt"
    _converter(custom)
    monkeypatch.setenv("PIQITT_REPO", str(custom))
    assert bridge.default_piqitt_repo() == custom
    assert bridge.backend_path() == custom / "scripts" / "fhir_convert_backend.py"


def test_missing_checkout_points_to_expected_workspace_path(tmp_path, monkeypatch):
    workspace = _fake_layout(tmp_path, monkeypatch)
    assert bridge.default_piqitt_repo() == workspace / "piqitt"
    with pytest.raises(FileNotFoundError, match="Clone https://github.com/natosit-dev/piqitt"):
        bridge.load_backend()
