# Baseline B-001 — SHN Reference TP-01

**Recorded:** 2026-10-20  
**Status:** Reference workflow passed; **not** an integrated Workbench platform baseline  
**Scope:** Synthetic provider-facing CRD / DTR / PAS round trip through the hosted SHN Provider Test Endpoint, route `00301` (Da Vinci 2.2 line).  
**Evidence source:** User-run CLI output and test artifact manifest, recorded 2026-10-20. The original evidence files and ZIP reside in the user's local MVP-0 worktree; this document records their reported paths and hashes, but does not embed or independently revalidate their bytes.

## 1. Why this baseline exists

This record freezes the first observed end-to-end SHN reference workflow before consolidation of the Medilacra SHN Workbench and the earlier Medilacra MVP-0 execution code.

**B-001 is a reference behavior/evidence baseline, not the final architecture.** The intended *integrated baseline* will run TP-01 from one repository using shared configuration, transport, authentication, assertions, and evidence, with an environment-wide sanitized configuration snapshot.

The test proves that the existing MVP-0 client received responses matching its configured TP-01 expectations from the hosted synthetic test endpoint on this date. It does **not** by itself prove independent observation at every internal SHN Gateway/Hub hop, FHIR IG certification, payer production behavior, or go-live readiness.

## 2. Software and worktree provenance

| Role | Location (local) | Revision / state at testing |
|---|---|---|
| Intended platform home | `~/code/medilacra_shn_workbench` | `main`, clean; `d7b591d` — `docs: mark IRIS acceptance path complete` |
| Proven ePA reference implementation | `~/code/medilacra_shn_mvp0` | Detached worktree at `2202e0b5503b60eaffba5e6ff0341df143a58008`; `feat: log token expiry and transport retry metadata` |
| Original Medilacra development checkout | `~/code/medilacra` | `yakkity-ack`; preexisting modified/untracked files deliberately left untouched |

The isolated MVP-0 worktree was created from `experiment/shn-mvp0`. The runner and case definition in that revision:

- `connectathon/shn_provider/reference_run.py`
- `connectathon/shn_provider/reference_suite.py`
- `connectathon/shn_test_cases/tp01_00301_round_trip.json`
- `connectathon/shn_provider/reference_payloads.py`

