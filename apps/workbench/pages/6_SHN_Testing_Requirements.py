"""Display the dated, source-editable SHN requirements inventory.

The integrated Medilacra shell and standalone Workbench both execute this
page from the Workbench subtree. No requirements are stored in Streamlit.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st


DOCUMENT = Path(__file__).resolve().parents[1] / "docs" / "SHN_TESTING_REQUIREMENTS_2026-10-31.md"

st.set_page_config(page_title="Workbench — SHN Testing Requirements", page_icon="📋", layout="wide")
st.title("📋 SHN Testing Requirements")
st.caption("Working snapshot · 2026-10-31 · Not an SHN-approved specification")

if not DOCUMENT.is_file():
    st.error(f"Requirements document is missing: {DOCUMENT.name}")
else:
    content = DOCUMENT.read_text(encoding="utf-8")
    st.markdown(content)
    st.download_button(
        "Download requirements Markdown",
        data=content,
        file_name=DOCUMENT.name,
        mime="text/markdown",
        use_container_width=True,
    )
