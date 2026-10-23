# MediLacra SHN Workbench — Build Plan

**Version:** 0.1  
**Date:** 2026-10-15  
**Repository:** `natosit-dev/medilacra_shn_workbench`  
**Status:** Initial build plan  
**Scope:** MVP interoperability test bench inspired by the Touchstone execution model without recreating Touchstone.

---

## 1. Purpose

The current MediLacra SHN Provider page proved that the transport, workflow, evidence, and logging machinery works, but it also exposed a limitation: too much of the behavior is fixed around one provider-side workflow.

The Workbench should turn that implementation into a configurable interoperability test bench.

The core loop is:

```text
TestSystem
   +
CredentialProfile
   +
FHIR TestScript JSON
        ↓
generic runner
        ↓
HTTP / FHIR exchange
        ↓
assertions + minimal conformance checks
        ↓
raw evidence + logs + export
```

SHN and the local IRIS FHIR server are the first two configured systems. Neither should define the architecture.

The design goal is not to build a certification platform, conformance cathedral, or replacement for Touchstone. The goal is a small, inspectable tool that can:

1. define a system under test,
2. establish connectivity,
3. establish authentication,
4. execute a real FHIR TestScript,
5. inspect raw traffic,
6. evaluate a small useful subset of assertions,
7. preserve evidence,
8. compare observed behavior across runs.

---

## 2. Core Design Decisions

### 2.1 Use FHIR TestScript directly

FHIR `TestScript` JSON is the canonical test definition.

Do not translate it into a MediLacra-specific test schema merely because the runner implements only a subset.

When the runner encounters a valid TestScript feature it does not implement, report it explicitly as:

```text
UNSUPPORTED
```

Do not silently ignore it and do not approximate semantics.

This follows the successful PIQITT reference-bridge pattern:

```text
external standard artifact
        ↓
local binding/execution adapter
        ↓
local execution
```

### 2.2 Separate test system from test definition

A TestScript describes the test.

A TestSystem describes where it runs.

The same script should be executable against different systems without editing the script.

### 2.3 Raw traffic is a first-class output

The Workbench is an engineering surface, not primarily a presentation dashboard.

Default output should favor:

```text
REQUEST
RESPONSE
HEADERS
ASSERTIONS
LOG
```

using monospace/raw text rather than deeply nested interactive JSON trees.

Pretty JSON remains available, but is not the primary representation.

### 2.4 Capture before summarizing

Preserve raw requests, responses, headers, timings, assertion results, and execution events.

Summary views are derived from that evidence.

### 2.5 Minimal conformance

The Workbench executes and observes.

Validators validate.

The core should expose a validator interface rather than growing into a complete FHIR/IG conformance engine.

---

## 3. MVP Core Objects

Only four first-class objects are required for v0.1.

### TestSystem

Describes the system under test.

Example:

```json
{
  "id": "shn-provider-test",
  "name": "SHN Provider Test Endpoint",
  "base_url": "https://pa-test.shn-preview.org",
  "protocol": "fhir",
  "fhir_version": "4.0.1",
  "format": "json",
  "identity": {
    "user_key": null,
    "organization_key": null
  },
  "tls": {
    "verify": true
  },
  "credential_profile": "shn-client-secret"
}
```

Expected initial fields:

- id
- name
- base URL
- protocol
- FHIR version
- preferred format
- USER_KEY-style identity
- organization key / organization identity
- TLS verification behavior
- credential profile reference
- optional default headers

### CredentialProfile

Describes how authentication is obtained without embedding secret values in normal configuration.

Initial auth types:

- none
- Basic
- Bearer
- OAuth2 client credentials

Planned next:

- `private_key_jwt`

Credential profiles reference secret sources rather than storing secret values in committed configuration.

### TestScript

The original FHIR TestScript JSON resource.

The Workbench keeps the source document intact and builds a local execution view from it.

### TestRun

Local record of one execution:

- TestScript identity
- TestSystem identity
- CredentialProfile identity
- timestamps
- operations
- assertions
- transport results
- validation results
- execution events
- artifacts
- overall result

---

## 4. Gap Analysis

