from __future__ import annotations

import json
import re
from pathlib import Path

import streamlit as st

from toolbench.credentials import list_profiles
from toolbench.export import run_zip_bytes
from toolbench.explain import (
    ACTION_STATES, VALIDATION_STATES, EVENT_PHASES,
    describe_action, describe_scope, action_label,
)
from toolbench.runner import TestScriptRunner
from toolbench.systems import list_systems
from toolbench.testscript import list_testscripts, load_testscript
from unified.shn_credentials import selected_shn_client_path, with_shn_client_path


st.set_page_config(
    page_title="Workbench — TestScript Runner",
    page_icon="🧪",
    layout="wide",
)

st.title("🧪 FHIR TestScript Runner")
st.caption(
    "Executes the supported TestScript subset without rewriting the source resource. "
    "Unsupported standard elements are surfaced explicitly."
)

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
profile_ids = list(profile_by_id)
default_profile_id = system.credential_profile or "none"
profile_index = (
    profile_ids.index(default_profile_id)
    if default_profile_id in profile_ids
    else 0
)
profile_id = st.selectbox(
    "CredentialProfile",
    profile_ids,
    index=profile_index,
    format_func=lambda value: profile_by_id[value].name,
)
selected_profile = with_shn_client_path(
    profile_by_id[profile_id],
    selected_shn_client_path(st.session_state),
)

with st.expander("Import TestScript JSON"):
    uploaded = st.file_uploader(
        "FHIR TestScript JSON",
        type=["json"],
        key="testscript-upload",
    )
    if uploaded is not None and st.button(
        "Save imported TestScript locally",
        use_container_width=True,
        key="save-imported-testscript",
    ):
        try:
            source = json.loads(uploaded.getvalue().decode("utf-8"))
            if not isinstance(source, dict) or source.get("resourceType") != "TestScript":
                raise ValueError("uploaded JSON must be a FHIR TestScript resource")
            raw_name = str(
                source.get("name")
                or source.get("id")
                or Path(uploaded.name).stem
                or "imported-testscript"
            )
            slug = re.sub(r"[^A-Za-z0-9._-]+", "-", raw_name).strip("-").lower()
            path = Path("testscripts/local") / f"{slug or 'imported-testscript'}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(source, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            st.success(f"Saved {path}")
            st.rerun()
        except Exception as exc:
            st.exception(exc)
    st.caption(
        "Relative fixture files can be placed beside the imported script under "
        "testscripts/local/. Imported files are gitignored."
    )

paths = list_testscripts()
path_by_label = {str(path): path for path in paths}
script_label = st.selectbox("TestScript", list(path_by_label))
script = load_testscript(path_by_label[script_label])
if script.name.startswith("IRIS") and system.id == "shn-provider-test":
    st.warning(
        "An IRIS FHIR test is selected against the SHN provider ePA endpoint. "
        "Choose Local IRIS FHIR Server for IRIS CRUD and CapabilityStatement "
        "tests; SHN's provider endpoint does not offer equivalent general "
        "FHIR CRUD operations. Fix the target first, then credentials."
    )


c1, c2, c3 = st.columns(3)
c1.metric("Actions", len(script.actions))
c2.metric("Fixtures", len(script.fixtures))
c3.metric("Unsupported", len(script.unsupported_elements))

st.markdown(f"**{script.name}**")
if script.description:
    st.write(script.description)

if script.unsupported_elements:
    st.warning(
        "Unsupported TestScript elements: "
        + ", ".join(script.unsupported_elements)
    )

with st.expander("What is this test checking? · Results guide", expanded=False):
    st.markdown("#### What this test actually does")
    if script.description:
        st.write(script.description)
    st.write(describe_scope(script))
    for action in script.actions:
        action_kind = "Request" if action.operation is not None else "Check"
        group = action.test_name or action.section
        st.markdown(f"**{action_kind}: {action_label(action)}** · {group}")
        st.write(describe_action(action))

    st.markdown("#### Reading the results")
    st.write(
        "**Overall PASS** means no implemented assertion or validator check "
        "reported FAIL/ERROR, and no unsupported TestScript feature was flagged. "
        "An automatic validation SKIP does not fail the run. "
        "PASS does not establish any behavior that this script never checked."
    )
    st.markdown("**State** — status of an operation or assertion row")
    st.table(
        [{"State": key, "Meaning": value} for key, value in ACTION_STATES.items()]
    )
    st.markdown(
        "**Validation** — automatic basic FHIR response inspection, "
        "independent of the TestScript's explicit assertions"
    )
    st.table(
        [{"Value": key, "Meaning": value} for key, value in VALIDATION_STATES.items()]
    )
    st.caption(
        "The validation column can combine several results for an operation. "
        "The current validator parses FHIR JSON and checks configured resourceType "
        "or declared meta.profile values. It does NOT perform full "
        "FHIR StructureDefinition or implementation-guide conformance validation."
    )
    st.markdown("**Phase** — category of event in the execution log")
    st.table(
        [{"Phase": key, "Meaning": value} for key, value in EVENT_PHASES.items()]
    )
    st.caption(
        "section = setup / test / teardown within a TestScript. "
        "kind = operation (HTTP request) or assertion (explicit check). "
        "HTTP is the response status; even 200 is not proof of business correctness. "
        "error = None means no error was recorded for that row."
    )

