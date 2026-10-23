# Medilacra

**Unified synthetic clinical reality × operational reality testing platform**

## Medilacra v1 — accepted local baseline (2026-10-23)

**Provisional release title:** Medilacra v1 — Unified Synthetic Clinical and Operational Testing Environment. The title is temporary; Medilacra is the product, and SHN provider ePA testing is one experimental integration rather than the product's full scope.

**Acceptance:** local, single-user baseline demonstrated by human walkthrough and live/synthetic evidence; see [release acceptance](docs/RELEASE_ACCEPTANCE_2026-10-23.md), [decision log](docs/RELEASE_DECISIONS_2026-10-23.md) and [release notes](docs/RELEASE_NOTES_V1.md). Positive workflows TP-01 and a mixed-result TP-02 have been observed against SHN's provider test endpoint. TP-02's DTR/PAS steps pass; its CRD expectation disagrees with the draft contract. The PIQI converter is currently missing; the full PIQI workflow is not included in the accepted v1 claim.

**Release type:** source-available local development/baseline release, not a hosted multiuser service, compliance certification or healthcare production integration. The current application launcher uses process-wide working-directory changes. Treat claims and evidence as scoped to the exact test and environment.

**License target:** GNU GPL version 2 for project-owned code in the integrated repository. See LICENSE and apps/workbench/LICENSE. Relicensing requires rights to affected code; third-party notices and dependency license terms continue to apply. Do not distribute until they have been reviewed.

## Run the unified Medilacra application

The `feat/unified-medilacra` branch combines the existing MVP-0 synthetic
healthcare generator and SHN Workbench under one Streamlit app, while retaining
the extracted FHIR Engine library. Operational modules are preserved as
imported applications; a single shared Engine API is future refactoring work.

```bash
python -m pip install -r requirements-unified.txt
python -m streamlit run app.py
```

SHN OAuth client JSON setup (one file for Workbench and ePA):
[SHN v1 client JSON guide](docs/SHN_V1_CLIENT_JSON_SETUP.md).
Do not commit or display client secrets. A green file-valid indicator checks
only JSON structure; actual token acquisition must be tested separately.

**Deployment scope:** currently supported as a local, single-user
integration/pilot. The original Streamlit compatibility launcher uses a
process-wide working-directory change and must be refactored/tested before
multi-user server deployment. Combined-code license compatibility should be
resolved before external distribution.

User-friendly [TestScript Runner results guide](docs/TESTSCRIPT_RESULTS_GUIDE.md) explains action state, validation status, execution phase and each selected script's checks.

## M-001 source-preserving FHIR library harvest

**Beyond Conformance · Shared FHIR/ePA domain library**

Medilacra FHIR Engine provides deterministic synthetic clinical realities, scenario definitions, request builders, response interpreters, negative-test mutations, and cohort generation. It is intended to be imported by both **Medilacra MVP-0** (demo and bulk experiments) and **Medilacra SHN Workbench** (configurable capability testing and evidence inspection).

## Historical M-001 status — source-preserving harvest (October 21, 2026)

The M-001 harvest originally copied selected source files from `natosit-dev/medilacra` commit `2202e0b5503b60eaffba5e6ff0341df143a58008` without editing the harvested modules. Source-compatible `connectathon.*` and `hl7_demo.*` imports are intentionally retained to make behavioral comparisons possible. The preserved Engine still does **not** have a mature stable API; the root application now hosts the original MVP-0 and Workbench source trees without merging their implementations.

See [Harvest scope](docs/HARVEST_SCOPE.md), [source provenance](docs/harvest-manifest.json), and the [milestone and application-architecture decision record](docs/MILESTONES_AND_APP_TOPOLOGY_2026-10-21.md).

### Boundaries

- **Engine:** Build synthetic clinical data and FHIR payloads; interpret FHIR/ePA responses; create test cases, negative mutations and cohorts.
- **Workbench:** Configure environments and authentication; execute HTTP/FHIR TestScripts; assert, validate, snapshot, inspect and retain evidence.
- **MVP-0:** Run demonstrators, synthetic cohorts, clinical experiments and demo workflows.

The Engine does **not** own OAuth, endpoint-specific network transport, pass/fail decisions, deployment, or UI. Some harvested legacy modules still contain optional file-writing/CLI helpers; these are retained unchanged for initial parity, not promoted as the domain API.

## Installation

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
```

The package requires Python 3.10+ and Faker. In this compatibility cut, existing module names are used:

```python
from connectathon.shn_provider.summaries import summarize_crd, summarize_pas
from connectathon.shn_provider.mutations import apply_mutation
from connectathon.shn_provider.reference_payloads import build_crd
from connectathon.shn_bulk_crd import build_bulk_lumbar_fusion_batch
```

## Subsequent Engine validation objective

Reproduce previously observed TP-01 request builds and response interpretations against B-001 frozen artifacts, then add a stable `medilacra_fhir_engine` namespace. **Tests for source parity and integration remain pending until run and recorded; a GitHub commit alone is not E-001 validation.**

Reference: [Workbench B-001 TP-01 run record](https://github.com/natosit-dev/medilacra_shn_workbench/blob/main/docs/BASELINE_B001_SHN_REFERENCE_TP01_2026-10-20.md).
