# SHN Testing Requirements — Working Inventory

**Snapshot:** 2026-10-31  
**Status:** Provisional working inventory, not an SHN-approved specification, a certification claim, or legal advice.  
**Maintenance:** Read-only in the Workbench. Review against new source documents and SHN decisions next week; revise this Markdown rather than editing assertions to force passing results.  
**Purpose:** Translate named needs and observable behavior into reproducible experiments. A documented promise, a deployed capability, a passing test, and proven conformance are different things.

## 1. Boundaries and evidence vocabulary

- **System under test:** SHN provider-facing endpoint, gateway behavior and configured payer-side participants. Medilacra is an independent synthetic provider/test client; SHN is an integration, not Medilacra's product boundary.
- **Observed:** Raw request/response, transport metadata or dated human-executed run, with a run ID and environment. **Implemented:** Code or a deployed endpoint explicitly inspected. **Specified:** A dated versioned contract. **Verified:** An independently replayable test tied to that contract. **Unresolved:** A disputed or missing source.
- **Current reference surface:** `pa-test.shn-preview.org`; SHN routes `00300` and `00301` as represented in existing fixtures. Route-to-IG equivalence must be checked against target configuration rather than inferred from route numbers. AEGIS Touchstone CRD transport exists in a separate Medilacra feature branch.
- **Existing evidence:** Reference-suite TP-01–TP-05 and TN-01–TN-10, scenario workflows, request/response files, `run.json`, `events.jsonl`, SHA-256 artifact inventory, correlation/trace links and Workbench exports. Preserve original observations.
- **Planning horizon:** SHN's stated January 1 internal limited payer/provider objective, and the separately applicable 2027 payer API compliance milestone, are context for prioritization—not proof of functionality, regulator-approved acceptance criteria, or a replacement for counsel's interpretation.

## 2. Current experiment requirements

| ID | Question or test requirement | Evidence / acceptance boundary | State on 2026-10-31 |
|---|---|---|---|
| SHN-TST-001 | Inventory each *advertised* service, hook, endpoint, version, payer route and participant configuration before testing. | Discovery response and timestamp, target URL/version, separate documented/deployed observations. | Partially exercised; full matrix open. |
| SHN-TST-002 | CRD `order-sign` from a synthetic patient, Coverage and draft ServiceRequest, maintaining payer route and clinical links. | Captured request, response, correlation IDs, resulting Coverage Information and scenario assertions. | Existing TP/scenario coverage. |
| SHN-TST-003 | Preserve every CRD Coverage Information occurrence, including multiple coverages and conflicting/indeterminate values; do not overwrite or invent a single answer. | Lossless interpreted occurrences; explicit ambiguity instead of a last-value-wins scalar. | Parser improvement proposed. |
| SHN-TST-004 | Keep `order-dispatch` capability claims separate from provider-test discovery. Check unsupported-hook behavior without calling it conformance. | Compare discovery, versioned docs and valid hook-specific requests. TN-07/TN-08 remain documented negative experiments. | Conflict open; no positive capability claimed. |
| SHN-TST-005 | DTR package retrieval accepts only the actually observed supported parameter conventions; questionnaire canonical originates from live CRD. | DTR request, package, selected canonical and version-specific source contract; no fabricated canonical. | Existing 2.0/2.2 experiments; normative validation open. |
| SHN-TST-006 | QuestionnaireResponse answers come from mapped synthetic clinical facts; reject unmapped required items, wrong subject/Coverage and changed question semantics. | Mapping provenance, question text/type checks, patient/Coverage consistency, captured QR. | Implemented in current provider workflow; broaden fixtures as needed. |
| SHN-TST-007 | PAS submit/inquiry and DTR relaunch preserve claim/authorization/CommunicationRequest linkage and payer responses. | Captured sequence, PAS status/review action, trace handoff and inquiry output. | TP-01 and scenario coverage; broader states open. |
| SHN-TST-008 | Negative/failure cases cover bad routing, broken patient linkage, invalid/missing payloads, unsupported service, reused correlation and token expiry. | One controlled mutation per experiment, recorded actual HTTP/body; do not replace observed failures with invented spec targets. | TN suite exists; expectations disputed in places. |
| SHN-TST-009 | Validate syntax, semantic invariants and relevant versioned FHIR/CRD/DTR/PAS profiles as *distinct* checks. | Named validator/version/profile plus OperationOutcome and failure details; basic JSON parse is not full IG validation. | Basic FHIR inspection available; full profile validation unverified. |
| SHN-TST-010 | Preserve transport identity: authentication boundaries, attempt/correlation/leg IDs, retry behavior, failure semantics and traceability across every hop. | Fresh invocation IDs; safe auth metadata; request/response/status per leg; delivered/received/failed must not be conflated. | Partially instrumented; independent gateway tracing needed. |
| SHN-TST-011 | Measure latency with configurable thresholds and explicitly named start/stop boundaries. | Raw total elapsed and individual HTTP-attempt time, effective config, thresholds, warning/failure result; no asserted normative budget absent a source. | Total elapsed exists; configurable assessment requested. |
| SHN-TST-012 | Store and export reproducible *synthetic* execution evidence without passwords, bearer tokens or identifiable patient data. | Run/test identity, test contract, code/ref, input/output, evaluation, hashes, timestamp and correlation references. | Existing full logs and ZIP exports; audit sanitization before external release. |
| SHN-TST-013 | Exercise multiple payer coverages, version negotiation, 2.1 and cross-version transformations only where target behavior is specified and fixtures exist. | Distinguish client line, payer line, transformation and response; mark unavailable configurations not tested. | Future coverage, not current product defect. |
| SHN-TST-014 | Keep AEGIS Touchstone CRD proxy validation as a transport variant, preserving SHN OAuth routing and direct SHN DTR/PAS/inquiry. | Distinct direct-vs-proxy tests and request/response artifacts. | Separate feature branch; not established as merged. |
| SHN-TST-015 | Reconstruct handoff/failure clocks at gateway, hub and receiver (including time of receipt and explicit negative acknowledgments). | Event evidence and contractual source for each clock; transport success alone is not clinical delivery. | Architectural investigation; no accepted event contract. |
| SHN-TST-016 | Inspect data persistence, PHI-bearing paths, retention, access, audit, geography and HIPAA role assignment without assuming conduit exemption. | Deployment/runtime inspection plus counsel/security determination; no assertion that a payload-blind design is automatically exempt. | Authority and deployment facts unresolved. |
| SHN-TST-017 | Compare SHN documented capabilities to deployed behavior, avoiding source-of-truth inference from AI-generated notes or code alone. | Requirements-to-implementation-to-execution matrix; discrepancies remain open with dated owners. | Ongoing independent validation need. |

