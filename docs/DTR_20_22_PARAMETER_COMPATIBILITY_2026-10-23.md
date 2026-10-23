# DTR response names across 2.0 and 2.2 — 2026-10-23

**Status:** Compatibility fix implemented in original MVP-0 code used by the unified Streamlit application; replay tests added. Live retest completed successfully on 2026-10-23; see `docs/RELEASE_ACCEPTANCE_2026-10-23.md`.

## Why TP-02 reported a missing package

The SHN 00300 reference payer returned a FHIR `Parameters` resource with a Bundle named `PackageBundle`, containing the expected `PriorAuthRequired` Questionnaire and QuestionnaireResponse. The original MediLacra summaries and both DTR documentation materializers looked only for `packagebundle` and erroneously interpreted the returned package as absent.

This **is an IG-version distinction**:

- **DTR 2.0.1 (STU2):** `PackageBundle`, `operationOutcome`.
  Source: https://hl7.org/fhir/us/davinci-dtr/STU2/StructureDefinition-dtr-qpackage-output-parameters.html
- **DTR 2.2.0:** `packagebundle`, `outcome`.
  Source: https://hl7.org/fhir/us/davinci-dtr/en/OperationDefinition-questionnaire-package.html
- **Observed SHN 00300:** `PackageBundle` together with `outcome`, a mixed spelling combination. The bundle itself is not absent; assess response conformance against the actual route/version contract separately.

## Change

One explicit, shared allowlist handles the two documented package and OperationOutcome parameter-name spellings. It is used by:

1. The provider DTR response materializer (`connectathon/shn_provider/dtr.py`);
2. The older lumbar-fusion DTR QuestionnaireResponse materializer (`connectathon/shn_dtr_questionnaire_response.py`);
3. The DTR summary used by the reference suite (`connectathon/shn_provider/summaries.py`).

The summary now preserves the exact incoming names under `package_parameter_names` and `outcome_parameter_names` alongside the interpreted contents.

**No global case-insensitive JSON lookup**: FHIR `resourceType`, JSON members, canonical URLs, codes and PAS `responseBundle` remain exact. No request payloads or contract expectations are modified. The imported MVP-0 subtree is the active runtime; the M-001 hash-locked Engine harvest under `src/` remains untouched until its own parity/refactor milestone.

## Similar capitalization audit

The identified DTR package readers were all updated. The DTR outcome reader now also recognizes `operationOutcome` (2.0.1) and `outcome` (2.2.0). PAS inquiry expects `responseBundle`, as published in PAS 2.2.1, so it remains exact. The CRD response uses `systemActions` as specified by CDS Hooks, which we did not change.

## How to test

```bash
cd ~/code/medilacra_fhir_engine
git pull --ff-only
(cd apps/mvp0 && python -m pytest -q \
  tests/test_shn_dtr_parameter_versions.py tests/test_shn_reference_suite.py)
```

For a live SHN confirmation, run **TP-02** from the unified app against route 00300 and inspect the DTR summary. It should show `package_present=true`, the `PriorAuthRequired` canonical, and `package_parameter_names=["PackageBundle"]`.

**Expected remaining TP-02 discrepancy:** the staff draft specifies CRD `doc-needed=no-doc` but the live payer returned `admin`. This is a **separate** contract mismatch. Fixing DTR interpretation will not automatically make overall TP-02 pass against the existing draft.

Evidence from the original run is immutable; rerun and compare new output rather than rewriting old archives.
