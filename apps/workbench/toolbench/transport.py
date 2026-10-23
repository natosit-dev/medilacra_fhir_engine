from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urljoin

import requests

from .auth import AuthManager
from .safety import body_was_redacted, sanitize_jsonish_text
from .systems import TestSystem


@dataclass(frozen=True)
class TransportResult:
    method: str
    url: str
    status_code: int | None
    reason: str | None
    request_headers: dict[str, str]
    request_body: str | None
    response_headers: dict[str, str]
    response_text: str
    elapsed_ms: float
    request_target: str | None = None
    attempts: int = 1
    correlation_id: str | None = None
    response_correlation_id: str | None = None
    leg_id: str | None = None
    trace_url: str | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return (
            self.error is None
            and self.status_code is not None
            and 200 <= self.status_code < 300
        )

    def json_body(self) -> Any:
        if not self.response_text.strip():
            return None
        return json.loads(self.response_text)

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["request_body_redacted"] = body_was_redacted(self.request_body)
        value["response_body_redacted"] = body_was_redacted(self.response_text)
        value["request_body"] = sanitize_jsonish_text(self.request_body)
        value["response_text"] = sanitize_jsonish_text(self.response_text) or ""
        return value


class TransportClient:
    def __init__(
        self,
        system: TestSystem,
        auth: AuthManager | None = None,
        *,
        timeout_seconds: float = 30.0,
        event_sink=None,
    ) -> None:
        self.system = system
        self.auth = auth
        self.timeout_seconds = float(timeout_seconds)
        self.event_sink = event_sink

    def _emit(self, event_type: str, data: dict[str, Any]) -> None:
        if self.event_sink:
            self.event_sink(event_type, "transport", data)

    def request(
        self,
        method: str,
        path_or_url: str,
        *,
        headers: dict[str, str] | None = None,
        body: str | bytes | dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> TransportResult:
        method = method.upper().strip()
        if path_or_url.startswith(("http://", "https://")):
            url = path_or_url
        else:
            url = urljoin(
                self.system.base_url.rstrip("/") + "/",
                path_or_url.lstrip("/"),
            )

        request_headers = self.system.headers()
        if headers:
            request_headers.update(
                {str(key): str(value) for key, value in headers.items()}
            )
        if self.auth:
            try:
                request_headers.update(self.auth.headers())
            except Exception as exc:
                safe_headers = self._safe_headers(request_headers)
                result = TransportResult(
                    method=method,
                    url=url,
                    status_code=None,
                    reason=None,
                    request_headers=safe_headers,
                    request_body=(
                        json.dumps(body)
                        if isinstance(body, dict)
                        else body.decode("utf-8", errors="replace")
                        if isinstance(body, bytes)
                        else body
                    ),
                    response_headers={},
                    response_text="",
                    elapsed_ms=0.0,
                    request_target=path_or_url,
                    error=f"authentication failed: {type(exc).__name__}: {exc}",
                )
                self._emit(
                    "http.request.blocked",
                    {
                        "method": method,
                        "url": url,
                        "headers": safe_headers,
                        "error": result.error,
                    },
                )
                return result

        corr = self.system.correlation
        sent_correlation = correlation_id
        if (
            corr.request_header
            and corr.generate_uuid
            and not sent_correlation
        ):
            sent_correlation = str(uuid.uuid4())
        if corr.request_header and sent_correlation:
            request_headers[corr.request_header] = sent_correlation

        if isinstance(body, dict):
            payload = json.dumps(body)
        elif isinstance(body, bytes):
            payload = body.decode("utf-8", errors="replace")
        else:
            payload = body

        safe_headers = self._safe_headers(request_headers)
        self._emit(
            "http.request.sent",
            {
                "method": method,
                "url": url,
                "headers": safe_headers,
                "body": sanitize_jsonish_text(payload),
                "body_redacted": body_was_redacted(payload),
                "correlation_id": sent_correlation,
            },
        )

        started = time.monotonic()
        attempts = 0
        try:
            kwargs: dict[str, Any] = {
                "headers": request_headers,
                "timeout": self.timeout_seconds,
                "verify": self.system.tls.requests_verify,
            }
            if self.system.tls.requests_cert:
                kwargs["cert"] = self.system.tls.requests_cert
            if method in {"POST", "PUT", "PATCH", "DELETE"} and payload is not None:
                kwargs["data"] = payload

            while True:
                attempts += 1
                response = requests.request(method, url, **kwargs)
                retry = self.system.retry
                if (
                    response.status_code not in retry.statuses
                    or attempts > retry.max_retries
                ):
                    break
                retry_after = response.headers.get("Retry-After")
                try:
                    delay = int(retry_after)
                except (TypeError, ValueError):
                    delay = retry.default_retry_after_seconds
                self._emit(
                    "http.retry.scheduled",
                    {
                        "url": url,
                        "http_status": response.status_code,
                        "attempt": attempts,
                        "retry_after_seconds": max(0, delay),
                        "correlation_id": sent_correlation,
                    },
                )
                time.sleep(max(0, delay))

            elapsed = round((time.monotonic() - started) * 1000.0, 1)
            response_headers = self._safe_response_headers(
                {
                    str(key): str(value)
                    for key, value in response.headers.items()
                }
            )
            response_corr = (
                _header_value(response_headers, corr.response_header)
                if corr.response_header
                else None
            )
            leg_id = (
                _header_value(response_headers, corr.leg_header)
                if corr.leg_header
                else None
            )
            trace_key = response_corr or sent_correlation or leg_id
            trace_url = (
                corr.trace_url_template.format(id=trace_key)
                if corr.trace_url_template and trace_key
                else None
            )
            result = TransportResult(
                method=method,
                url=url,
                status_code=int(response.status_code),
                reason=response.reason,
                request_headers=safe_headers,
                request_body=payload,
                response_headers=response_headers,
                response_text=response.text,
                elapsed_ms=elapsed,
                request_target=path_or_url,
                attempts=attempts,
                correlation_id=sent_correlation,
                response_correlation_id=response_corr,
                leg_id=leg_id,
                trace_url=trace_url,
            )
        except Exception as exc:
            result = TransportResult(
                method=method,
                url=url,
                status_code=None,
                reason=None,
                request_headers=safe_headers,
                request_body=payload,
                response_headers={},
                response_text="",
                elapsed_ms=round(
                    (time.monotonic() - started) * 1000.0,
                    1,
                ),
                request_target=path_or_url,
                attempts=max(1, attempts),
                correlation_id=sent_correlation,
                error=str(exc),
            )

        self._emit(
            "http.response.received",
            {
                "http_status": result.status_code,
                "reason": result.reason,
                "headers": result.response_headers,
                "body": sanitize_jsonish_text(result.response_text),
                "body_redacted": body_was_redacted(result.response_text),
                "elapsed_ms": result.elapsed_ms,
                "attempts": result.attempts,
                "correlation_id": result.response_correlation_id,
                "sent_correlation_id": result.correlation_id,
                "leg_id": result.leg_id,
                "trace_url": result.trace_url,
                "error": result.error,
            },
        )
        return result

    def _safe_headers(
        self,
        headers: dict[str, str],
    ) -> dict[str, str]:
        sensitive = {
            "authorization",
            "proxy-authorization",
            "cookie",
        }
        sensitive.update(
            header.lower()
            for header in self.system.sensitive_headers
        )
        out: dict[str, str] = {}
        for key, value in headers.items():
            if key.lower() in sensitive:
                if key.lower() == "authorization":
                    scheme = value.split(" ", 1)[0] if value else ""
                    out[key] = (
                        f"<redacted:{scheme}>" if scheme else "<redacted>"
                    )
                else:
                    out[key] = "<redacted>"
            else:
                out[key] = value
        return out

    @staticmethod
    def _safe_response_headers(
        headers: dict[str, str],
    ) -> dict[str, str]:
        sensitive = {"set-cookie", "proxy-authenticate"}
        return {
            key: ("<redacted>" if key.lower() in sensitive else value)
            for key, value in headers.items()
        }


def _header_value(
    headers: dict[str, str],
    name: str,
) -> str | None:
    wanted = name.lower()
    for key, value in headers.items():
        if key.lower() == wanted:
            return value
    return None
