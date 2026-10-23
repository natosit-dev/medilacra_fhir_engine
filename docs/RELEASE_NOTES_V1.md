# Medilacra v1 — Release Notes

**Provisional release title:** Medilacra v1 — Unified Synthetic Clinical and Operational Testing Environment

**Release type:** Initial local, single-user baseline. **Product:** Medilacra. SHN is one experimentally tested integration, not the entire product.

Medilacra v1 brings its existing synthetic clinical simulation and operational interoperability testing interfaces into a single Streamlit application, preserving the functionality of the original Medilacra MVP-0, SHN Workbench, and extracted FHIR Engine components before a future unification of their internal APIs.

## What's included

- **Clinical reality:** synthetic patients, encounters, observations, transactions and HL7 v2 generation; SDOH/SPCU enrichment; scenario configuration; local DuckDB persistence experiments.
- **Operational reality:** TestSystem inventory, connection and HTTP probes, local IRIS FHIR and SHN test endpoints, None/Basic/Bearer/OAuth2 credential methods, FHIR TestScript runner, assertions, basic FHIR response inspection, regression comparison and evidence ZIP exports.
- **Experiments:** SHN provider ePA CRD/DTR/PAS reference workflows and controlled TP/TN test cases, plus the existing DiScO Inferno and PIQI interfaces (with limitations noted below).
- **Human-readable inspection:** TestScript guide explains each operation and assertion, states, validation results and execution phases. Run records preserve request/response and configuration provenance.
- **SHN credential selection:** one gitignored local client JSON path shared between the Workbench and ePA workflow.
- **DTR compatibility:** explicit recognition of the published `PackageBundle` (DTR 2.0) and `packagebundle` (DTR 2.2) spellings, plus their corresponding OperationOutcome parameter names; the original spelling remains visible in evidence.

## Observed baseline — October 23, 2026

Acceptance was conducted in Windows WSL2 with Python 3.10 and local Streamlit. **80 local offline tests passed** (17 Engine/navigation, 26 Workbench and 37 selected MVP-0), with matching successful GitHub Actions runs.

- **IRIS:** FHIR CapabilityStatement TestScript PASS, HTTP 200. The paired regression comparison found zero content differences.
- **SHN service discovery:** `GET /cds-services` returned HTTP 200 and both explicit assertions passed. Automatic **FHIR parse SKIP is expected**, because CDS Hooks discovery JSON is not a FHIR resource.
- **SHN TP-01:** five live operations completed successfully. The PAS review action was **A4 Pending** (not authorization approval).
- **SHN TP-02:** DTR and PAS steps passed, including live confirmation of the older `PackageBundle` spelling. PAS reported **A1 Certified in total**. The entire test retained one **known CRD expectation mismatch**: staff-draft `doc-needed=no-doc`, observed `admin`. This is intentionally reported rather than suppressed.
- **Evidence:** user exercised exports, regression inspection and DiScO tooling; raw test ZIPs are not included in the source distribution.

See the [October 23 acceptance record](RELEASE_ACCEPTANCE_2026-10-23.md) for the run IDs, evidence ledger and precise scope of those observations.

## How to run locally

Requires Python 3.10+ and the optional services/data files used by each experiment.

```bash
git clone https://github.com/natosit-dev/medilacra_fhir_engine.git
cd medilacra_fhir_engine
python -m pip install -r requirements-unified.txt
python -m streamlit run app.py
```

SHN OAuth requires a **separately obtained** client JSON file stored locally, outside Git; see [SHN client JSON setup](SHN_V1_CLIENT_JSON_SETUP.md). The included example credential profile contains no secrets.

## Scope and known limitations

- This is a **single-user, locally executed** research and baseline-testing environment, not a production healthcare service or multiuser server. The temporary compatibility launcher changes the process-wide working directory.
- Full PIQI conversion is **deferred**; the external converter at `apps/piqitt/scripts/fhir_convert_backend.py` is not present.
- The TP-02 CRD discrepancy remains open pending agreement on the authoritative payer/test contract.
- The current basic FHIR validator does not perform full StructureDefinition / implementation-guide conformance validation. PAS review outcomes must not be confused with transport success.
- DuckDB writes were observed during acceptance, but record contents were not independently inspected in the final pass.
- The standalone extracted Engine package still has its historical `0.1.0` Python package version and source-preserving compatibility API. This **Medilacra product v1** release does not claim E-001 Engine behavioral parity or a stable canonical public Engine API.
- Historical test expectations, synthetic reality, raw observations and derived interpretation are deliberately distinguished; the release does not certify SHN, IRIS or any payer.

## License, data and publication

The integrated project's license target is **GNU GPL version 2** for code the project is authorized to distribute under those terms; see root `LICENSE` and `apps/workbench/LICENSE`. Third-party dependencies, clinical terminologies, exported schemas and imported artifacts retain their own rights.

**Before public publication:** complete the [publication review](PUBLICATION_AUDIT_2026-10-23.md). Tracked historical staging files and third-party terminology/schema assets require inspection. The existence of GPLv2 text does not establish redistribution rights for those assets.

Do not distribute private SHN run evidence, credentials, token values, patient data or other confidential source artifacts. The archived live test ZIPs described in the acceptance ledger are intentionally excluded.

**Provenance:** Human-tested application baseline `82c184146afcac3979ed86808ddf91c6d5fc207d` with two locally modified YAML data caches. Release documentation revisions are subsequent commits; the eventual release tag should record the reviewed, clean commit being published.
