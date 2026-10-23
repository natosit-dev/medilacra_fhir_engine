# Medilacra FHIR Engine — Milestones and Application Consolidation

**Recorded:** 2026-10-21  
**Status:** M-001 completed; application architecture **open for discussion**  
**Repositories:** [Engine](https://github.com/natosit-dev/medilacra_fhir_engine), [Workbench](https://github.com/natosit-dev/medilacra_shn_workbench), [Medilacra / MVP-0](https://github.com/natosit-dev/medilacra), [medilacra_app](https://github.com/natosit-dev/medilacra_app)

**Historical note (updated 2026-10-23):** This October 21 milestone/topology document predates the accepted unified Streamlit integration. A single UI (Option A) has since been selected and manually exercised. [Current release acceptance](RELEASE_ACCEPTANCE_2026-10-23.md) and [decision log](RELEASE_DECISIONS_2026-10-23.md) supersede the outdated 'architecture open' statuses below. E-001 canonical Engine parity remains pending.

## 1. Scope of this milestone record

Record the completed **source-preserving library harvest**, capture the proposal for an application interface as a **future milestone**, and preserve the user's original objective of **one consolidated application** as an active design option.

**Do not infer that three existing repositories require three applications.** Libraries, repository boundaries, execution processes, and user interfaces are separate architectural decisions.

## 2. M-001 — Source-preserving Engine harvest — COMPLETE

### Established

- Independent private GitHub repository: `natosit-dev/medilacra_fhir_engine`, with its existing GPL-2.0 license preserved.
- Editable Python package: `medilacra-fhir-engine==0.1.0` (Python 3.10+).
- **47** historical source artifacts copied at their exact Git blob identities: **24 Python modules**, **23 JSON files** comprising SHN scenarios, TP/TN reference test cases, and reference request fixtures.
- Harvest origin: `natosit-dev/medilacra` commit `2202e0b5503b60eaffba5e6ff0341df143a58008`; per-file original blob hashes in `docs/harvest-manifest.json`.
- Offline test suite: **5 passed** in the user's local `dev310` WSL environment on 2026-10-21 (0.16s), including source identity and basic synthetic cohort, scenario and mutation checks.
- Automated GitHub Actions run `39591150740` completed **successfully** at commit `3b3e3291dcc5894d59ab0d47242d877e92925aa6`.
- Source-file identity verified by comparing all 47 remote Git tree blobs against the source manifest; no changes to harvested source bytes.

### Explicit limits

- **E-001 full behavioral parity is NOT yet established.** The existing tests are integrity/smoke tests; no complete frozen B-001 response-processing comparison is yet recorded.
- The Engine still exposes compatibility imports under `connectathon.*` and `hl7_demo.*`; a stable `medilacra_fhir_engine.*` domain API remains a follow-on.
- Several historical modules retain optional file-output and CLI functions. These are legacy companions to domain functions, not a declaration that the Engine owns application orchestration.
- SHN OAuth, network client, transport, live `ReferenceSuiteRunner`, `ProviderWorkflow`, live send scripts, and evidence/export layer were intentionally **not** harvested.
- No `app.py` or `medi_lacra_app.py` exists in the Engine. This is intentional for M-001, not a permanent decision against an Engine inspector or a unified UI.

### Local validation reported by the user

```bash
cd ~/code/medilacra_fhir_engine
python -m pip install -e '.[dev]'
python -m pytest -q
# 5 passed in 0.16s (dev310)
```

### Relevant preceding baseline

[Workbench B-001](https://github.com/natosit-dev/medilacra_shn_workbench/blob/main/docs/BASELINE_B001_SHN_REFERENCE_TP01_2026-10-20.md) is the **live SHN TP-01 reference execution**. It records five successful reference operations and PAS-to-DTR trace handoff. M-001 establishes the **source extraction**, not a repetition of that live run under the Engine.

## 3. Pending milestones

| ID | Milestone | Acceptance criteria | Status |
|---|---|---|---|
| **E-001** | Frozen Engine behavioral parity | Compare seeded generated realities, CRD/DTR/PAS/inquiry payloads, response summaries, mutations, and cohort manifests against pinned MVP-0; compare the TP-01 response interpretation to preserved B-001 evidence without network calls | **Pending** |
| **M-002** | Select a unified application topology | Explicit decision on one UI vs several, one deployment vs several, source repo boundaries, shared engine/runner ownership, and local-to-Docker migration; write an ADR | **Open** |
| **M-003** | Application inspection surface | Navigate or inspect Engine-generated realities, messages, mutations and cohort manifests through the chosen application architecture; preserve offline usability | **Proposed, NOT committed to standalone `app.py`** |
| **I-001** | Integrate Engine with Workbench and MVP-0 | Both consumers use a pinned Engine version; no competing copies of domain code; existing B-001 run can be reproduced through an evidence-bearing integrated execution path with effective-config snapshot and versioned expectations | **Pending** |

**Order note:** E-001 can proceed before or alongside topology design. Do not make a new Engine-only UI a prerequisite for behavioral parity.

## 4. Application architecture — options to evaluate

### A. One application / one user-facing shell, modular internals

One navigational surface offers:

- **Generate / Explore:** Clinical reality, patient cohorts, FHIR messages and scenario selection.
- **Demonstrate / Bulk:** End-to-end ePA workflows, rules matrices and cohort experiments.
- **Test capabilities:** Configurable systems, credentials, TestScripts, capability-to-case coverage, assertions, validation.
- **Evidence:** Inspect raw transactions, derivation chains, configuration snapshots, versioned expected results, run comparisons and exports.

Underneath, Engine is an importable domain package; one execution/evidence foundation serves both demonstration and testing modes. **One UI does not inherently require one Git repo or one Python process.**

Advantages: unified navigation, context can follow a synthetic case from generation to tests and evidence; no competing frontends. Risk: coupling exploratory demo state and controlled test evidence if boundaries are not explicit.

### B. Separate MVP-0 and Workbench applications consuming one Engine

Keep distinct application shells, shared versioned Engine package, interoperable artifact and run IDs.

Advantages: least immediate UI disruption, existing demonstrations preserved. Risks: fragmented exploration across apps, duplicate identity/context handling, two evidence browsing experiences, and more runtime configuration.

### C. One product with separately deployed applications/services

Unified frontend with separate generation and execution services behind typed APIs, potentially React/FastAPI when needs justify it.

Advantages: independently scalable long-running bulk workloads; separation of resource-intensive generation and UI. Risks: deployment/service contracts/auth state far exceed our local primitive needs today.

### Relevant existing application surfaces

- `medilacra/medi_lacra_app.py`: existing Streamlit **HL7 message generator**, coupled to its broader `hl7_demo` pipeline.
- `medilacra_shn_workbench/app.py` and `pages/`: existing Streamlit test and evidence app.
- `medilacra_app`: repository README describes a proposed **React + FastAPI frontend**; its inspected root contains the README/license/ignore files, not a demonstrated working frontend.

These are **sources to evaluate**, not a reason to pick a framework immediately.

## 5. Decision criteria

When selecting an architecture, test it against concrete user journeys:

1. Generate one synthetic clinical reality and turn it into CRD → DTR → PAS inputs without re-keying identifiers.
2. Run one TP-01 reference case and then inspect exactly which capabilities each observation supports.
3. Generate 100 cases, isolate one anomaly, and navigate directly from cohort summary to full raw evidence.
4. Compare a frozen historical expected-results set to new observations with provenance and effective-config snapshot.
5. Run entirely offline with local fixtures, and later target local Docker/IRIS or hosted SHN by configuration.
6. Keep clinical-data generation and semantic interpretation independent from transport, auth, pass/fail and evidence ownership.

**Default evaluation preference (not a decision):** start by exploring **Option A, a single user-facing application with modular boundaries**, without assuming the entire codebase should be moved into one repository. Favor local simplicity over prematurely deployed microservices.

## 6. Architectural invariants

- **Capability is not scenario.** Scenarios exercise capabilities; individual observations are attached to executions and assessed against explicit versioned expectations.
- **Expectation is not observation.** Keep requirement/source, expected behavior, observed response, verified conformance, and human acceptance separable.
- **No duplicate engines.** Engine owns synthetic/domain FHIR construction and interpretation. Shared execution tooling owns auth, transport, request/response capture, assertions and evidence.
- **One operation for effective configuration snapshot**, attached to the execution; include resolved non-secret settings, file revisions, expectation provenance and software versions, excluding credential values.
- **MVP-0 breadth remains valuable.** Deterministic cohorts, rule matrix, negative mutations and response-dependent experimentation must survive consolidation.
- **Workbench depth remains valuable.** Raw payload inspection, capability assessment, transport diagnosis and evidence review must survive consolidation.
- **No claimed integrated baseline** until the chosen app actually exercises both modes and retains comparable execution evidence.

## 7. Decision log

| ID | Decision | Status |
|---|---|---|
| D-01 | Preserve the M-001 pure/domain source harvest as a separately versioned package | **Adopted** |
| D-02 | Do not add a standalone Engine `app.py` merely because it lacks a UI | **Provisional** |
| D-03 | Evaluate the user's preferred single-application experience first | **Adopted as design direction; topology not chosen** |
| D-04 | Maintain an independent source-integrity and offline behavioral-parity gate before modifying harvested functions | **Adopted** |
| O-01 | One repo vs several versioned repositories? | **Open** |
| O-02 | Streamlit shell vs React/FastAPI or hybrid? | **Open** |
| O-03 | Does a bulk cohort execute in the UI process, a worker, or a separately managed process? | **Open** |
| O-04 | Where does the one shared execution/evidence interface live? | **Open** |

**No application files or integration code were added by this documentation milestone.**