| Capability | Existing source | Action |
|---|---|---|
| DNS resolution | MediLacra Connectivity page | Reuse behavior; extract into pure Python |
| TCP probe | MediLacra Connectivity page | Reuse behavior; extract |
| TLS handshake | MediLacra Connectivity page | Reuse behavior; extract |
| Certificate inspection | MediLacra Connectivity page | Reuse behavior; normalize output |
| Port probe | MediLacra Connectivity page | Reuse as optional utility |
| Arbitrary HTTP request | MediLacra Connectivity page | Reuse behavior; move behind generic transport client |
| TLS verify toggle | MediLacra Connectivity page | Reuse |
| Timeout controls | MediLacra Connectivity page | Reuse |
| MLLP sender | MediLacra Connectivity page | Reuse later as optional adapter, not FHIR core |
| OAuth client credentials | MediLacra SHN provider client | Reuse and generalize |
| Token caching / expiry | MediLacra SHN provider client | Reuse and generalize |
| Retry metadata | MediLacra SHN provider client | Reuse and generalize |
| Correlation IDs | MediLacra SHN provider client | Reuse; make configurable |
| Safe credential handling | MediLacra SHN provider client/logging | Reuse policy and regression tests |
| Raw request/response capture | SHN reference suite | Reuse |
| Expected vs observed assertions | SHN reference suite | Reuse concept; remove SHN assumptions |
| Full execution logging | SHN logging layer | Port nearly intact |
| Artifact hashing | SHN logging layer | Reuse |
| Single-run ZIP export | SHN exporter | Reuse |
| Multi-run collection export | SHN collector | Reuse |
| Standard-artifact adapter pattern | PIQITT official-reference branch | Reuse architectural pattern |
| PASS/FAIL/SKIP/UNSUPPORTED states | PIQITT | Reuse and add ERROR |
| Deep FHIR path extraction | PIQITT | Reuse/tweak |
| FHIR `[x]` choice extraction | PIQITT | Reuse/tweak |
| Resource selector logic | PIQITT | Reuse only where useful |
| Regression comparison | PIQITT regression diff | Generalize from score drift to transaction/assertion drift |
| Flattened scorecard/export pattern | PIQITT | Reuse presentation idea |
| HL7 v2 → FHIR converter | PIQITT | Optional adapter later, not core |
| PIQI evaluation | PIQITT | Optional validator/plugin later |
| TestSystem model | None | Build new |
| CredentialProfile model | Partial behavior only | Build new abstraction |
| FHIR TestScript loader | None | Build new |
| Generic TestScript executor | None | Build new |
| Fixture resolver | None | Build new |
| Generic assertion engine | Partial in SHN/PIQITT | Build by generalizing existing primitives |
| Minimal validator interface | Partial | Build new |
| IRIS system config | Existing operational knowledge only | Build new config |
| Raw technical runner UI | None | Build new |

The project is therefore mostly extraction, generalization, and assembly rather than greenfield development.

---

## 5. Proposed Repository Structure

```text
medilacra_shn_workbench/
│
├── app.py
│
├── toolbench/
│   ├── systems.py
│   ├── credentials.py
│   ├── connectivity.py
│   ├── transport.py
│   ├── auth.py
│   ├── fhir.py
│   ├── testscript.py
│   ├── fixtures.py
│   ├── assertions.py
│   ├── runner.py
│   ├── validation.py
│   ├── logging.py
│   ├── regression.py
│   └── export.py
│
├── pages/
│   ├── 1_Test_Systems.py
│   ├── 2_Connection_Lab.py
│   ├── 3_Auth_Workbench.py
│   ├── 4_TestScript_Runner.py
│   └── 5_Evidence.py
│
├── config/
│   ├── systems/
│   │   ├── shn-provider-test.json
│   │   └── iris-local.json
│   └── credentials/
│       └── examples/
│
├── testscripts/
│   ├── smoke/
│   ├── shn/
│   └── iris/
│
├── results/
│   └── .gitignore
│
├── tests/
│
└── docs/
```

No database is required for the MVP.

Configuration, TestScripts, and result artifacts remain file-based.

---

## 6. Connectivity Layer

Harvest the existing MediLacra Connectivity page and move its logic out of Streamlit.

Target pure functions:

```python
resolve_dns()
probe_tcp()
probe_tls()
inspect_certificate()
probe_ports()
send_http()
```

The functions should return structured results rather than rendering UI.

Example TLS result:

```text
host
port
connected
tls_version
cipher
certificate_subject
certificate_issuer
not_before
not_after
latency_ms
error
```

The old MLLP sender should be retained later under an optional adapter such as:

