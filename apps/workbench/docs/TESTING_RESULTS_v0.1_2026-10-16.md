# MediLacra SHN Workbench — Testing Results

**Version:** 0.1  
**Date:** 2026-10-16  
**Scope:** Live IRIS acceptance testing for the Workbench MVP  
**Status:** IRIS acceptance path passed; SHN acceptance pending

---

## 1. Test Environment

Workbench:

- repository: `natosit-dev/medilacra_shn_workbench`
- execution environment: WSL/Linux
- Python environment: conda `dev310`
- UI: Streamlit

Local FHIR server:

- product: InterSystems IRIS for Health
- FHIR version: `4.0.1`
- endpoint:

```text
http://localhost:52773/csp/healthshare/piqitt/fhir/r4
```

Important deployment details discovered during live testing:

- port `52773` serves plain HTTP, not HTTPS
- the namespace path is case-sensitive
- `piqitt` must be lower-case

---

## 2. Connection Lab

### Observed connectivity

```text
DNS   PASS   localhost -> 127.0.0.1
TCP   PASS   localhost:52773
TLS   SKIP   endpoint scheme is HTTP
```

Direct Workbench HTTP request:

```text
GET /metadata
HTTP 200 OK
Content-Type: application/fhir+json; charset=UTF-8
```

The response was a FHIR `CapabilityStatement` reporting:

- `fhirVersion = 4.0.1`
- server implementation: InterSystems FHIR Server
- JSON and XML formats

### Testing-driven corrections

The first live runs exposed configuration rather than transport defects:

1. the original endpoint was incorrectly configured as HTTPS
2. the namespace was initially configured as upper-case `PIQITT`
3. a stale local TestSystem override continued to force HTTPS after the built-in config was corrected

The Connection Lab was updated to:

- skip TLS probing when the effective endpoint uses HTTP
- display the effective endpoint
- display the parsed scheme
- display whether a TLS probe will run

This made configuration precedence visible instead of presenting a misleading SSL failure.

---

## 3. CapabilityStatement TestScript

TestScript:

```text
IRISCapabilityStatement
```

### 3.1 Anonymous run

Run ID:

```text
iriscapabilitystatement-iris-fhir-local-20261015T172321Z-247dd0e2
```

Credential profile:

```text
none
```

Result:

```text
PASS
duration: 233.1 ms

GET /metadata                    200
assert HTTP 200                  PASS
assert CapabilityStatement       PASS
```

Conclusion:

`GET /metadata` is available without authentication.

### 3.2 Basic-auth run

Run ID:

```text
iriscapabilitystatement-iris-fhir-local-20261016T123813Z-46324738
```

Credential profile:

```text
iris-basic
```

Result:

```text
PASS
duration: 150.6 ms

GET /metadata                    200
assert HTTP 200                  PASS
assert CapabilityStatement       PASS
```

The request evidence records:

```text
Authorization: <redacted:Basic>
```

Conclusion:

Basic authentication is injected successfully while credential values remain outside persisted evidence.

---

## 4. Patient CRUD TestScript

TestScript:

```text
IRISPatientCRUD
```

Synthetic resource id:

```text
Patient/medilacra-workbench-patient
```

### 4.1 Anonymous run

Run ID:

```text
irispatientcrud-iris-fhir-local-20261015T172513Z-dacb37b5
```

Credential profile:

```text
none
```

Result:

```text
FAIL
duration: 89.8 ms
```

Observed IRIS responses:

```text
PUT    /Patient/medilacra-workbench-patient    401
GET    /Patient/medilacra-workbench-patient    401
DELETE /Patient/medilacra-workbench-patient    401
```

Assertions correctly failed because the GET did not produce a Patient:

```text
HTTP 200 expected       observed 401       FAIL
Patient expected        observed null      FAIL
Patient id expected     observed []        FAIL
```

Interpretation:

The Workbench reached IRIS successfully. The failure describes the server's access boundary: Patient resource interactions require authentication.

The runner UI was subsequently adjusted so successfully executed HTTP operations are shown as `EXECUTED` rather than implying that HTTP 401 is a successful test assertion.

### 4.2 Basic-auth run

Run ID:

```text
irispatientcrud-iris-fhir-local-20261016T124409Z-2ff49015
```

Credential profile:

```text
iris-basic
```

Result:

```text
PASS
duration: 543.7 ms
```

Observed operations:

| Operation | HTTP | Observed |
|---|---:|---|
| PUT synthetic Patient | 201 | Created |
| GET synthetic Patient | 200 | FHIR Patient returned |
| DELETE synthetic Patient | 204 | No Content |

Assertions:

| Assertion | Result |
|---|---|
| GET status = 200 | PASS |
| resourceType = Patient | PASS |
| id = medilacra-workbench-patient | PASS |

FHIR validation:

- PUT response: SKIP — empty/non-FHIR response body
- GET response: PASS — parsed as FHIR `Patient`
- DELETE response: SKIP — empty response body

The PUT response included a FHIR history location ending in:

```text
Patient/medilacra-workbench-patient/_history/1
```

The GET returned the same Patient id with `meta.versionId = 1`.

---

## 5. Authentication Boundary Established

Live testing established the following behavior:

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

The built-in IRIS TestSystem therefore defaults to `CredentialProfile = none` for public metadata testing, while `iris-basic` is selected explicitly for authenticated resource operations.

---

## 6. Evidence and Credential Hygiene

The exported run evidence proved the persistence boundary works as intended.

Persisted request headers contain:

```text
Authorization: <redacted:Basic>
```

Persisted credential metadata identifies sources rather than values.

The evidence bundle contains:

- sanitized TestSystem snapshot
- sanitized CredentialProfile/source snapshot
- TestScript snapshot
- chronological event log
- transaction log
- request headers
- request body
- response headers
- response body
- assertion results
- validation results
- artifact hashes

The evidence from the anonymous CRUD failure was sufficient to identify the 401 boundary without reproducing the run.

---

## 7. Architectural Result

The IRIS acceptance path now works end-to-end:

```text
TestSystem
   +
CredentialProfile
   +
FHIR TestScript
        ↓
generic runner
        ↓
HTTP/FHIR exchange
        ↓
assertions + minimal validation
        ↓
raw evidence + export
```

This has been proven for both:

- anonymous FHIR metadata access
- authenticated FHIR resource CRUD

No IRIS-specific execution branch was added to the generic runner to make the live tests pass.

---

## 8. Implementation Changes Driven by Testing

| Finding | Change |
|---|---|
| Port 52773 is HTTP, not HTTPS | Corrected IRIS TestSystem scheme |
| Namespace path is case-sensitive | Corrected `PIQITT` to `piqitt` |
| TLS probe produced false failure for HTTP | Connection Lab skips TLS for HTTP |
| Stale local override obscured effective config | Connection Lab displays effective endpoint/scheme/TLS decision |
| `/metadata` is public | IRIS default credential profile changed to `none` |
| Patient interactions return 401 anonymously | Runner now calls out 401 explicitly |
| Operation PASS was semantically confusing | UI displays successful transport execution as `EXECUTED` |
| Operation failures were hard to inspect | Underlying operation error is displayed directly |

---

## 9. Acceptance Status

### IRIS

**PASS for the planned v0.1 path.**

Completed:

- connectivity
- public metadata
- Basic authentication
- CapabilityStatement TestScript
- authenticated Patient CRUD
- assertions
- minimal FHIR parsing/validation
- teardown
- evidence export
- credential redaction

### SHN

**Pending live Workbench acceptance.**

The next acceptance target is the SHN TestSystem using the same generic runner.
