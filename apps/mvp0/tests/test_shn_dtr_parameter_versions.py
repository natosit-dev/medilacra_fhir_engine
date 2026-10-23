"""Regress DTR version-specific response parameter names from SHN route 00300.

2.0.1 output: PackageBundle / operationOutcome.
2.2.0 output: packagebundle / outcome.
FHIR JSON property keys and resourceType values are NOT case-folded.
"""
from __future__ import annotations

import pytest

from connectathon.shn_dtr_parameters import dtr_package_bundles
from connectathon.shn_provider.dtr import _package_resources as provider_package
from connectathon.shn_dtr_questionnaire_response import (
    _package_resources as legacy_materializer_package,
)
from connectathon.shn_provider.summaries import summarize_dtr, summarize_inquiry


Q_URL = "http://example.org/fhir/Questionnaire/PriorAuthRequired"


def dtr_response(package_name: str, outcome_name: str) -> dict:
    return {
        "resourceType": "Parameters",
        "parameter": [
            {
                "name": package_name,
                "resource": {
                    "resourceType": "Bundle",
                    "type": "collection",
                    "entry": [
                        {
                            "resource": {
                                "resourceType": "Questionnaire",
                                "url": Q_URL,
                            },
                        },
                        {
                            "resource": {
                                "resourceType": "QuestionnaireResponse",
                                "questionnaire": Q_URL,
                                "subject": {"reference": "Patient/MBR-COVERED"},
                            },
                        },
                    ],
                },
            },
            {
                "name": outcome_name,
                "resource": {
                    "resourceType": "OperationOutcome",
                    "issue": [{
                        "severity": "information",
                        "diagnostics": "Patient demographic pre-population skipped",
                    }],
                },
            },
        ],
    }


@pytest.mark.parametrize(
    ("package_name", "outcome_name"),
    [
        ("PackageBundle", "operationOutcome"),  # published DTR STU2 2.0.1
        ("packagebundle", "outcome"),          # published DTR 2.2.0
        ("PackageBundle", "outcome"),          # live SHN 00300 mixed response
    ],
)
def test_dtr_summarizer_interprets_versioned_names(package_name, outcome_name):
    response = dtr_response(package_name, outcome_name)
    summary = summarize_dtr(response)
    assert summary["package_present"] is True
    assert summary["questionnaire"] == Q_URL
    assert summary["questionnaire_count"] == 1
    assert summary["questionnaire_response_count"] == 1
    assert summary["resource_counts"] == {
        "Questionnaire": 1,
        "QuestionnaireResponse": 1,
    }
    assert summary["outcome_issue_count"] == 1
    assert "pre-population skipped" in summary["error_text"]
    assert summary["package_parameter_names"] == [package_name]
    assert summary["outcome_parameter_names"] == [outcome_name]


@pytest.mark.parametrize("package_name", ["PackageBundle", "packagebundle"])
def test_both_document_materializers_accept_published_versions(package_name):
    response = dtr_response(package_name, "outcome")
    questionnaire, qr = provider_package(response)
    legacy_q, legacy_qr = legacy_materializer_package(response)
    assert questionnaire["url"] == legacy_q["url"] == Q_URL
    assert qr["questionnaire"] == legacy_qr["questionnaire"] == Q_URL


def test_unknown_spelling_not_silently_converted():
    response = dtr_response("PACKAGEBUNDLE", "outcome")
    assert not dtr_package_bundles(response)
    summary = summarize_dtr(response)
    assert summary["package_present"] is False
    assert summary["questionnaire"] is None
    with pytest.raises(ValueError, match="0 packagebundle"):
        provider_package(response)


def test_pas_inquiry_response_bundle_remains_case_sensitive():
    """PAS publishes responseBundle. No arbitrary folding of unrelated names."""
    bundle = {
        "resourceType": "Bundle",
        "entry": [{"resource": {
            "resourceType": "ClaimResponse", "outcome": "complete",
        }}],
    }
    correct = {"resourceType": "Parameters", "parameter": [
        {"name": "responseBundle", "resource": bundle},
    ]}
    wrong = {"resourceType": "Parameters", "parameter": [
        {"name": "RESPONSEBUNDLE", "resource": bundle},
    ]}
    assert summarize_inquiry(correct)["inquiry_response_count"] == 1
    assert summarize_inquiry(wrong)["inquiry_response_count"] == 0
