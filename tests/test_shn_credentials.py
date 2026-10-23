"""SHN client-path override is per Streamlit session and never stores secrets."""
import json
from dataclasses import dataclass
from pathlib import Path

from unified.shn_credentials import (
    SHN_CLIENT_PATH_KEY,
    SHN_CLIENT_INPUT_KEY,
    inspect_shn_client,
    selected_shn_client_path,
    with_shn_client_path,
)


@dataclass(frozen=True)
class Source:
    source: str
    path: str
    key: str
    env: str | None = None


@dataclass(frozen=True)
class Profile:
    id: str
    client_id: Source
    client_secret: Source


def test_status_reports_valid_without_returning_secrets(tmp_path):
    secret = tmp_path / "client.json"
    secret.write_text(json.dumps({"client_id": "secret-id", "client_secret": "secret-value"}))
    ready, status = inspect_shn_client(secret)
    assert ready
    assert "secret-id" not in status and "secret-value" not in status
    assert "OAuth has not been tested" in status


def test_missing_or_invalid_file_has_clear_status(tmp_path):
    assert inspect_shn_client(tmp_path / "missing.json")[0] is False
    invalid = tmp_path / "bad.json"
    invalid.write_text(json.dumps({"client_id": "only-id"}))
    assert inspect_shn_client(invalid)[0] is False


def test_selected_path_is_per_session(tmp_path):
    p1 = tmp_path / "user-one.json"
    p2 = tmp_path / "user-two.json"
    assert selected_shn_client_path({SHN_CLIENT_PATH_KEY: str(p1)}) == p1
    assert selected_shn_client_path({SHN_CLIENT_PATH_KEY: str(p2)}) == p2


def test_override_only_changes_shn_profile(tmp_path):
    orig = Profile(
        id="shn-provider-client-secret",
        client_id=Source("json_file", "/old/path", "client_id", "SHN_CLIENT_FILE"),
        client_secret=Source("json_file", "/old/path", "client_secret", "SHN_CLIENT_FILE"),
    )
    path = tmp_path / "new-client.json"
    modified = with_shn_client_path(orig, path)
    assert modified is not orig
    assert modified.client_id.path == str(path)
    assert modified.client_secret.path == str(path)
    assert modified.client_id.env is None and modified.client_secret.env is None
    assert orig.client_id.path == "/old/path"
    iris = Profile(id="iris-basic", client_id=orig.client_id, client_secret=orig.client_secret)
    assert with_shn_client_path(iris, path) is iris


def test_durable_path_key_differs_from_widget_key(tmp_path):
    state = {SHN_CLIENT_PATH_KEY: str(tmp_path / "selected.json")}
    assert SHN_CLIENT_PATH_KEY != SHN_CLIENT_INPUT_KEY
    # Streamlit can delete the input widget on navigation, but durable key survives.
    state[SHN_CLIENT_INPUT_KEY] = "discard-me"
    state.pop(SHN_CLIENT_INPUT_KEY)
    assert selected_shn_client_path(state) == tmp_path / "selected.json"


def test_relative_selected_path_is_stable_across_working_directories(tmp_path, monkeypatch):
    from unified.shn_credentials import ROOT
    state = {SHN_CLIENT_PATH_KEY: "my-secrets/client.json"}
    monkeypatch.chdir(tmp_path)
    assert selected_shn_client_path(state) == ROOT / "my-secrets/client.json"