```text
toolbench/adapters/mllp.py
```

It should not complicate the initial FHIR/TestScript path.

---

## 7. Generic Transport

Combine the useful parts of:

- MediLacra arbitrary HTTP connectivity testing,
- SHN provider transport,
- SHN evidence capture.

Conceptual interface:

```python
transport.request(
    method="POST",
    url=...,
    headers=...,
    body=...,
    auth=...,
    tls=...,
)
```

Generic result:

```text
request metadata
response status
response headers
response body
elapsed_ms
attempts
error
```

SHN-specific metadata such as:

- `X-Correlation-Id`
- `X-SHN-Leg-Id`
- operator trace URL

must be optional configuration/observation, not hard-coded transport semantics.

The transport layer must not know what CRD, DTR, or PAS means.

---

## 8. Authentication Workbench

Authentication is a first-class engineering problem and should have its own UI.

### MVP auth types

```text
None
Basic
Bearer
OAuth2 client_credentials
```

### Initial UI behavior

```text
AUTH PROFILE
[ SHN client_secret ▼ ]

Type:
OAuth2 client_credentials

Token URL:
/oauth/token

Client ID source:
client.json

Secret source:
client.json

[ Generate Token ]

HTTP 200
expires_in: 300
scope: system/Davinci.write
token age: 0 sec

[ Test Auth ]
```

### Credential boundary

Persist/log:

- auth method
- token endpoint
- token request status
- token acquisition time
- expiry
- scope
- whether cached token was reused
- secret source path/type

Never persist/log:

- client secret value
- bearer/access token
- Basic credential value
- Authorization header value
- private key
- client assertion

Port the whole-export secret-leak regression tests from MediLacra.

---

## 9. FHIR TestScript Loader

Load normal FHIR TestScript JSON.

Do not create a parallel MediLacra test-definition format.

The source TestScript remains available unchanged.

The loader should create a normalized execution view for the supported subset.

### Initial TestScript areas

- URL/name/description
- origin/destination
- fixture
- setup
- test
- teardown
- operation
- assert

Unsupported valid elements are preserved in source and surfaced as `UNSUPPORTED` when relevant.

---

## 10. TestScript MVP Subset

Do not implement the entire TestScript specification.

### Fixtures

Initial support:

- local JSON fixture
- embedded FHIR resource
- response/resource produced by an earlier operation

### Operations

Initial methods:

- GET
- POST
- PUT
- DELETE

Initial operation properties:

- path / URL
- source fixture
- target fixture
- Accept
- Content-Type
- configured headers

### Assertions

Initial assertions:

- HTTP status equals
- response header exists
- JSON parses
- FHIR resource parses
- resourceType equals
- JSONPath exists
- JSONPath equals/compares to value
- request method / request URL

Real TestScript `validateProfileId` requires StructureDefinition validation and is intentionally not approximated by checking `meta.profile`. Add a validator adapter when a real test requires it. FHIRPath and XPath remain explicit unsupported states in v0.1.

---

## 11. FHIR Utility Harvest from PIQITT

Adapt small, deterministic primitives rather than porting the PIQI engine.

Useful functionality:

### Deep extraction

Examples:

```text
Patient.birthDate
Observation.category*.coding*.code
```

### Choice values

Resolve FHIR choices such as:

```text
value[x]
```

against:

```text
valueQuantity
valueString
valueCodeableConcept
valueDateTime
...
```

### Resource selectors

Useful fallback pattern:

```text
resource: Observation
selector:
  category*.coding*.code == laboratory
```

Do not create a broad custom query language if TestScript/FHIRPath covers the real need.

---

## 12. Assertion Result Model

Use explicit execution states:

```text
PASS
FAIL
SKIP
UNSUPPORTED
ERROR
```

Definitions:

- **PASS** — assertion executed and succeeded.
- **FAIL** — assertion executed and evaluated false.
- **SKIP** — assertion does not apply due to its condition/context.
- **UNSUPPORTED** — valid TestScript behavior the Workbench does not yet implement.
- **ERROR** — assertion or execution could not run due to an execution failure.

Do not collapse these states into booleans.

---

## 13. Minimal Conformance Layer

Keep conformance deliberately narrow.

Initial layers:

```text
Transport
FHIR structure
Profile validation
```

Example result:

```text
HTTP                      PASS
JSON parse                PASS
FHIR resourceType         PASS
Expected declared profile PASS
FHIR validator            FAIL
```

