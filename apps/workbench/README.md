# MediLacra SHN Workbench

Small interoperability test bench built from proven MediLacra and PIQITT primitives.

The workbench keeps **TestSystem configuration**, **CredentialProfile configuration**, and **FHIR TestScript JSON** separate so the same runner can be used against different endpoints.

## Current MVP

- configurable TestSystems
- USER_KEY / organization-key header slots
- TLS verification, CA bundle, and client certificate configuration
- DNS / TCP / TLS / certificate / port probes
- raw arbitrary HTTP testing
- None / Basic / Bearer / OAuth2 client-credentials auth
- safe token lifecycle handling
- generic HTTP transport with optional correlation/trace headers
- FHIR TestScript JSON loader
- local fixtures and response fixtures
- GET / POST / PUT / PATCH / DELETE operations
- PASS / FAIL / SKIP / UNSUPPORTED / ERROR assertion states
- HTTP, header, resourceType, JSONPath/value, content-type, request-method, and request-URL assertions
- PIQITT-derived deep-path and `[x]` extraction primitives for local FHIR adapters
- explicit UNSUPPORTED handling for XPath/FHIRPath, real profile validation, capability preconditions, and other unimplemented TestScript semantics
- minimal FHIR response validation
- run-all and run-through-step execution
- chronological execution logging
- sanitized TestScript/TestSystem/credential-source provenance snapshots
- raw request/response evidence with credential-shaped JSON values redacted from persisted artifacts
- single-run and multi-run ZIP exports
- baseline/current regression comparison

## Built-in systems

### SHN Provider Test

`config/systems/shn-provider-test.json`

The OAuth client profile reads a gitignored local file:

```text
config/credentials/local/secrets/shn-client.json
```

### Local IRIS FHIR

`config/systems/iris-fhir-local.json`

The built-in local FHIR base is:

```text
http://localhost:52773/csp/healthshare/piqitt/fhir/r4
```

This local IRIS deployment is plain HTTP on port `52773`, and the namespace
path is case-sensitive: `piqitt` must be lower-case.

Credentials remain local:

```bash
export IRIS_FHIR_USER='...'
export IRIS_FHIR_PASSWORD='...'
```

If the local IRIS deployment changes, override the TestSystem under
`config/systems/local/`. The repo includes IRIS CapabilityStatement and
synthetic Patient CRUD TestScripts.

Live IRIS acceptance testing is complete for the current v0.1 path:

- anonymous `GET /metadata` → HTTP 200
- Basic-auth `GET /metadata` → HTTP 200
- anonymous Patient PUT/GET/DELETE → HTTP 401
- Basic-auth Patient CRUD → PUT 201, GET 200, DELETE 204, assertions PASS

See `docs/TESTING_RESULTS_v0.1_2026-10-16.md` for run IDs, evidence findings,
and implementation fixes driven by testing.

## Run

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

Pages:

1. **Test Systems**
2. **Connection Lab**
3. **Auth Workbench**
4. **FHIR TestScript Runner**
5. **Evidence**

Command-line execution uses the same runner:

```bash
python -m toolbench.run \
  --system shn-provider-test \
  --credential none \
  --testscript testscripts/shn/provider-connectivity.json
```

Run through one action and its prerequisites:

```bash
python -m toolbench.run \
  --system iris-fhir-local \
  --testscript testscripts/iris/patient-crud.json \
  --through get-patient
```

Bundle all recorded evidence without sending network traffic:

```bash
python -m toolbench.collect
```

## Deliberately not migrated

The workbench does **not** carry the full MediLacra application:

- synthetic-data generation stack
- DuckDB / analytics
- SDOH integrations
- HL7 message builders
- SHN-specific CRD/DTR/PAS workflow orchestration
- PIQI scoring UI/model

Those remain separate and can be attached later as narrow adapters if a real test requires them.

The build contract and decision log are in:

`docs/MEDILACRA_SHN_WORKBENCH_BUILD_PLAN_v0.1_2026-10-15.md`


## Unified Medilacra v1 release boundary

This Workbench is included inside the unified Medilacra Streamlit application; the root [release acceptance record](../../docs/RELEASE_ACCEPTANCE_2026-10-23.md) supersedes v0.1 standalone acceptance for the combined release. Licensing of Workbench code contributed and controlled by the Medilacra project has been aligned to GPL version 2 in this integrated repository. Existing dependency licenses and third-party notices are not overwritten by this change.
