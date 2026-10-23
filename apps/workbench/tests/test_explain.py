"""Regression tests for plain-language descriptions of real TestScripts."""
from pathlib import Path
from toolbench.explain import ACTION_STATES, VALIDATION_STATES, EVENT_PHASES, describe_action, describe_scope, action_label
from toolbench.testscript import load_testscript

FIXTURES = Path(__file__).resolve().parents[1] / "testscripts"


def test_guide_covers_actual_states_and_phases():
    assert {"EXECUTED", "PASS", "FAIL", "SKIP", "ERROR", "UNSUPPORTED"} == set(ACTION_STATES)
    assert {"PASS", "FAIL", "ERROR", "SKIP", "None / blank"} == set(VALIDATION_STATES)
    assert set(EVENT_PHASES) == {
        "run", "configuration", "fixture", "authentication", "transport",
        "operation", "validation", "assertion", "persistence",
    }


def test_shn_connectivity_guide_describes_its_real_checks():
    script = load_testscript(FIXTURES / "shn" / "provider-connectivity.json")
    explanations = [describe_action(action) for action in script.actions]
    assert len(explanations) == 3
    assert "CDS Hooks service listing" in explanations[0]
    assert "200" in explanations[1]
    assert "'services' is present" in explanations[2]
    assert "not assert that a list is nonempty" in explanations[2]
    assert "1 HTTP operation(s) and 2 explicit assertion(s)" in describe_scope(script)


def test_iris_capability_guide_does_not_overclaim():
    script = load_testscript(FIXTURES / "iris" / "capability-statement.json")
    descriptions = [describe_action(action) for action in script.actions]
    assert any("advertised server capabilities" in text for text in descriptions)
    assert any("does not prove" in text for text in descriptions)


def test_skip_is_not_failure_or_fhir_conformance():
    assert "not full StructureDefinition" in VALIDATION_STATES["PASS"]
    assert "CDS Hooks JSON is not FHIR JSON" in VALIDATION_STATES["SKIP"]
    assert "not establish HTTP success" in ACTION_STATES["EXECUTED"]


def test_ui_contains_the_expandable_guide_and_action_context():
    source = (Path(__file__).resolve().parents[1] / "pages" / "4_TestScript_Runner.py").read_text()
    assert 'st.expander("What is this test checking? · Results guide"' in source
    assert "for action in script.actions:" in source
    assert "st.write(describe_action(action))" in source
    assert "EVENT_PHASES.items()" in source
    assert "VALIDATION_STATES.items()" in source


def test_all_real_testscript_actions_have_renderable_labels():
    """Exercise the same field access as the Streamlit guide for every fixture."""
    paths = sorted(FIXTURES.rglob("*.json"))
    # Fixture resources are JSON, but not FHIR TestScripts.
    import json
    scripts = [
        load_testscript(path) for path in paths
        if json.loads(path.read_text(encoding="utf-8")).get("resourceType") == "TestScript"
    ]
    assert scripts
    for script in scripts:
        for action in script.actions:
            label = action_label(action)
            assert isinstance(label, str) and label.strip(), (script.path, action.id)
            assert label == (
                action.operation.label if action.operation is not None
                else action.assertion.label
            )


def test_guide_renders_nested_action_labels_not_missing_script_action_label():
    source = (Path(__file__).resolve().parents[1] / "pages" / "4_TestScript_Runner.py").read_text()
    assert 'action_label(action)' in source
    # Result actions legitimately have a top-level label; parsed ScriptAction
    # objects used by the guide do not.
    assert 'st.markdown(f"**{action_kind}: {action.label}** · {group}")' not in source



def test_auth_preparation_help_covers_supported_profiles():
    from toolbench.explain import AUTH_PREPARATION_HELP

    assert set(AUTH_PREPARATION_HELP) == {
        "none", "basic", "bearer", "oauth2_client_credentials",
    }
    assert "does not contact the server" in AUTH_PREPARATION_HELP["none"]
    assert "Does not verify" in AUTH_PREPARATION_HELP["basic"]
    assert "Does not request a new token" in AUTH_PREPARATION_HELP["bearer"]
    assert "fresh OAuth access token" in AUTH_PREPARATION_HELP["oauth2_client_credentials"]


def test_auth_page_uses_new_button_label_and_selected_profile_explanation():
    source = (
        Path(__file__).resolve().parents[1] / "pages" / "3_Auth_Workbench.py"
    ).read_text(encoding="utf-8")
    assert 'st.button("Acquire/Prepare Credentials"' in source
    assert "Generate / resolve auth" not in source
    assert "AUTH_PREPARATION_HELP.get(" in source
    assert "profile.type" in source
    # The explanation is part of the same column as the preparation button.
    assert source.index("AUTH_PREPARATION_HELP.get(") < source.index("with c2:")
