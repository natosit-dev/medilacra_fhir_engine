from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import urljoin

import requests

from .credentials import CredentialProfile
from .systems import TestSystem


EventSink = Callable[[str, str, dict[str, Any]], Any]


@dataclass(frozen=True)
class AuthStatus:
    profile_id: str
    auth_type: str
    active: bool
    acquired_at_epoch: float | None = None
    expires_at_epoch: float | None = None
    scope: str | None = None
    token_http_status: int | None = None
    error: str | None = None

    @property
    def expires_in_seconds(self) -> int | None:
        if self.expires_at_epoch is None:
            return None
        return max(0, int(self.expires_at_epoch - time.time()))


class AuthManager:
    def __init__(
        self,
        system: TestSystem,
        profile: CredentialProfile | None,
        *,
        timeout_seconds: float = 20.0,
        event_sink: EventSink | None = None,
    ) -> None:
        self.system = system
        self.profile = profile
        self.timeout_seconds = float(timeout_seconds)
        self.event_sink = event_sink
        self._token: str | None = None
        self._token_expires_at_monotonic = 0.0
        self._token_acquired_epoch: float | None = None
        self._scope: str | None = None
        self._token_http_status: int | None = None
        self._error: str | None = None
        self._checked = False

    def _emit(
        self,
        event_type: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        if self.event_sink:
            self.event_sink(event_type, "authentication", data or {})

    def _profile(self) -> CredentialProfile:
        if self.profile is None:
            return CredentialProfile(
                id="none",
                name="No authentication",
                type="none",
            )
        return self.profile

    def status(self) -> AuthStatus:
        profile = self._profile()
        active = False
        expires_at_epoch = None
        if profile.type == "oauth2_client_credentials" and self._token:
            remaining = self._token_expires_at_monotonic - time.monotonic()
            active = remaining > 0
            if self._token_acquired_epoch is not None:
                expires_at_epoch = time.time() + max(0, remaining)
        elif profile.type == "none":
            active = True
        elif profile.type in {"basic", "bearer"}:
            active = self._checked and self._error is None
        return AuthStatus(
            profile_id=profile.id,
            auth_type=profile.type,
            active=active,
            acquired_at_epoch=self._token_acquired_epoch,
            expires_at_epoch=expires_at_epoch,
            scope=self._scope,
            token_http_status=self._token_http_status,
            error=self._error,
        )

    def acquire(self, *, force: bool = False) -> AuthStatus:
        profile = self._profile()
        self._error = None

        if profile.type in {"none", "basic", "bearer"}:
            try:
                self.headers(force=force)
            except Exception as exc:
                self._error = str(exc)
            return self.status()

        if profile.type != "oauth2_client_credentials":
            self._error = f"unsupported auth type {profile.type!r}"
            return self.status()

        try:
            self._ensure_oauth_token(force=force)
        except Exception as exc:
            self._error = str(exc)
        return self.status()

    def headers(self, *, force: bool = False) -> dict[str, str]:
        profile = self._profile()

        if profile.type == "none":
            self._checked = True
            return {}

        if profile.type == "basic":
            if not profile.username or not profile.password:
                raise ValueError("basic auth requires username and password sources")
            raw = (
                profile.username.resolve()
                + ":"
                + profile.password.resolve()
            ).encode("utf-8")
            encoded = base64.b64encode(raw).decode("ascii")
            self._checked = True
            return {"Authorization": f"Basic {encoded}"}

        if profile.type == "bearer":
            if not profile.bearer_token:
                raise ValueError("bearer auth requires bearer_token source")
            token = profile.bearer_token.resolve()
            self._checked = True
            return {"Authorization": f"Bearer {token}"}

        if profile.type == "oauth2_client_credentials":
            token = self._ensure_oauth_token(force=force)
            return {"Authorization": f"Bearer {token}"}

        raise ValueError(f"unsupported auth type {profile.type!r}")

    def _ensure_oauth_token(self, *, force: bool = False) -> str:
        profile = self._profile()
        if (
            not force
            and self._token
            and time.monotonic() < self._token_expires_at_monotonic
        ):
            self._emit(
                "auth.token.reused",
                {
                    "profile_id": profile.id,
                    "token_url": self._token_url(profile),
                },
            )
            return self._token

        if self._token:
            self._emit(
                "auth.token.expired",
                {
                    "profile_id": profile.id,
                    "token_url": self._token_url(profile),
                },
            )
            self._token = None

        if not profile.client_id or not profile.client_secret:
            raise ValueError(
                "oauth2_client_credentials requires client_id and client_secret sources"
            )

        token_url = self._token_url(profile)
        self._emit(
            "auth.token.requested",
            {
                "profile_id": profile.id,
                "token_url": token_url,
                "auth_style": profile.auth_style,
            },
        )

        client_id = profile.client_id.resolve()
        client_secret = profile.client_secret.resolve()
        data: dict[str, str] = {"grant_type": "client_credentials"}
        if profile.scope:
            data["scope"] = profile.scope
        data.update(profile.token_extra_fields)

        kwargs: dict[str, Any] = {
            "data": data,
            "timeout": self.timeout_seconds,
            "verify": self.system.tls.requests_verify,
        }
        if self.system.tls.requests_cert:
            kwargs["cert"] = self.system.tls.requests_cert

        if profile.auth_style == "basic":
            kwargs["auth"] = (client_id, client_secret)
        elif profile.auth_style == "body":
            data["client_id"] = client_id
            data["client_secret"] = client_secret
        else:
            raise ValueError(
                f"unsupported OAuth client auth style {profile.auth_style!r}"
            )

        response = requests.post(token_url, **kwargs)
        self._token_http_status = int(response.status_code)

        try:
            payload = response.json()
        except ValueError:
            payload = {}

        if response.status_code < 200 or response.status_code >= 300:
            self._emit(
                "auth.token.failed",
                {
                    "profile_id": profile.id,
                    "token_url": token_url,
                    "http_status": response.status_code,
                },
            )
            raise RuntimeError(
                f"token request failed with HTTP {response.status_code}"
            )

        token = payload.get("access_token")
        if not token:
            raise RuntimeError("token response contains no access_token")

        expires_in = int(payload.get("expires_in", 300))
        self._token = str(token)
        self._checked = True
        self._token_expires_at_monotonic = (
            time.monotonic() + max(1, expires_in - 30)
        )
        self._token_acquired_epoch = time.time()
        self._scope = payload.get("scope") or profile.scope
        self._emit(
            "auth.token.acquired",
            {
                "profile_id": profile.id,
                "token_url": token_url,
                "http_status": response.status_code,
                "expires_in_seconds": expires_in,
                "scope": self._scope,
            },
        )
        return self._token

    def _token_url(self, profile: CredentialProfile) -> str:
        if not profile.token_url:
            raise ValueError("OAuth profile requires token_url")
        if profile.token_url.startswith(("http://", "https://")):
            return profile.token_url
        return urljoin(self.system.base_url + "/", profile.token_url.lstrip("/"))