## 3. Known disagreements and exclusions

- **TP-02:** The Oct 23 accepted run reported CRD `doc-needed=no-doc` expected vs `admin` observed, while DTR/PAS succeeded. Keep the disagreement visible until source owners establish the contract; do not relabel it green.
- **Order-dispatch:** Provider-test service discovery was reported not to advertise `shn-order-dispatch`; TN-08 expects a 404 for that refusal boundary. Other gateway documentation described order-dispatch support. Do not resolve the contradiction by assuming either source is authoritative.
- **HTTP 500/502 and OperationOutcome:** Document actual responses separately from any normative error requirement. A returned error can be useful observed behavior and a conformance failure at the same time.
- **Profile validation:** The current Workbench `BasicFHIRValidator` checks basic FHIR parsing/type/profile declaration; it cannot establish full StructureDefinition/IG conformance. The test harness should not claim that it can.
- **2.2 request authorization:** Strict 2.2 CRD fixtures and a properly scoped FHIR server authorization source need separate verification. SHN gateway OAuth is not automatically a FHIR-server token. Do not insert live tokens into evidence.
- **Delaware and other state clocks:** Recoupment, challenge, receipt, retention and information-blocking obligations need authoritative legal and contractual sources; this inventory records questions, not approved interpretations.
- **Not currently claimed:** Production-readiness, comprehensive CRD 2.1 behavior, full payer directories, all hooks, certification, independent HIPAA legal classification, or network-wide SLAs. The previously discussed 99.9% SLA / 30-minute assessment is a contract question, not the same thing as a per-request performance threshold.

## 4. Test execution rule

1. Identify target environment, participant/route, protocol/IG version, discovery result and effective non-secret configuration.
2. Declare the test objective and assertion source: observation-only, local experiment expectation, partner contract, IG conformance, or operational SLO.
3. Generate synthetic reality and capture the exact payload emitted (not merely the template used to make it).
4. Record response and timing independent of pass/fail; retain trace/correlation identifiers, complete synthetic artifacts and software revision.
5. Assess only what was asserted. A missing capability is **not tested/unavailable**, not silently passed. Conflicting observations are **unresolved**, not overwritten.
6. Export immutable observed evidence and preserve the original expectation. Changes to tests must create a new version, not rewrite a historical run.

## 5. Questions for the next requirements revision

- Which transaction types and which named participants actually constitute the January 1 internal target?
- Which service/IG combinations are mandatory, optional, or explicitly unsupported at each SHN endpoint?
- What are the source documents and accountable owners for discovery, FHIR conformance, failed-delivery behavior and error mappings?
- Which clocks begin on submission, hub acceptance, recipient receipt, business acknowledgment and final processing?
- Which timing SLOs are operative, how are they measured, and do they apply to the gateway, a payer, or end-to-end?
- What test rights, read-only runtime access, trace retention, infrastructure and independence are authorized for validation?
- Which legal/security decisions govern PHI handling and persistence at every hop?
- Which AEGIS/Drummond/MITRE/ONC artifacts or external test fixtures are usable, and what license/version applies?

## 6. Working references and change control

- Existing source: `docs/RELEASE_ACCEPTANCE_2026-10-23.md`, `docs/RELEASE_DECISIONS_2026-10-23.md`, `apps/mvp0/docs/SHN_REFERENCE_TEST_SUITE_BUILD_PLAN_2026-10-12.md`, `apps/mvp0/docs/SHN_FULL_EXECUTION_LOGGING_BUILD_PLAN_2026-10-14.md` and SHN Workbench run exports.
- Further context: discussions and observations through 2026-10-31 concerning SHN gateway testing, privacy/operational governance, AEGIS, failure clocks and implementation discrepancies. These are **not independently validated source documents**.
- **Next update:** Replace provisional assertions only when source-backed requirements arrive. Record source URL/document version, owner, date, affected requirement IDs, and test implications in the revision.
