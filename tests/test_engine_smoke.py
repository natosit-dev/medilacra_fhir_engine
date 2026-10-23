"""Initial offline import and deterministic-domain smoke checks.

These are not full B-001 parity or implementation-guide conformance tests.
"""
from connectathon.shn_provider.summaries import summarize_dtr, summarize_inquiry
from connectathon.shn_provider.mutations import apply_mutation
from connectathon.shn_provider.scenario import list_scenarios
from connectathon.shn_provider.test_case import get_test_case
from connectathon.shn_bulk_crd import build_bulk_lumbar_fusion_batch


def test_seeded_cohort_is_distinct_and_reproducible():
    one = build_bulk_lumbar_fusion_batch(start_seed=100, count=3)
    two = build_bulk_lumbar_fusion_batch(start_seed=100, count=3)
    assert one == two
    assert one["count"] == 3
    assert len({x["patient_id"] for x in one["cases"]}) == 3


def test_scenario_case_data_available():
    assert list_scenarios()
    case = get_test_case("TP-01")
    assert case.id == "TP-01"
    assert len(case.operations) == 5


def test_mutation_does_not_modify_original():
    request = {"prefetch": {"coverage": {
        "contained": [{"resourceType": "Organization", "identifier": [{"value": "00301"}]}],
        "payor": []
    }}}
    modified = apply_mutation("unknown_payer", request)
    assert request["prefetch"]["coverage"]["contained"][0]["identifier"][0]["value"] == "00301"
    assert modified.payload["prefetch"]["coverage"]["contained"][0]["identifier"][0]["value"] == "99999"
