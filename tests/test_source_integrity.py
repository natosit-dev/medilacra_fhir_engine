"""Verify harvested source bytes against their original Git blob identities.

The harvest manifest records blob hashes from natosit-dev/medilacra at
the fixed commit 2202e0b. This test needs no network, credentials or Git.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "harvest-manifest.json"


def _git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}".encode("ascii") + bytes([0]) + data).hexdigest()


def test_pinned_harvest_blob_hashes():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["source_commit"] == "2202e0b5503b60eaffba5e6ff0341df143a58008"
    assert len(manifest["entries"]) == 47

    for entry in manifest["entries"]:
        path = ROOT / entry["engine_path"]
        assert path.is_file(), f"missing source: {path}"
        actual = _git_blob_sha1(path.read_bytes())
        assert actual == entry["source_blob_sha"], f"source drift: {path}"


def test_harvest_does_not_include_transport_or_secret_files():
    forbidden = [
        "src/connectathon/shn_provider/client.py",
        "src/connectathon/shn_provider/workflow.py",
        "src/connectathon/shn_provider/reference_suite.py",
        "src/connectathon/shn_live_baseline_00301/client.json",
    ]
    assert all(not (ROOT / rel).exists() for rel in forbidden)