Validator interface:

```python
Validator.validate(resource)
```

Initial implementations:

- `NoOpValidator`
- `BasicFHIRValidator`

Future adapters may include:

- PIQITT
- official HL7 validator CLI
- remote validator services

The generic runner should not absorb those engines.

---

## 14. IRIS as the Second System

IRIS should be present from the first usable runner so the architecture is forced to remain generic.

Initial IRIS TestScript:

```text
GET /metadata
    expect HTTP 200
    expect CapabilityStatement

POST Patient
    expect HTTP 200/201

GET Patient/{id}
    expect HTTP 200
    expect Patient

DELETE Patient/{id}
```

Architectural proof:

The same runner executes both IRIS and SHN without code changes.

Only TestSystem configuration, credentials, and TestScript should change.

---

## 15. SHN TestScript Migration

Do not immediately reproduce every current SHN reference test.

Start small:

1. connectivity/auth smoke,
2. one simple CRD exchange,
3. expand into DTR/PAS only after the generic runner is proven.

This is intentionally exploratory.

The point is to discover how far standard FHIR TestScript can describe the existing SHN flows before creating any extension mechanism.

Do not invent extensions preemptively.

---

## 16. Raw Runner UI

The TestScript Runner should look closer to a terminal/test harness than an executive dashboard.

Example:

```text
SYSTEM:      [ IRIS Local ▼ ]
TESTSCRIPT:  [ Patient CRUD ▼ ]

[ Run Step ] [ Run All ]

STEP 2 — POST Patient
HTTP 201
143 ms

REQUEST
────────────────────────────────────────
POST /Patient
Accept: application/fhir+json
Content-Type: application/fhir+json

{"resourceType":"Patient", ...}


RESPONSE
────────────────────────────────────────
HTTP/1.1 201 Created
Content-Type: application/fhir+json
Location: Patient/123/_history/1

{"resourceType":"Patient","id":"123",...}


ASSERTIONS
────────────────────────────────────────
PASS  status = 201
PASS  resourceType = Patient
PASS  id exists
```

Views:

```text
Raw
Pretty
Headers
Assertions
Log
```

Default to Raw.

---

## 17. Logging

Port the MediLacra execution logger and generalize event names.

Initial events:

```text
run.started
system.selected
testscript.loaded
fixture.loaded

auth.started
auth.token.requested
auth.token.acquired
auth.token.reused
auth.token.expired
auth.completed

operation.started
http.request.sent
http.response.received
assertion.evaluated
validation.started
validation.completed
operation.completed

artifact.written
run.completed
```

Preserve monotonically increasing sequence IDs as the authoritative execution order.

---

## 18. Evidence and Export

Reuse the MediLacra evidence model.

### Per-run artifacts

```text
<run-id>/
  run.json
  events.jsonl
  transactions.jsonl

  operations/
    01-get-metadata/
      request.txt
      response.txt
      request-headers.json
      response-headers.json
      result.json
```

### Single-run export

```text
toolbench-run-<run-id>.zip
```

### Multi-run collection

```text
toolbench-transaction-logs-<timestamp>.zip

collection.json
transactions.jsonl
transactions.csv
events.jsonl
runs/
  ...
```

Preparing an evidence bundle must never create network traffic.

---

## 19. Regression Comparison

Generalize PIQITT's regression-diff concept.

Initial comparison should focus on useful deterministic differences:

- operation count
- HTTP status
- assertion state
- selected observed values
- header presence
- response resource type/profile
- latency delta

Example:

```text
BASELINE                  CURRENT

HTTP 200                  HTTP 400
X-Correlation-Id present  X-Correlation-Id present
resourceType Patient      OperationOutcome
assert profile PASS       FAIL
latency 112 ms            381 ms
```

Do not begin with a sophisticated semantic diff engine.

---

## 20. Pages

### 1 — Test Systems

Create/edit/select:

- name
- base URL
- protocol
- FHIR version
- preferred format
- USER_KEY
- organization key
- TLS settings
- auth profile
- optional headers

### 2 — Connection Lab

- DNS
- TCP
- TLS
- certificate inspection
- port probe
- `GET /metadata`
- arbitrary HTTP request

### 3 — Auth Workbench

- select CredentialProfile
- acquire token
- inspect safe token metadata
- test authenticated request

### 4 — TestScript Runner

