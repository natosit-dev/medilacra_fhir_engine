from __future__ import annotations

import json
from urllib.parse import urlparse

import streamlit as st

from toolbench.connectivity import (
    probe_dns,
    probe_http,
    probe_ports,
    probe_tcp,
    probe_tls,
)
from toolbench.systems import list_systems


st.set_page_config(
    page_title="Workbench — Connection Lab",
    page_icon="🌐",
    layout="wide",
)

st.title("🌐 Connection Lab")
st.caption(
    "DNS, TCP, TLS, certificate, and raw HTTP checks. "
    "This page does not require a TestScript."
)

systems = list_systems()
system_by_id = {system.id: system for system in systems}
system_ids = list(system_by_id)

selected_id = st.selectbox(
    "TestSystem",
    system_ids,
    format_func=lambda system_id: system_by_id[system_id].name,
) if system_ids else None

selected = system_by_id.get(selected_id) if selected_id else None
default_url = (
    selected.base_url
    if selected and selected.configured
    else "https://pa-test.shn-preview.org"
)

use_system_endpoint = st.toggle(
    "Use selected TestSystem endpoint",
    value=True,
    help=(
        "Keeps the Connection Lab tied to the TestSystem configuration and "
        "avoids stale Streamlit URL state. Turn this off to probe an arbitrary URL."
    ),
)

if use_system_endpoint and selected and selected.configured:
    url = selected.base_url
    st.code(url, language=None)
else:
    url = st.text_input(
        "Endpoint URL",
        default_url,
        key="connection-lab-manual-endpoint",
    )

parsed = urlparse(url if "://" in url else f"https://{url}")
st.caption(
    f"Effective endpoint: {url} • scheme={parsed.scheme or 'unknown'} • "
    f"TLS probe={'YES' if parsed.scheme.lower() == 'https' else 'NO'}"
)
host = parsed.hostname or ""
default_port = parsed.port or (443 if parsed.scheme == "https" else 80)

c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    host_override = st.text_input("Host", host)
with c2:
    port = int(
        st.number_input(
            "Port",
            min_value=1,
            max_value=65535,
            value=int(default_port),
            step=1,
        )
    )
with c3:
    default_verify = selected.tls.verify if selected else True
    verify_tls = st.toggle(
        "Verify TLS",
        value=default_verify,
        disabled=parsed.scheme.lower() != "https",
    )

timeout = float(
    st.number_input(
        "Timeout (seconds)",
        min_value=1,
        max_value=60,
        value=6,
        step=1,
    )
)

if st.button("Run connection checks", type="primary", use_container_width=True):
    dns = probe_dns(host_override)
    tcp = probe_tcp(host_override, port, timeout)

    tls = None
    if parsed.scheme.lower() == "https":
        tls = probe_tls(
            host_override,
            port,
            timeout,
            verify=verify_tls,
        )

    rows = [
        {
            "check": "DNS",
            "status": "PASS" if dns.ok else "FAIL",
            "elapsed_ms": dns.elapsed_ms,
            "detail": ", ".join(dns.addresses) if dns.ok else dns.error,
        },
        {
            "check": "TCP",
            "status": "PASS" if tcp.ok else "FAIL",
            "elapsed_ms": tcp.elapsed_ms,
            "detail": f"{host_override}:{port}" if tcp.ok else tcp.error,
        },
        {
            "check": "TLS",
            "status": (
                "SKIP"
                if tls is None
                else "PASS" if tls.ok else "FAIL"
            ),
            "elapsed_ms": None if tls is None else tls.elapsed_ms,
            "detail": (
                f"Not applicable for {parsed.scheme.upper()} endpoint"
                if tls is None
                else (
                    f"{tls.tls_version or 'TLS'} • {tls.certificate_subject or 'no CN'}"
                    if tls.ok
                    else tls.error
                )
            ),
        },
    ]
    st.dataframe(rows, hide_index=True, use_container_width=True)

    with st.expander("Raw connectivity results"):
        st.code(
            json.dumps(
                {
                    "dns": dns.as_dict(),
                    "tcp": tcp.as_dict(),
                    "tls": tls.as_dict() if tls is not None else {
                        "skipped": True,
                        "reason": f"endpoint scheme is {parsed.scheme or 'unknown'}",
                    },
                },
                indent=2,
                sort_keys=True,
            ),
            language="json",
        )

st.divider()
st.subheader("Quick port probes")
ports_text = st.text_input(
    "Ports",
    "22,80,443,1972,52773",
    help="Comma-separated TCP ports.",
)
if st.button("Probe ports", use_container_width=True):
    ports = [
        int(value.strip())
        for value in ports_text.split(",")
        if value.strip().isdigit()
    ]
    port_results = probe_ports(host_override, ports)
    st.dataframe(
        [
            {
                "port": result.port,
                "status": "OPEN" if result.ok else "NO RESPONSE",
                "elapsed_ms": result.elapsed_ms,
                "error": result.error,
            }
            for result in port_results
        ],
        hide_index=True,
        use_container_width=True,
    )

st.divider()
st.subheader("HTTP request")

default_path = selected.test_path if selected else "/"
default_request_url = (
    url.rstrip("/") + default_path
    if use_system_endpoint and selected and selected.configured
    else url
)
request_url = st.text_input(
    "Request URL",
    default_request_url,
    key=f"connection-lab-request-url:{selected_id}:{use_system_endpoint}",
)
method = st.selectbox("Method", ["GET", "POST", "PUT", "PATCH", "DELETE"])
headers_text = st.text_area(
    "Headers (JSON)",
    json.dumps(
        selected.default_headers if selected else {"Accept": "application/json"},
        indent=2,
    ),
)
body = st.text_area("Body", height=180)

if st.button("Send HTTP request", use_container_width=True):
    try:
        headers = json.loads(headers_text) if headers_text.strip() else {}
        if not isinstance(headers, dict):
            raise ValueError("headers must be a JSON object")
    except Exception as exc:
        st.error(f"Invalid headers JSON: {exc}")
    else:
        result = probe_http(
            request_url,
            method,
            headers={str(k): str(v) for k, v in headers.items()},
            body=body,
            timeout_seconds=timeout,
            verify_tls=verify_tls,
        )

        if result.error:
            st.error(result.error)
        else:
            st.markdown(
                f"**HTTP {result.status_code} {result.reason or ''}** "
                f"• {result.elapsed_ms:.1f} ms"
            )
            st.markdown("**Response headers**")
            st.code(
                "\n".join(
                    f"{key}: {value}"
                    for key, value in result.response_headers.items()
                ),
                language=None,
            )
            st.markdown("**Response body**")
            st.code(result.response_text or "<empty>", language=None)
