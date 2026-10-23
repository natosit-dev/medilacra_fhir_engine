from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

import streamlit as st

from toolbench.auth import AuthManager
from toolbench.explain import AUTH_PREPARATION_HELP
from toolbench.credentials import get_profile, list_profiles
from toolbench.systems import list_systems
from toolbench.transport import TransportClient
from unified.shn_credentials import (
    SHN_CLIENT_PATH_KEY,
    SHN_CLIENT_INPUT_KEY,
    default_shn_client_path,
    inspect_shn_client,
    selected_shn_client_path,
    with_shn_client_path,
)


st.set_page_config(
    page_title="Workbench — Auth",
    page_icon="🔐",
    layout="wide",
)

st.title("🔐 Auth Workbench")
st.caption(
    "IRIS basic authentication uses IRIS_FHIR_USER and IRIS_FHIR_PASSWORD "
    "from the Streamlit process environment."
)

st.caption(
    "Acquire and test authentication independently from TestScript execution. "
    "Credential and token values are not displayed or persisted."
)

st.subheader("SHN client JSON")
st.caption(
    "Enter an absolute path on the machine running Streamlit. "
    "Do not paste the JSON or its secret values. This setting applies to "
    "the SHN ePA page and the Workbench TestScript Runner in this browser session."
)
# Streamlit clears widget-owned state when navigating to another page.
# Keep a durable, non-widget session key for the selected client path.
if SHN_CLIENT_PATH_KEY not in st.session_state:
    st.session_state[SHN_CLIENT_PATH_KEY] = str(default_shn_client_path())
if SHN_CLIENT_INPUT_KEY not in st.session_state:
    st.session_state[SHN_CLIENT_INPUT_KEY] = st.session_state[SHN_CLIENT_PATH_KEY]


def _save_shn_client_path() -> None:
    st.session_state[SHN_CLIENT_PATH_KEY] = st.session_state[SHN_CLIENT_INPUT_KEY]


st.text_input(
    "SHN client JSON file path",
    key=SHN_CLIENT_INPUT_KEY,
    on_change=_save_shn_client_path,
    help="Example: /home/user/.config/medilacra/shn-client.json. "
         "For unattended startup, set SHN_CLIENT_FILE before launching Streamlit.",
)
shn_client_file = selected_shn_client_path(st.session_state)
ready, reason = inspect_shn_client(shn_client_file)
if ready:
    st.success(reason)
else:
    st.warning(reason)
st.caption("File validation checks structure only. For SHN, use Acquire/Prepare Credentials to request an OAuth token.")

systems = list_systems()
system_by_id = {system.id: system for system in systems}
system_id = st.selectbox(
    "TestSystem",
    list(system_by_id),
    format_func=lambda value: system_by_id[value].name,
)
system = system_by_id[system_id]

profiles = list_profiles()
profile_by_id = {profile.id: profile for profile in profiles}
default_profile = system.credential_profile or "none"
profile_ids = list(profile_by_id)
default_index = (
    profile_ids.index(default_profile)
    if default_profile in profile_ids
    else 0
)
profile_id = st.selectbox(
    "CredentialProfile",
    profile_ids,
    index=default_index,
    format_func=lambda value: profile_by_id[value].name,
)
profile = with_shn_client_path(profile_by_id[profile_id], shn_client_file)

with st.expander("Credential profile definition"):
    profile_json = json.dumps(asdict(profile), indent=2, sort_keys=True)
    edited_profile = st.text_area(
        "Profile JSON",
        profile_json,
        height=360,
        key=f"credential-profile-json:{profile.id}",
    )
    if st.button(
        "Save credential profile as local override",
        key=f"save-credential-profile:{profile.id}",
        use_container_width=True,
    ):
        try:
            value = json.loads(edited_profile)
            if not isinstance(value, dict):
                raise ValueError("credential profile must be a JSON object")
            if value.get("id") != profile.id:
                raise ValueError("local override must keep the same profile id")
            path = Path("config/credentials/local") / f"{profile.id}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(value, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            st.success(f"Saved {path}")
        except Exception as exc:
            st.exception(exc)

with st.expander("Create local CredentialProfile"):
    credential_template = {
        "id": "new-credential-profile",
        "name": "New Credential Profile",
        "type": "none",
    }
    new_profile_json = st.text_area(
        "New profile JSON",
        json.dumps(credential_template, indent=2),
        height=220,
        key="new-credential-profile-json",
    )
    if st.button(
        "Create local CredentialProfile",
        key="create-local-credential-profile",
        use_container_width=True,
    ):
        try:
            value = json.loads(new_profile_json)
            if not isinstance(value, dict):
                raise ValueError("credential profile must be a JSON object")
            new_id = str(value.get("id") or "").strip()
            if not new_id:
                raise ValueError("id is required")
            path = Path("config/credentials/local") / f"{new_id}.json"
            if path.exists():
                raise FileExistsError(
                    f"{path} already exists; edit the existing profile instead"
                )
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(value, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            st.success(f"Created {path}")
        except Exception as exc:
            st.exception(exc)

# A path change must not reuse the OAuth manager/token from another client.
manager_key = f"auth-manager:{system.id}:{profile.id}:{shn_client_file if profile.id == 'shn-provider-client-secret' else ''}"
manager = st.session_state.get(manager_key)
if manager is None:
    manager = AuthManager(system, profile)
    st.session_state[manager_key] = manager

st.code(
    f"system={system.id}\nauth={profile.type}\nbase={system.base_url}",
    language=None,
)

c1, c2 = st.columns(2)
with c1:
    if st.button("Acquire/Prepare Credentials", type="primary", use_container_width=True):
        status = manager.acquire(force=True)
        st.session_state[f"auth-status:{manager_key}"] = status
    st.caption(
        AUTH_PREPARATION_HELP.get(
            profile.type,
            "Unsupported authentication type; review the selected CredentialProfile.",
        )
    )
with c2:
    if st.button(
        "Test authenticated request",
        use_container_width=True,
        disabled=not system.configured,
    ):
        try:
            client = TransportClient(system, manager)
            response = client.request("GET", system.test_path)
            st.session_state[f"auth-test:{manager_key}"] = response
        except Exception as exc:
            st.exception(exc)

status = st.session_state.get(f"auth-status:{manager_key}") or manager.status()
st.markdown("### Auth state")
st.json(
    {
        "profile_id": status.profile_id,
        "auth_type": status.auth_type,
        "active": status.active,
        "token_http_status": status.token_http_status,
        "expires_in_seconds": status.expires_in_seconds,
        "scope": status.scope,
        "error": status.error,
    },
    expanded=True,
)

response = st.session_state.get(f"auth-test:{manager_key}")
if response:
    st.markdown("### Authenticated request")
    st.code(
        f"{response.method} {response.url}\n"
        f"HTTP {response.status_code} {response.reason or ''}\n"
        f"{response.elapsed_ms:.1f} ms",
        language=None,
    )
    st.markdown("**Request headers**")
    st.code(
        "\n".join(f"{k}: {v}" for k, v in response.request_headers.items()),
        language=None,
    )
    st.markdown("**Response headers**")
    st.code(
        "\n".join(f"{k}: {v}" for k, v in response.response_headers.items()),
        language=None,
    )
    st.markdown("**Response body**")
    st.code(response.response_text or "<empty>", language=None)
