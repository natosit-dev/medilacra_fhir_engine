from __future__ import annotations

import json

import streamlit as st

from toolbench.export import collection_zip_bytes, discover_runs, run_zip_bytes
from toolbench.regression import compare_runs, save_comparison


st.set_page_config(
    page_title="Workbench — Evidence",
    page_icon="📦",
    layout="wide",
)

st.title("📦 Evidence")
st.caption(
    "Recorded runs, transaction bundles, and baseline comparison. "
    "Preparing exports reads local evidence only and sends no network traffic."
)

runs = discover_runs()
if not runs:
    st.info("No recorded runs yet.")
    st.stop()

rows = [
    {
        "run_id": run.run_id,
        "testscript": run.run.get("testscript_name"),
        "system": run.run.get("system_name"),
        "status": run.run.get("status"),
        "started": run.run.get("started_at"),
        "duration_ms": run.run.get("duration_ms"),
    }
    for run in runs
]
st.dataframe(rows, hide_index=True, use_container_width=True)

selected_id = st.selectbox(
    "Run",
    [run.run_id for run in reversed(runs)],
)
selected = next(run for run in runs if run.run_id == selected_id)

st.download_button(
    "Export selected run",
    data=run_zip_bytes(selected.path),
    file_name=f"toolbench-run-{selected.run_id}.zip",
    mime="application/zip",
    use_container_width=True,
)

collection_bytes, manifest = collection_zip_bytes(runs)
st.download_button(
    "Export all recorded transaction logs",
    data=collection_bytes,
    file_name=f"{manifest['collection_id']}.zip",
    mime="application/zip",
    use_container_width=True,
)
st.caption(
    f"{manifest['summary']['run_count']} runs • "
    f"{manifest['summary']['transaction_count']} transactions • "
    f"{manifest['summary']['event_count']} events"
)

st.divider()
st.subheader("Baseline comparison")

run_ids = [run.run_id for run in runs]
baseline_id = st.selectbox("Baseline", run_ids, index=0)
current_id = st.selectbox("Current", run_ids, index=len(run_ids) - 1)

if st.button("Compare runs", use_container_width=True):
    baseline = next(run.run for run in runs if run.run_id == baseline_id)
    current = next(run.run for run in runs if run.run_id == current_id)
    comparison = compare_runs(baseline, current)
    st.metric("Differences", comparison["difference_count"])
    if comparison["differences"]:
        st.dataframe(
            comparison["differences"],
            hide_index=True,
            use_container_width=True,
        )
    if comparison["latency"]:
        st.markdown("**Latency**")
        st.dataframe(
            comparison["latency"],
            hide_index=True,
            use_container_width=True,
        )
    comparison_path = save_comparison(comparison)
    st.caption(f"Saved comparison evidence: {comparison_path}")

    comparison_json = json.dumps(
        comparison,
        indent=2,
        sort_keys=True,
    ) + "\n"
    st.download_button(
        "Export regression comparison",
        data=comparison_json,
        file_name=(
            f"regression-{baseline_id}-vs-{current_id}.json"
        ),
        mime="application/json",
        use_container_width=True,
    )
    with st.expander("Raw comparison"):
        st.code(
            comparison_json,
            language="json",
        )