with st.expander("Raw TestScript JSON"):
    st.code(
        json.dumps(script.source, indent=2, sort_keys=True),
        language="json",
    )

if not system.configured:
    st.error(
        "This TestSystem is not fully configured. "
        "Set the required environment/config value before running it."
    )

step_ids = [action.id for action in script.actions]
selected_step = st.selectbox(
    "Run through step",
    step_ids,
    format_func=lambda action_id: next(
        (
            action.operation.label
            if action.operation is not None
            else action.assertion.label
            for action in script.actions
            if action.id == action_id
        ),
        action_id,
    ),
)

run_cols = st.columns(2)
run_all = run_cols[0].button(
    "Run all",
    type="primary",
    use_container_width=True,
    disabled=not system.configured,
)
run_through = run_cols[1].button(
    "Run through selected step",
    use_container_width=True,
    disabled=not system.configured,
)

if run_all or run_through:
    try:
        profile = selected_profile
        runner = TestScriptRunner(execution_mode="streamlit")
        with st.spinner(f"Running {script.name} against {system.name}..."):
            result = runner.run(
                script,
                system,
                profile,
                through_action_id=(selected_step if run_through else None),
            )
        st.session_state["toolbench-last-run"] = result
    except Exception as exc:
        st.exception(exc)

result = st.session_state.get("toolbench-last-run")
if result and result.testscript_id == script.id and result.system_id == system.id:
    http_statuses = [
        (action.transport or {}).get("status_code")
        for action in result.actions
        if action.transport
    ]
    if 401 in http_statuses:
        st.warning(
            "IRIS returned HTTP 401 for one or more operations. "
            "The request reached the server, but this resource interaction requires "
            "authentication (or the supplied credentials were rejected). "
            "Select/configure an authenticated CredentialProfile and rerun."
        )

    if result.status == "PASS":
        st.success(f"{result.status} • {result.duration_ms:.1f} ms")
    elif result.status == "UNSUPPORTED":
        st.warning(f"{result.status} • {result.duration_ms:.1f} ms")
    else:
        st.error(f"{result.status} • {result.duration_ms:.1f} ms")

    rows = [
        {
            "section": action.section,
            "test": action.test_name,
            "action": action.action_id,
            "kind": action.kind,
            "state": (
                "EXECUTED"
                if action.kind == "operation" and action.state == "PASS"
                else action.state
            ),
            "http": (
                (action.transport or {}).get("status_code")
                if action.transport
                else None
            ),
            "validation": (
                ",".join(
                    str(row.get("state"))
                    for row in action.validation
                    if row.get("state")
                )
                if action.validation
                else None
            ),
            "error": action.error,
            "label": action.label,
        }
        for action in result.actions
    ]
    st.dataframe(rows, hide_index=True, use_container_width=True)

    for action in result.actions:
        display_state = (
            "EXECUTED"
            if action.kind == "operation" and action.state == "PASS"
            else action.state
        )
        with st.expander(
            f"{display_state} — {action.action_id} — {action.label}",
            expanded=False,
        ):
            matching_script_action = next(
                (item for item in script.actions if item.id == action.action_id),
                None,
            )
            if matching_script_action is not None:
                st.caption(describe_action(matching_script_action))
            if action.error:
                st.error(action.error)
            if action.transport:
                tx = action.transport
                st.markdown("**REQUEST**")
                st.code(
                    f"{tx.get('method')} {tx.get('url')}\n"
                    + "\n".join(
                        f"{k}: {v}"
                        for k, v in (tx.get("request_headers") or {}).items()
                    )
                    + "\n\n"
                    + (tx.get("request_body") or ""),
                    language=None,
                )
                st.markdown("**RESPONSE**")
                st.code(
                    f"HTTP {tx.get('status_code')} {tx.get('reason') or ''}\n"
                    + "\n".join(
                        f"{k}: {v}"
                        for k, v in (tx.get("response_headers") or {}).items()
                    )
                    + "\n\n"
                    + (tx.get("response_text") or ""),
                    language=None,
                )
                if tx.get("trace_url"):
                    st.link_button("Open trace", tx["trace_url"])
            if action.assertion:
                st.markdown("**ASSERTION**")
                st.code(
                    json.dumps(action.assertion, indent=2, sort_keys=True),
                    language="json",
                )
            if action.validation:
                st.markdown("**VALIDATION**")
                st.code(
                    json.dumps(action.validation, indent=2, sort_keys=True),
                    language="json",
                )

    st.markdown("### Execution log")
    st.dataframe(
        [
            {
                "seq": event["sequence"],
                "time": event["timestamp"],
                "event": event["event_type"],
                "operation": event.get("operation_id"),
                "phase": event["phase"],
            }
            for event in result.events
        ],
        hide_index=True,
        use_container_width=True,
    )

    if result.artifact_dir:
        st.download_button(
            "Export run evidence",
            data=run_zip_bytes(result.artifact_dir),
            file_name=f"toolbench-run-{result.run_id}.zip",
            mime="application/zip",
            use_container_width=True,
        )