- choose TestSystem
- choose/load TestScript
- inspect script metadata
- run one step
- run all
- raw request/response
- assertions
- conformance results
- event log

### 5 — Evidence

- runs
- transactions
- raw evidence
- single-run export
- collection export
- baseline/current comparison

---

## 21. Explicitly Deferred

Do not build these in v0.1:

- full FHIR TestScript support
- TestScript authoring IDE
- visual workflow editor
- certification program management
- FHIR IG/package management UI
- terminology server
- account/user/role administration
- organization administration
- persistent database
- cloud deployment architecture
- scheduler
- notification system
- SMART app launch framework
- Inferno clone
- Touchstone-compatible server APIs
- general-purpose results warehouse
- complex analytics dashboards

Optional adapters such as PIQI evaluation and HL7 v2 → FHIR conversion can be added only after the generic runner is proven.

---

## 22. Build Sequence

### Pass 1 — Repository foundation

1. Establish package structure.
2. Add requirements.
3. Add test infrastructure.
4. Ignore local credentials/config overrides/results.
5. Preserve this build plan as the starting contract.

### Pass 2 — Connectivity extraction

6. Extract DNS logic from MediLacra.
7. Extract TCP probe.
8. Extract TLS handshake/certificate inspection.
9. Extract arbitrary HTTP sender.
10. Add pure-function tests.
11. Build thin Connection Lab page.

### Pass 3 — Systems and auth

12. Implement `TestSystem`.
13. Implement `CredentialProfile`.
14. Add SHN system config.
15. Add IRIS system config.
16. Generalize client-credentials token acquisition.
17. Add Basic/Bearer/None auth.
18. Port credential-leak regression tests.
19. Build Auth Workbench.

### Pass 4 — TestScript

20. Implement TestScript loader.
21. Preserve original source resource.
22. Normalize supported fixtures.
23. Normalize supported operations.
24. Normalize supported assertions.
25. Surface unsupported elements explicitly.

### Pass 5 — FHIR primitives and runner

26. Harvest PIQITT deep-path extraction.
27. Harvest FHIR `[x]` choice extraction.
28. Harvest useful selector behavior.
29. Build assertion engine.
30. Implement PASS/FAIL/SKIP/UNSUPPORTED/ERROR.
31. Build generic TestScript runner.
32. Build raw runner UI.

### Pass 6 — Prove genericity

33. Configure local IRIS.
34. Create/load Patient CRUD TestScript.
35. Run against IRIS.
36. Configure SHN.
37. Create/load SHN smoke TestScript.
38. Run against SHN.
39. Confirm neither execution requires runner code changes.

### Pass 7 — Evidence

40. Port RunLogger.
41. Port request/response artifact persistence.
42. Port hashing/index.
43. Port single-run export.
44. Port multi-run transaction collection.
45. Build Evidence page.

### Pass 8 — Regression

46. Generalize PIQITT regression comparison.
47. Compare baseline/current operation results.
48. Add compact difference view.
49. Add regression result to evidence export.

### Pass 9 — Stop

50. Use the tool on real interoperability work.
51. Record actual friction.
52. Add only the next capability demanded by a real test.

---

## 23. MVP Definition of Done

Version 0.1 is complete when the following works end-to-end.

### IRIS

```text
select IRIS TestSystem
        ↓
run DNS/TCP/TLS
        ↓
authenticate
        ↓
GET CapabilityStatement
        ↓
run Patient CRUD FHIR TestScript
        ↓
inspect raw HTTP
        ↓
see assertion/conformance states
        ↓
export complete evidence
```

### SHN

```text
select SHN TestSystem
        ↓
run connectivity
        ↓
acquire/test token
        ↓
load SHN FHIR TestScript
        ↓
execute
        ↓
inspect raw HTTP
        ↓
see assertions
        ↓
export complete evidence
```

### Architectural acceptance criterion

**No runner code changes are required to switch between IRIS and SHN.**

Only configuration, credentials, fixtures, and TestScript should change.

If that is true, the Workbench has successfully escaped the assumptions of the original SHN provider workflow.

---

## 24. Provenance / Harvest Sources

### MediLacra Connectivity

Harvest:

- DNS
- TCP
- TLS
- certificate inspection
- port probing
- arbitrary HTTP
- TLS verification/timeout controls
- optional MLLP adapter

Required change:

- move logic out of Streamlit into pure reusable Python.

