# Medilacra v1 — Release Acceptance (2026-10-23)

**Disposition:** PASS for the initial local, single-user baseline, with explicit exceptions below. Approved by user through a hands-on acceptance walkthrough and uploaded run exports.

**Provisional name:** Medilacra v1 — Unified Synthetic Clinical and Operational Testing Environment.

**Tested integration baseline:** `feat/unified-medilacra` commit `82c184146afcac3979ed86808ddf91c6d5fc207d`. Runtime: Windows WSL2, Python 3.10.21 (`dev310`), local Streamlit, IRIS FHIR and SHN provider test endpoint. Latest CI for baseline: [GitHub Actions 39988928432](https://github.com/natosit-dev/medilacra_fhir_engine/actions/runs/39988928432), 17 root Engine/navigation tests + 26 Workbench + 37 selected MVP-0 regression tests passed.

**Important provenance qualification — resolved against terminal output:** the user supplied the original WSL `git status --short` output from the acceptance run: exactly two tracked YAML cache files were modified (`apps/mvp0/data/acs_poverty_cache.yaml` and `apps/mvp0/data/airnow_cache.yaml`). Branch `feat/unified-medilacra` and HEAD `82c184146afcac3979ed86808ddf91c6d5fc207d` were confirmed, and `git pull --ff-only` reported "Already up to date." The working tree was **not clean** at that time; no Python code modifications or untracked files were shown. This explains the likely source of the archived runs' `git_dirty: true` flags but cannot establish that the cache contents were identical throughout execution. The live results remain valid observed evidence; final release reproducibility still requires checking the final committed release candidate in a clean checkout or worktree.

## Human acceptance — user-reported

| Area | Manual observations / acceptance | Qualification |
|---|---|---|
| Source/CLI | **Terminal output shared and verified:** `git pull --ff-only` up to date, correct branch/HEAD, two modified tracked YAML caches; 17 root + 26 Workbench + 37 selected MVP-0 tests PASS locally. | **80/80 passed** in user's `dev310` environment; initial working tree was dirty, not clean. CI independently passed the same tests at the recorded SHA. |
| Unified Streamlit navigation | Home + 13 views in Clinical Reality, Operational Reality, Workflows & Experiments and Inspection & Tools exercised. | PIQI function is deferred below. |
| HL7 Message Generator | Synthetic messages including SDOH/SPCU generated; output inspected. | Acceptance is local functional, not population-level clinical validation. |
| Message Configuration | ADT, ORU, DFT/SDOH previews exercised after panel cleanup. | YAML warnings/changes noted by user; not independently inspected. |
| Site & Scenario Setup | `Medilacra_Health_System` loaded and Validate & Preview used. | — |
| Generate & Persist | DuckDB database file changed after a run. | Contents **not** independently inspected; persistence effects observed, database correctness not verified. |
| Test Systems/Connection Lab | IRIS/SHN systems, probe and endpoint behavior exercised. | Saved/configured does not establish authenticated or functional. |
| Authentication | Local SHN JSON recognized, OAuth acquisition, shared path across app pages checked; secret not displayed in UI. | File remains local/ignored; live FHIR operation is separate from `/healthz` check. |
| FHIR TestScript Runner | IRIS CapabilityStatement and SHN provider connectivity run; expandable plain-language guide and action details work. | Basic FHIR validator correctly SKIPs CDS Hooks non-FHIR response. |
| SHN ePA experiment | TP-01 and TP-02 new live evidence archived. | TP-02 overall FAIL is a known CRD draft expectation disagreement; DTR/PAS passed. |
| Workbench Evidence | ZIP/transaction logs and regression comparison exported. | 17-run archive includes historical failures; it is not 17 newly passing runs. |
| DiScO Inferno | User reports working UI and ZIP export (earlier archive reviewed). | No new DiScO archive attached during this final pass. |
| PIQI Connectathon | Tool is reachable, but converter `apps/piqitt/scripts/fhir_convert_backend.py` is absent. | **Deferred**, not a demonstrated working feature. |

### Attached Oct 23 evidence ledger

| Evidence ID | Supplied archive / comparison | Observed |
|---|---|---|
| E-01 | `toolbench-run-iriscapabilitystatement-iris-fhir-local-20261023T190940Z-490ee39e.zip` | PASS; GET /metadata 200; 3 actions; basic FHIR parse PASS; 173.8ms |
| E-02 | `toolbench-run-shnproviderconnectivity-shn-provider-test-20261023T191102Z-2ba2935c.zip` | PASS; GET /cds-services 200; 3 actions; FHIR parse SKIP (CDS Hooks JSON), 385.8ms |
| E-03 | `medilacra-test-log-tp01-20261023T191343Z-314118ad.zip` | PASS, 5/5 operations HTTP 200, ~3.75s, 82 events; PAS A4 Pending, inquiry 4 responses; 20/20 artifact SHA-256 checks match after mapping archived artifacts paths |
| E-04 | `medilacra-test-log-tp02-20261023T191404Z-b3f6f429.zip` | Overall FAIL (only CRD `doc-needed` expected no-doc, observed admin); DTR recognized `PackageBundle`, 1 Questionnaire, 1 QuestionnaireResponse; PAS A1 Certified in total, authorization ID `AUTH-0006`; 12/12 SHA-256 checks match |
| E-05 | `toolbench-transaction-logs-20261023T191601Z.zip` | Collection of 17 historical runs, 31 transactions and 525 events; 10 passed/7 failed across history, **not** just the final two tests |
| E-06 | `regression-iriscapabilitystatement-iris-fhir-local-20261023T191043Z-5ad16b99-vs-iriscapabilitystatement-iris-fhir-local-20261023T191031Z-8d10cb93.json` | 0 differences; GET /metadata baseline 35.2ms, current 41.8ms (+6.6ms) |
| E-07 | User-pasted WSL terminal acceptance output (`git pull --ff-only`, branch, `git status --short`, `git rev-parse HEAD`, and three `pytest -q` commands) | Branch `feat/unified-medilacra`, HEAD `82c184146afcac3979ed86808ddf91c6d5fc207d`; exactly two modified tracked caches, no source files shown as modified; **17 passed in 0.16s, 26 in 0.30s, 37 in 0.44s**. Local result **80/80 PASS**. |

Previous accepted evidence: Oct 21/22 TP-01, local IRIS metadata/CRUD scenarios, DiScO archives, and Oct 23 TP-02 DTR repair run are retained in prior conversations and [M-003 acceptance](M003_ACCEPTANCE_2026-10-21.md); new archives are **not** added to Git.

### Validation distinction

The SHN provider-connectivity `GET /cds-services` response is CDS Hooks discovery JSON, not FHIR resource JSON. `BasicFHIRValidator` correctly reports `FHIR parse: SKIP`; this neither overrides nor invalidates the two explicit passing TestScript assertions. A passing test is scoped to those actual assertions, not a general protocol conformance certification.

### Credentials and data boundary

The Git-tracked Workbench `config/credentials/examples/shn-provider-client-secret.json` is **a profile with a local path reference, not a secret**. The actual path under `apps/workbench/config/credentials/local/secrets/` is excluded by the subtree `.gitignore`; no file in that local directory exists in the reviewed Git tree. User can verify with `git check-ignore -v` and `git ls-files --`. Exports undergo sanitization but should be reviewed before public distribution; this record does not publish credentials, bearer tokens, real PHI, or raw private SHN artifacts.

## Known / deliberately deferred

1. PIQI converter path `apps/piqitt/scripts/fhir_convert_backend.py` missing. PIQI full path **not accepted**; after-v1.
2. TP-02 CRD expects `doc-needed=no-doc` in staff draft; SHN reference payer returns `admin`. Keep as openly reported assertion mismatch until contract owners resolve.
3. Full Engine E-001 parity and imported code deduplication remain pending; current stable behavior uses MVP-0 and Workbench trees.
4. Legacy Streamlit compatibility launcher changes process-wide CWD. **No multiuser-hosted claim.**
5. DuckDB file updated, contents not inspected. Two **tracked** local YAML data caches were modified at the initial acceptance check: `apps/mvp0/data/acs_poverty_cache.yaml` and `apps/mvp0/data/airnow_cache.yaml`. This is nonblocking for local functional acceptance but **does not satisfy** the clean-tree release check; do not discard or overwrite the caches without inspecting them.
6. SHN DTR demographic prepopulation warning remains, independent of successful package retrieval.
7. Full FHIR profile validation, IRIS CRUD re-run in the combined UI, and end-to-end production readiness are **not** claimed.

## Release hygiene after acceptance

- [x] Candidate CI verified at `82c1841`.
- [x] Local WSL CLI output received and cross-checked: 17 + 26 + 37 = **80 passing tests**; dirty status accounted for by two tracked data caches.
- [x] Human acceptance and evidence assembled.
- [x] Known PIQI / CRD / data-inspection limits recorded rather than hidden.
- [x] Local credential file ignored in Git tree and profile references only a path.
- [ ] Verify the **final** documentation/license commit in CI and clean working tree.
- [ ] Validate copyright authority and any third-party code before external distribution; GPLv2 text in integrated project files alone cannot change third-party rights.
- [ ] Merge/tag/publish separately, when release distribution is authorized.

**Release statement:** Medilacra v1 is a locally executable synthetic clinical and operational testing environment with a live-tested SHN ePA experimental integration. It is not a production gateway, shared multiuser server, or interoperability certification service.
