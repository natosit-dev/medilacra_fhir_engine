from __future__ import annotations

import socket
import ssl
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

import requests


@dataclass(frozen=True)
class DNSResult:
    host: str
    addresses: list[str]
    elapsed_ms: float
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.addresses)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TCPResult:
    host: str
    port: int
    elapsed_ms: float
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TLSResult:
    host: str
    port: int
    elapsed_ms: float
    tls_version: str | None = None
    cipher: str | None = None
    certificate_subject: str | None = None
    certificate_issuer: str | None = None
    not_before: str | None = None
    not_after: str | None = None
    days_until_expiry: int | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HTTPResult:
    method: str
    url: str
    status_code: int | None
    reason: str | None
    elapsed_ms: float
    response_headers: dict[str, str]
    response_text: str
    content_type: str | None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return (
            self.error is None
            and self.status_code is not None
            and 200 <= self.status_code < 300
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def probe_dns(host: str) -> DNSResult:
    started = time.monotonic()
    try:
        infos = socket.getaddrinfo(host, None)
        addresses = sorted({info[4][0] for info in infos})
        return DNSResult(
            host=host,
            addresses=addresses,
            elapsed_ms=round((time.monotonic() - started) * 1000.0, 1),
        )
    except Exception as exc:
        return DNSResult(
            host=host,
            addresses=[],
            elapsed_ms=round((time.monotonic() - started) * 1000.0, 1),
            error=str(exc),
        )


def probe_tcp(host: str, port: int, timeout_seconds: float = 6.0) -> TCPResult:
    started = time.monotonic()
    try:
        with socket.create_connection(
            (host, int(port)),
            timeout=float(timeout_seconds),
        ):
            pass
        return TCPResult(
            host=host,
            port=int(port),
            elapsed_ms=round((time.monotonic() - started) * 1000.0, 1),
        )
    except Exception as exc:
        return TCPResult(
            host=host,
            port=int(port),
            elapsed_ms=round((time.monotonic() - started) * 1000.0, 1),
            error=str(exc),
        )


def _common_name(value: Any) -> str | None:
    if not value:
        return None
    try:
        flattened = dict(item for group in value for item in group)
    except Exception:
        return None
    return flattened.get("commonName")


def _days_until(not_after: str | None) -> int | None:
    if not not_after:
        return None
    try:
        expiry = datetime.strptime(
            not_after,
            "%b %d %H:%M:%S %Y %Z",
        ).replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return (expiry - datetime.now(timezone.utc)).days


def probe_tls(
    host: str,
    port: int = 443,
    timeout_seconds: float = 6.0,
    verify: bool = True,
) -> TLSResult:
    started = time.monotonic()
    try:
        context = (
            ssl.create_default_context()
            if verify
            else ssl._create_unverified_context()
        )
        with socket.create_connection(
            (host, int(port)),
            timeout=float(timeout_seconds),
        ) as sock:
            with context.wrap_socket(sock, server_hostname=host) as secure:
                certificate = secure.getpeercert()
                cipher = secure.cipher()
                return TLSResult(
                    host=host,
                    port=int(port),
                    elapsed_ms=round(
                        (time.monotonic() - started) * 1000.0,
                        1,
                    ),
                    tls_version=secure.version(),
                    cipher=cipher[0] if cipher else None,
                    certificate_subject=_common_name(
                        certificate.get("subject")
                    ),
                    certificate_issuer=_common_name(
                        certificate.get("issuer")
                    ),
                    not_before=certificate.get("notBefore"),
                    not_after=certificate.get("notAfter"),
                    days_until_expiry=_days_until(
                        certificate.get("notAfter")
                    ),
                )
    except Exception as exc:
        return TLSResult(
            host=host,
            port=int(port),
            elapsed_ms=round((time.monotonic() - started) * 1000.0, 1),
            error=str(exc),
        )


def probe_http(
    url: str,
    method: str = "GET",
    *,
    headers: dict[str, str] | None = None,
    body: str | bytes | None = None,
    timeout_seconds: float = 10.0,
    verify_tls: bool = True,
) -> HTTPResult:
    method = method.upper().strip()
    started = time.monotonic()
    try:
        response = requests.request(
            method,
            url,
            headers=headers or {},
            data=body if method in {"POST", "PUT", "PATCH", "DELETE"} else None,
            timeout=float(timeout_seconds),
            verify=bool(verify_tls),
        )
        return HTTPResult(
            method=method,
            url=url,
            status_code=int(response.status_code),
            reason=response.reason,
            elapsed_ms=round((time.monotonic() - started) * 1000.0, 1),
            response_headers={
                str(key): str(value)
                for key, value in response.headers.items()
            },
            response_text=response.text,
            content_type=response.headers.get("content-type"),
        )
    except Exception as exc:
        return HTTPResult(
            method=method,
            url=url,
            status_code=None,
            reason=None,
            elapsed_ms=round((time.monotonic() - started) * 1000.0, 1),
            response_headers={},
            response_text="",
            content_type=None,
            error=str(exc),
        )


def probe_ports(
    host: str,
    ports: list[int],
    timeout_seconds: float = 2.0,
) -> list[TCPResult]:
    return [
        probe_tcp(host, int(port), timeout_seconds)
        for port in ports
    ]