### MediLacra SHN Provider / Reference Suite

Harvest:

- OAuth client credentials
- token lifecycle
- retries
- correlation/timing metadata
- safe credential boundary
- transport evidence
- expected-vs-observed result structure
- RunLogger
- artifact persistence
- single-run export
- collection export

Required change:

- remove CRD/DTR/PAS and SHN endpoint assumptions from core execution.

### PIQITT Connectathon / Official Reference Work

Harvest:

- external-standard-artifact adapter pattern
- explicit unsupported/unbound semantics
- deep FHIR path extraction
- FHIR `[x]` extraction
- resource selector primitives
- regression-diff pattern
- flattened human export pattern

Do not port into the core:

- old PIQI Streamlit interface
- hand-authored PIQI YAML profile architecture
- PIQI scoring model
- HL7 → FHIR conversion

Those remain optional adapters.

---

## 25. Initial Decision Log

| Decision | Rationale |
|---|---|
| Use standard FHIR TestScript JSON | Avoid another proprietary test schema |
| Preserve unsupported standard elements | Prevent silent semantic loss |
| Make TestSystem independent from TestScript | Enables the same test to run across endpoints |
| Use IRIS and SHN from the start | Forces generic architecture |
| Keep conformance minimal | Avoid rebuilding dedicated validator products |
| Default to raw HTTP output | Optimize for interoperability debugging rather than presentation |
| Keep files as persistence for MVP | No demonstrated need for a database |
| Reuse logging/evidence machinery | Already proven in live SHN testing |
| Reuse PIQITT primitives, not its UI/model | Harvest working functionality without inheriting older architecture |
| Defer TestScript extensions | Learn from real scripts before inventing local semantics |
| Stop after MVP and use it | Real interoperability friction should drive the next layer |


---

## 26. Implementation Status — 2026-10-15

The initial MVP has now been materialized in this repository.

### Implemented from the build plan

- Repository/package foundation and smoke CI.
- Pure connectivity primitives extracted from MediLacra:
  - DNS
  - TCP
  - TLS
  - certificate inspection
  - quick port probes
  - arbitrary HTTP
- `TestSystem` configuration model, including:
  - base URL
  - protocol/FHIR version
  - TLS verification
  - CA bundle
  - client certificate/key
  - USER_KEY/organization-key header slots
  - default headers
  - optional correlation/leg/trace metadata
  - configurable retry policy
- `CredentialProfile` with:
  - none
  - Basic
  - Bearer
  - OAuth2 client credentials
  - environment and local JSON-file value sources
- Generic `AuthManager` with in-memory OAuth tokens and safe lifecycle metadata.
- Generic `TransportClient` with:
  - raw request/response capture
  - TLS options
  - credential injection
  - configurable identity headers
  - optional correlation UUIDs
  - configurable retry observation
  - sensitive request/response header redaction
- FHIR TestScript loader that preserves the source JSON.
- Explicit unsupported-element inventory instead of silent omission.
- Local static fixtures plus responses materialized as later fixture sources.
- TestScript operation support for GET/POST/PUT/PATCH/DELETE.
- TestScript assertion states:
  - PASS
  - FAIL
  - SKIP
  - UNSUPPORTED
  - ERROR
- Initial assertions:
  - HTTP status / named response
  - Content-Type
  - response header
  - FHIR resourceType
  - JSONPath existence/value comparison
  - request method / request URL
  - response-code operators including `in` / `notIn`
  - request/response direction for supported assertion types
  - `validateProfileId` surfaced as UNSUPPORTED until actual StructureDefinition validation exists
- PIQITT-derived lightweight FHIR extraction for local adapters:
  - deep dotted paths
  - array fan-out with `*`
  - FHIR choice extraction with `[x]`
- TestScript `path` uses JSONPath; XPath is explicitly UNSUPPORTED rather than reinterpreted.
- Minimal `Validator` interface with:
  - `NoOpValidator`
  - `BasicFHIRValidator`
- Generic TestScript runner with run-all and run-through-step modes.
- Request/response ids and target-fixture URL resolution for common FHIR operations.
- Local TestScript import from the UI.
- Generic CLI runner and no-network evidence collection CLI.
- Generic append-only execution logger.
- Raw request/response/header operation evidence.
- Sanitized TestScript, TestSystem, and credential-source provenance snapshots per run.
- Header and credential-shaped JSON-body redaction at the persistence boundary while leaving the live in-memory request untouched.
- SHA-256 artifact inventory events.
- Single-run ZIP export.
- Multi-run transaction/event collection export.
- Baseline/current regression comparison.
- Thin Streamlit pages:
  1. Test Systems
  2. Connection Lab
  3. Auth Workbench
  4. TestScript Runner
  5. Evidence
