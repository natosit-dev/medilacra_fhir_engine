"""Single Streamlit front door for original MediLacra and SHN Workbench.

    python -m streamlit run app.py

M-003 preserves existing behavior; it does not alter either application's
business logic or connect the new shared Engine domain API yet.
"""
from __future__ import annotations

import streamlit as st

from unified.legacy import execute_existing_page
from unified.page_catalog import PAGES


def home() -> None:
    st.set_page_config(page_title="Medilacra", page_icon="🧬", layout="wide")
    st.title("Medilacra")
    st.caption("Synthetic clinical reality × operational reality")
    col_clinical, col_operational = st.columns(2)
    with col_clinical:
        st.subheader("Clinical Reality")
        st.write("Generate patients, encounters, messages, scenarios and cohorts.")
    with col_operational:
        st.subheader("Operational Reality")
        st.write("Configure participants and systems; execute tests; inspect evidence.")
    st.info(
        "M-003 integration: the original Medilacra and Workbench pages are "
        "available from this navigation. Their implementations are unchanged. "
        "Full cross-app case continuity comes next."
    )


def legacy_page(source: str):
    """Create a per-page callable with an explicit source path."""
    def show() -> None:
        execute_existing_page(source)
    return show


def main() -> None:
    navigation: dict[str, list] = {
        "Start": [st.Page(home, title="Home", icon="🏠", default=True)]
    }
    page_refs = {}
    for page in PAGES:
        registered = st.Page(
            legacy_page(page.source),
            title=page.title,
            icon=page.icon,
            url_path=page.slug,
        )
        navigation.setdefault(page.section, []).append(registered)
        page_refs[page.slug] = registered
    # Cross-page links in imported pages require registered st.Page objects.
    st.session_state["_medilacra_page_refs"] = page_refs
    st.navigation(navigation, position="sidebar").run()


if __name__ == "__main__":
    main()
