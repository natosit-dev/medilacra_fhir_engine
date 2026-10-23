from __future__ import annotations

from toolbench.connectivity import (
    DNSResult,
    HTTPResult,
    TCPResult,
    TLSResult,
)


def test_connectivity_result_ok_semantics():
    assert DNSResult("example.org", ["127.0.0.1"], 1.0).ok is True
    assert DNSResult("example.org", [], 1.0, "nope").ok is False

    assert TCPResult("example.org", 443, 1.0).ok is True
    assert TCPResult("example.org", 443, 1.0, "nope").ok is False

    assert TLSResult("example.org", 443, 1.0).ok is True
    assert TLSResult("example.org", 443, 1.0, error="nope").ok is False

    assert HTTPResult(
        method="GET",
        url="https://example.org",
        status_code=200,
        reason="OK",
        elapsed_ms=1.0,
        response_headers={},
        response_text="",
        content_type="text/plain",
    ).ok is True

    assert HTTPResult(
        method="GET",
        url="https://example.org",
        status_code=500,
        reason="Internal Server Error",
        elapsed_ms=1.0,
        response_headers={},
        response_text="",
        content_type="text/plain",
    ).ok is False