- Built-in SHN provider TestSystem and connectivity TestScript.
- Local IRIS FHIR TestSystem using the recovered PIQITT FHIR base.
- IRIS CapabilityStatement TestScript.
- IRIS synthetic Patient CRUD TestScript + fixture.
- Whole-export regression testing for credential/identity-value leakage.

### IRIS endpoint materialized

The native IRIS FHIR base was recovered and verified live. The built-in local IRIS TestSystem is:

```text
http://localhost:52773/csp/healthshare/piqitt/fhir/r4
```

Port `52773` is plain HTTP in this deployment, and the namespace path is case-sensitive: `piqitt` must be lower-case.

Credential values remain environment/local-only. The TestSystem can still be overridden under `config/systems/local/` if the local deployment changes.

### Architectural state

The core runner contains no CRD/DTR/PAS branches and no IRIS-specific execution branches.

```text
TestSystem
   +
CredentialProfile
   +
FHIR TestScript
        ↓
generic runner
        ↓
generic transport
        ↓
assertions / minimal validation
        ↓
evidence
```

The IRIS side of the v0.1 acceptance path has now been exercised live end-to-end. Remaining acceptance work is the SHN side. Live use should continue to drive the next changes rather than speculative feature growth.

Notably, full TestScript variables, XPath, FHIRPath expressions, metadata capability enforcement, warning-only assertions, multi-origin/destination routing, and true `validateProfileId` conformance validation remain explicit UNSUPPORTED states rather than approximated behavior.


---

## 27. Live IRIS Acceptance Results — 2026-10-16

Detailed evidence and run IDs are recorded in:

`docs/TESTING_RESULTS_v0.1_2026-10-16.md`

### Connectivity

Verified against:

```text
http://localhost:52773/csp/healthshare/piqitt/fhir/r4
```

Observed:

- DNS: PASS — `localhost -> 127.0.0.1`
- TCP: PASS — port `52773`
- TLS: SKIP — endpoint is HTTP
- `GET /metadata`: HTTP 200
- FHIR version: `4.0.1`

### Authentication boundary

```text
anonymous GET /metadata      -> 200
Basic-auth GET /metadata     -> 200

anonymous Patient PUT        -> 401
anonymous Patient GET        -> 401
anonymous Patient DELETE     -> 401

Basic-auth Patient PUT       -> 201
Basic-auth Patient GET       -> 200
Basic-auth Patient DELETE    -> 204
```

### TestScript execution

`IRISCapabilityStatement` passed with both:

- `CredentialProfile = none`
- `CredentialProfile = iris-basic`

`IRISPatientCRUD` behaved as expected:

- no authentication: FAIL after IRIS returned HTTP 401 for PUT/GET/DELETE
- Basic authentication: PASS end-to-end
- returned Patient parsed successfully as FHIR JSON
- HTTP status, `resourceType`, and Patient id assertions passed
- teardown DELETE returned HTTP 204

### Evidence / credential hygiene

Live evidence confirmed:

- Authorization values persist only as `<redacted:Basic>`
- credential values are not persisted
- credential-source provenance is retained
- runtime credential selection is recorded separately from the TestSystem default
- raw request/response artifacts, transactions, assertions, validation results, and event ordering are sufficient to diagnose failures without reproducing the run

### Testing-driven fixes

Live IRIS testing directly produced these corrections:

1. local IRIS endpoint changed from HTTPS to HTTP
2. namespace corrected from `PIQITT` to case-sensitive `piqitt`
3. Connection Lab skips TLS for HTTP endpoints
4. Connection Lab shows effective endpoint and TLS-probe decision
5. stale local TestSystem override behavior was exposed and diagnosed
6. IRIS default credential profile changed to `none` because `/metadata` is public
7. TestScript Runner distinguishes executed HTTP operations from passing assertions
8. TestScript Runner explicitly flags HTTP 401 responses
9. operation errors are shown directly in the UI

### Acceptance status

The IRIS v0.1 acceptance path is complete.

SHN remains the next live acceptance target.
