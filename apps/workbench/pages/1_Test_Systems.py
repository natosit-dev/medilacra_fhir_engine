from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from toolbench.systems import list_systems


st.set_page_config(
    page_title="Workbench — Test Systems",
    page_icon="🧭",
    layout="wide",
)

st.title("🧭 Test Systems")
st.info(
    "TestSystem defines the **intended target** (endpoint, protocol, credentials, "
    "TLS, retry, and correlation settings). **Configured** only indicates "
    "a base URL is present; a green Save/Create message means local JSON "
    "was written. Neither demonstrates a working connection. "
    "Use Connection Lab and TestScript Runner to verify behavior."
)

st.caption(
    "Endpoint configuration is separate from TestScript definitions. "
    "Built-in configs are read here; edits are saved as local gitignored overrides."
)

systems = list_systems()
if not systems:
    st.warning("No TestSystem configs found.")
    st.stop()

by_id = {system.id: system for system in systems}
selected_id = st.selectbox(
    "TestSystem",
    list(by_id),
    format_func=lambda system_id: by_id[system_id].name,
)
system = by_id[selected_id]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Protocol", system.protocol)
c2.metric("FHIR", system.fhir_version or "—")
c3.metric("TLS verify", str(system.tls.verify))
c4.metric("Configured", "yes" if system.configured else "no")

st.markdown("**Base URL**")
st.code(system.base_url or "<not configured>", language=None)

if system.notes:
    st.markdown("\n".join(f"- {note}" for note in system.notes))

st.markdown("### Configuration")
raw = json.dumps(system.as_dict(), indent=2, sort_keys=True)
edited = st.text_area(
    "JSON",
    value=raw,
    height=500,
    key=f"system-json-{system.id}",
)

if st.button("Save as local override", use_container_width=True):
    try:
        value = json.loads(edited)
        if not isinstance(value, dict):
            raise ValueError("configuration must be a JSON object")
        if value.get("id") != system.id:
            raise ValueError("local override must keep the same system id")
        path = Path("config/systems/local") / f"{system.id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        st.success(f"Saved {path}")
    except Exception as exc:
        st.exception(exc)


st.divider()
st.markdown("### Create local TestSystem")
new_template = {
    "id": "new-system",
    "name": "New Test System",
    "base_url": "https://example.org/fhir",
    "protocol": "fhir",
    "fhir_version": "4.0.1",
    "format": "json",
    "credential_profile": "none",
    "test_path": "/metadata",
    "tls": {
        "verify": True,
        "ca_bundle": None,
        "client_cert": None,
        "client_key": None,
    },
    "identity": {
        "user_key_header": None,
        "user_key": None,
        "organization_key_header": None,
        "organization_key": None,
    },
    "default_headers": {
        "Accept": "application/fhir+json"
    },
}
new_json = st.text_area(
    "New system JSON",
    json.dumps(new_template, indent=2),
    height=420,
    key="new-system-json",
)
if st.button("Create local TestSystem", use_container_width=True):
    try:
        value = json.loads(new_json)
        if not isinstance(value, dict):
            raise ValueError("configuration must be a JSON object")
        system_id = str(value.get("id") or "").strip()
        if not system_id:
            raise ValueError("id is required")
        path = Path("config/systems/local") / f"{system_id}.json"
        if path.exists():
            raise FileExistsError(
                f"{path} already exists; edit the existing system instead"
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        st.success(f"Created {path}")
    except Exception as exc:
        st.exception(exc)