Execution environment reported by the manifest: Linux / WSL2 (`6.18.33.2-microsoft-standard-WSL2`), CPython 3.10.21, CLI mode. Source repository: [Medilacra MVP-0 branch](https://github.com/natosit-dev/medilacra/tree/experiment/shn-mvp0). The recorded execution commit, rather than a mutable branch pointer, is authoritative for reproduction.

## 3. Preflight: Workbench already operating

**OAuth (Auth Workbench):** `shn-provider-client-secret` reported `active=true`, token HTTP `200`, scope `system/Davinci.write`, no error. This establishes token acquisition, *not* by itself authorization of a protected CRD request.

**Discovery (generic Workbench TestScript):**

- TestSystem: `shn-provider-test`
- Credential selection: `none` (public discovery)
- TestScript: `testscripts/shn/provider-connectivity.json`
- Result: `PASS` in 329.5 ms
- `GET /cds-services` returned HTTP 200; HTTP-status and `services`-array assertions passed
- Run: `shnproviderconnectivity-shn-provider-test-20261020T150734Z-21fff59d`
- Evidence: `~/code/medilacra_shn_workbench/results/shnproviderconnectivity-shn-provider-test-20261020T150734Z-21fff59d/`

The discovery TestScript does not yet assert the exact advertised SHN service IDs.

### Configuration-loader finding

Auth Workbench initially raised `KeyError: 'id'` because `list_profiles()` attempted to load a secret-value JSON file as a CredentialProfile definition. No source code was changed. Working local layout:

- CredentialProfile override: `config/credentials/local/shn-provider-client-secret.json`
- Secret source (ignored by Git): `config/credentials/local/secrets/shn-client.json`

The profile points to the nested secret path, which the nonrecursive profile enumerator does not scan. **Underlying discovery/type-validation defect remains unresolved.** Do not commit secret values, token bodies, or private keys.

## 4. TP-01 specification and execution

**Case:** TP-01 — Full round trip on payer route `00301`  
**Synthetic member:** `MBR-COVERED`  
**HCPCS:** `G0151`  
**Declared source in the checked-in case:** SHN Connectathon Test Process staff draft and SHN Provider Test Endpoint guide, provenance date 2026-10-12. The participant process was issued 2026-10-13 for the 2026-10-14 Connectathon.  
**Expected-results authority:** Reference case definition as checked into MVP-0 commit `2202e0b`. These are locally configured expectations, not independently established normative IG certification criteria.

Command run in the isolated MVP-0 worktree:

```bash
cd ~/code/medilacra_shn_mvp0
export SHN_CLIENT_FILE="$HOME/code/medilacra_shn_workbench/config/credentials/local/secrets/shn-client.json"
python -m connectathon.shn_provider.reference_run TP-01 --export
```

**Run ID:** `tp01-20261020T151118Z-5af171fe`  
**UTC start:** `2026-10-20T15:11:18.310856+00:00`  
**UTC completion:** `2026-10-20T15:11:29.267579+00:00`  
**Duration:** 10,956.7 ms  
**Result:** `passed=true`; five of five configured operation checks passed  
**Run events:** 82  
**Retries:** zero reported (each operation had `attempts=1`)

| Operation | HTTP | Configured expectation and observation | Result |
|---|---:|---|---|
| 1. CRD | 200 | `doc-needed=clinical`, questionnaire present; `pa-needed=auth-needed`, `covered=conditional`, one system action | PASS |
| 2. DTR | 200 | HomeHealthAssessment questionnaire package present; 1 Questionnaire, 3 Libraries, 1 QuestionnaireResponse, 1 ValueSet; payer demographic prepopulation warning | PASS |
| 3. PAS submit | 200 | `ClaimResponse.outcome=complete`; review-action code `A4` / display `Pending`; one `CommunicationRequest` with `102089-0` | PASS |
| 4. DTR relaunch | 200 | HomeHealthAssessment package returned after trace-based relaunch; same prepopulation warning | PASS |
| 5. PAS inquiry | 200 | One `responseBundle` and one decision: `A4` / `Pending`; `inquiry_response_count >= 1` | PASS |

**Interpretation cautions:** `ClaimResponse.outcome=complete` is a processing result; it is **not** a granted authorization. The actual recorded business review action was **pending**. DTR returned a package despite missing payer-side member matching for demographic prepopulation. A 200 response by itself would not establish IG conformance.

### Observed correlation / leg identifiers

| Operation | X-Correlation-Id | X-SHN-Leg-Id |
|---|---|---|
| CRD | `fbbc98d2-a304-4230-97ea-47cd29e7a297` | `0905c0b7a413a1755d1f5a68c9c2039d` |
| DTR | `7e0684f4-7a34-4902-8dd6-de09da57b13e` | `c3d03a5012df641bb9da0e1ae6ae1132` |
| PAS submit | `f02d47ed-1eec-4a7b-af86-78cf5e18db27` | `60a9f977840104e403de190e42a49453` |
| DTR relaunch | `b216ab80-c30e-436f-b5ad-1b2cb5d6ab38` | `5dc7a4c9eff1f7988597d710d9864384` |
| PAS inquiry | `689695fc-007c-4b78-8537-ad35eb0d5e5a` | `4952b38a6abf2b0de03c45109fb9d87e` |

### Verified response-dependent handoff

A separate **read-only local artifact check** extracted the `CommunicationRequest.identifier[0].value` from the PAS response and the `context.valueString` from the DTR relaunch request:

```text
PAS trace: AUTH-TRN0001
DTR trace: AUTH-TRN0001
MATCH
```

This establishes equality between these two captured payload values. It does not independently prove the payer's internal trace resolution or that the trace identifier is globally unique.

## 5. Local evidence location and integrity anchors

The exported results remain outside Git:

```text
~/code/medilacra_shn_mvp0/
  connectathon/results/shn_reference_suite/
    tp01-20261020T151118Z-5af171fe/
      operations/
        01-crd/
        02-dtr/
        03-pas-submit/
        04-dtr-relaunch/
        05-pas-inquire/
      export/
        medilacra-test-log-tp01-20261020T151118Z-5af171fe.zip
```

Each operation has `request.json`, `response.json`, `summary.json`, and `transport.json`. The reported manifest indexes these artifacts with SHA-256 hashes and lengths. Representative **response.json** SHA-256 values from that manifest:

| Operation | SHA-256 of `response.json` |
|---|---|
| 01-crd | `fdcc727968962f1d4fc26e5ced348e622cadc24a9dd961a308f2f862590d3edb` |
| 02-dtr | `31cefc6521f81f7bf884a8c91181aea64aafb386faad91db9ade8dffdda1faa2` |
| 03-pas-submit | `84667f8fb62caca4a98ae99c15bd832b0ee81bcce38f1f14cfb3fea5893115bf` |
| 04-dtr-relaunch | `0c4b7a11928095e02cc9fd5c0b7d47693d253c2ef5cdf6465aecf05ed7f049ba` |
| 05-pas-inquire | `980fe005926a4ebbd893a2c63202a6836ed6dcd3cb52a2720baf0c95f23fecda` |

These hashes are **reported by the local runner manifest**, not recomputed from files by the author of this document. Neither raw patient/payer payloads nor the ZIP are committed here; do not treat this Markdown file as a substitute for preserving the local export.

## 6. Exactly what has and has not been established

**Established by the reported execution:** public SHN service discovery; OAuth token acquisition; the reference runner's five CRD/DTR/PAS operations each returned HTTP 200 and matched their locally configured assertions; response-dependent PAS→DTR trace handoff; one pending result returned by inquiry; locally recorded evidence files and a ZIP export.

**Not independently established:** SHN's complete internal Gateway/Hub hop sequence, payload invariance at each boundary, conformance to the Da Vinci implementation guides, external payer production behavior, end-user UAT, operational acceptance, January go-live status, or provider attribution beyond a minimal synthetic requester. This run used the hosted synthetic reference endpoint, not a controlled provider/payer IRIS pair.

## 7. Decisions and next baseline

1. **Repository consolidation is the goal.** B-001 is a temporary cross-repository reference point; the **true integrated platform baseline remains pending** until TP-01 runs from one repository with one consolidated execution/evidence path.
2. **Preserve the existing working code, do not recreate TP-01.** Evaluate harvesting the MVP-0 response-driven workflow and builders into the Workbench while keeping generic HTTP/auth/config/evidence mechanics single-implemented.
3. **Configs are data.** Keep TestSystem, credential references, scenario, expected results, source provenance, and validator selection outside hard-coded SHN execution logic. Preserve FHIR TestScript as the standard test artifact; workflow coordination can remain a distinct concept.
4. **Snapshot Environment** is planned, not implemented: a single immutable sanitized snapshot of *effective* configuration, resolved overrides, expectation-source revisions, software commit(s), and validator settings, with no credential values.
5. **Local first.** No AWS prerequisite. Dockerized local IRIS/provider/payer paths can be brought in when needed; the initial hosted-endpoint reference run required neither.
6. **Minimal identity for V1.** One synthetic requester/provider and one payer route; sophisticated attribution and multi-practice isolation deferred.
7. **Preserve conflicting expectations.** The October Connectathon participant instructions and the technical Provider Endpoint guide disagree on several errors and correlation rules. Do not silently overwrite either; attach version/source and assess against an explicitly selected contract.

### Proposed integrated baseline acceptance

The next baseline should demonstrate TP-01 initiated in Workbench using a data-configured workflow adapter; all five responses observed and evaluated with equivalent or stronger assertions; evidence exported from Workbench; a single effective-config snapshot linked to the run; and comparison against B-001. No duplicate transport/auth implementations, hardcoded secret material, or wholesale uncontrolled branch merge.

**No integration work or Git merge is part of B-001.** The purpose of this document is to preserve the result before that design discussion.
