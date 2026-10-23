"""No Streamlit runtime required: verify that every original page is wired."""
from pathlib import Path

from unified.legacy import ROOT, execute_existing_page, page_directory
from unified.page_catalog import PAGES


def test_selected_page_inventory():
    assert len(PAGES) == 13
    sources = {page.source for page in PAGES}
    originals = {
        "apps/mvp0/medi_lacra_app.py",
        *{f"apps/mvp0/pages/{path.name}" for path in (ROOT / "apps/mvp0/pages").glob("*.py")},
        *{f"apps/workbench/pages/{path.name}" for path in (ROOT / "apps/workbench/pages").glob("*.py")},
    }
    suppressed = {
        "apps/mvp0/pages/4_IRIS SQL Viewer.py",
        "apps/mvp0/pages/0_medi_lacra_admin.py",
        "apps/mvp0/pages/6_Note_Coder.py",
        "apps/mvp0/pages/7_AI Admin.py",
    }
    assert sources == originals
    assert all(not (ROOT / src).exists() for src in suppressed)
    assert len({page.slug for page in PAGES}) == len(PAGES)
    assert all((ROOT / src).is_file() for src in sources)


def test_deleted_views_are_not_registered():
    removed = {
        "iris-sql", "note-coder", "ai-admin", "mvp0-admin",
    }
    assert not ({page.slug for page in PAGES} & removed)


def test_piqi_links_are_registered_page_refs():
    slugs = {p.slug for p in PAGES}
    assert {"disco-inferno", "hl7-generator"} <= slugs
    source = (ROOT / "apps/mvp0/pages/9_PIQI_Connectathon_43.py").read_text()
    assert 'st.session_state["_medilacra_page_refs"]["disco-inferno"]' in source
    assert 'st.session_state["_medilacra_page_refs"]["hl7-generator"]' in source
    assert 'st.page_link("pages/8_Disco_Inferno.py"' not in source


def test_clinical_and_operational_views_both_present():
    sections = {page.section for page in PAGES}
    assert "Clinical Reality" in sections
    assert "Operational Reality" in sections
    assert "Workflows & Experiments" in sections
    assert "Inspection & Tools" in sections


def test_working_directory_is_restored_on_error(tmp_path):
    cwd = Path.cwd()
    try:
        with page_directory(tmp_path):
            assert Path.cwd() == tmp_path
            raise RuntimeError("simulated page failure")
    except RuntimeError:
        pass
    assert Path.cwd() == cwd


def test_reject_non_application_pages():
    import pytest
    with pytest.raises((ValueError, FileNotFoundError)):
        execute_existing_page("pyproject.toml")
