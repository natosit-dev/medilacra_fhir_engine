# Medilacra v1 — Decision Log (accepted 2026-10-23)

**Product:** Medilacra. **SHN:** experimental integration / first tested endpoint. **Title:** provisional, subject to later rename.

| ID | Decision | Disposition / rationale |
|---|---|---|
| D-01 | Medilacra is the product; SHN is an integration/experiment, not the defining product boundary. | Accepted |
| D-02 | Consolidate original MVP-0, Workbench and extracted FHIR Engine into one repository and one user-facing Streamlit app before refactoring. | Implemented as source-preserving subtrees + root launcher |
| D-03 | Preserve existing code and interfaces first, defer domain/transport deduplication and React/FastAPI. | Accepted; Engine API parity still pending |
| D-04 | Represent synthetic clinical reality and operational reality as first-class navigation perspectives. | Implemented navigation; unified internal data model pending |
| D-05 | Separate observed facts, contract assertions and interpretations in evidence. | Accepted; no HTTP/pass-status overclaim |
| D-06 | Use a shared local SHN JSON path for ePA and Workbench; never check secrets into Git. | Implemented and manually tested |
| D-07 | Retire redundant MVP-0 Admin, Note Coder, AI Admin and obsolete ODBC viewer. | Implemented |
| D-08 | Support documented DTR v2.0 and v2.2 operation parameter-name variants in active MVP-0 parser; preserve exact observed names. | Implemented; live TP-02 retest verified |
| D-09 | Keep disputed staff-draft CRD and negative test expectations open until owners determine normative behavior. | Accepted; no expectation rewritten to force green |
| D-10 | Human-readable TestScript explanation belongs in app alongside raw checks. | Implemented and exercised |
| D-11 | Medilacra v1 support is local, single-user development / baseline testing; no multiuser hosted claim. | **Approved 2026-10-23** |
| D-12 | Use GNU GPL **version 2** across project-owned files in this integrated repository. | **Approved 2026-10-23**; nested Workbench license text aligned. No assertion of rights over unrelated third-party code or dependencies |
| D-13 | Defer full PIQI converter path/integration until after v1; disclose `apps/piqitt/scripts/fhir_convert_backend.py` missing. | Accepted release exception |
| D-14 | Preserve test evidence unmodified; future Run Analysis may visualize provenance-linked exports. | Accepted future direction |
| D-15 | User reviews checkpoint and acceptance before docs commit, tag or release. | Acceptance review delivered 2026-10-23; release publication is separate |

## Remaining work not represented as completed

E-001 frozen Engine behavior parity and I-001 shared Engine consumers, PIQI converter integration, multiuser isolation, production deployment, broader FHIR IG conformance, additional payer fixtures, complete test suite coverage, packaging/versioning, and enhanced run analysis.

Use the release record for observed verification, not this decision log as a substitute for live evidence.
