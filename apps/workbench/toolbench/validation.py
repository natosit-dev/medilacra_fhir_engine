from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol

from .assertions import ERROR, FAIL, PASS, SKIP
from .fhir import meta_profiles, parse_fhir_resource
from .transport import TransportResult


@dataclass(frozen=True)
class ValidationResult:
    name: str
    state: str
    expected: Any = None
    observed: Any = None
    message: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class Validator(Protocol):
    def validate(
        self,
        response: TransportResult,
        *,
        expected_resource: str | None = None,
        expected_profile: str | None = None,
    ) -> list[ValidationResult]:
        ...


class NoOpValidator:
    def validate(
        self,
        response: TransportResult,
        *,
        expected_resource: str | None = None,
        expected_profile: str | None = None,
    ) -> list[ValidationResult]:
        return []


class BasicFHIRValidator:
    def validate(
        self,
        response: TransportResult,
        *,
        expected_resource: str | None = None,
        expected_profile: str | None = None,
    ) -> list[ValidationResult]:
        content_type = next(
            (
                value
                for key, value in response.response_headers.items()
                if key.lower() == "content-type"
            ),
            "",
        )
        if "fhir+xml" in content_type.lower() or response.response_text.lstrip().startswith("<"):
            return [
                ValidationResult(
                    name="FHIR parse",
                    state=SKIP,
                    message="FHIR XML structural validation is not implemented in v0.1",
                )
            ]
        looks_fhir = (
            "fhir" in content_type.lower()
            or '"resourceType"' in response.response_text[:1000]
        )
        if not looks_fhir:
            return [
                ValidationResult(
                    name="FHIR parse",
                    state=SKIP,
                    message="response does not advertise or resemble FHIR JSON",
                )
            ]

        try:
            resource = parse_fhir_resource(response.response_text)
        except Exception as exc:
            return [
                ValidationResult(
                    name="FHIR parse",
                    state=ERROR,
                    message=str(exc),
                )
            ]

        results = [
            ValidationResult(
                name="FHIR parse",
                state=PASS,
                observed=resource.get("resourceType"),
            )
        ]

        if expected_resource:
            observed = resource.get("resourceType")
            results.append(
                ValidationResult(
                    name="FHIR resourceType",
                    state=PASS if observed == expected_resource else FAIL,
                    expected=expected_resource,
                    observed=observed,
                )
            )

        if expected_profile:
            profiles = meta_profiles(resource)
            results.append(
                ValidationResult(
                    name="FHIR declared profile",
                    state=PASS if expected_profile in profiles else FAIL,
                    expected=expected_profile,
                    observed=profiles,
                )
            )
        return results
