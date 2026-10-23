import streamlit as st


st.set_page_config(
    page_title="MediLacra SHN Workbench",
    page_icon="🧪",
    layout="wide",
)

st.title("🧪 MediLacra SHN Workbench")
st.caption(
    "Small interoperability test bench for connectivity, authentication, "
    "FHIR TestScript execution, raw evidence, and repeatable comparison."
)

st.markdown(
    """
Start with **Connection Lab**.

The workbench is intentionally being built from a small set of proven
MediLacra primitives rather than migrating the existing application wholesale.
"""
)
