# M-004 — Multi-Representation Eligibility Integration

**Target:** `natosit-dev/medilacra_fhir_engine`, branch `feat/m004-multiformat-eligibility`  
**Unified base:** `35b4b88c5c7e71da5965c5731c5efeac22673492`  
**Eligibility source:** `natosit-dev/medilacra` `experiment/employer-coverage`, pinned at `b7de24b32f548ecafdb8bba1a5dbaf1480435b23`  
**Build status:** Implemented on integration branch; CI and manual validation gates determine readiness.

## Scope

Adopt the employer-coverage additions as a source-level integration under `apps/mvp0`, preserving all existing unified SHN, DiScO, PIQI, Workbench and 47-file frozen Engine harvest components. Do **not** replace the entire MVP-0 subtree or overwrite the frozen `src` files.

Implemented:
- Independent synthetic payer membership, enrollment, benefits and identity matching.
- Semantic `EligibilityInquiry` and `EligibilityResponse` shared across representations.
- X12 HIPAA 5010 270/271 envelope generation, parsing, scaled control allocation.
- FHIR R4 4.0.1 `CoverageEligibilityRequest` and `CoverageEligibilityResponse` directly projected from the same semantic exchange, not converted from X12.
- Coverage-aware HL7 GT1/IN1/IN2 messages and HL7-to-FHIR coverage projection.
- Coverage/payer DuckDB extensions, generator controls, Generate & Persist, standalone X12 Eligibility page.
- Migrated source regressions and unified navigation/CI updates.

## Evidence gates

1. Original HL7-only generator output and offline SDOH behavior must not regress when new switches are off.
2. X12 and FHIR projections must agree on the same semantic eligibility exchange.
3. Payer evaluation must never use oracle-only clinical-to-payer identity links.
4. 1,000 exchange scale test must not collide in X12 control IDs.
5. DuckDB coverage/payer entities must remain queryable; `raw_hl7` must not store X12/FHIR artifacts.
6. Existing DiScO, SHN reference and Workbench tests must pass.
7. Streamlit unified navigation must expose all original 13 selected pages plus X12 Eligibility.
8. User acceptance: run generated HL7/X12/FHIR, both X12 scenario modes, and DiScO export in the unified interface.

## Out of scope

- Adding X12/FHIR corruption modes directly inside DiScO.
- Unifying MVP-0 and Workbench transport/evidence engines.
- Modifying frozen Engine source blob hashes.
- X12 278, 837, 835 or comprehensive HIPAA implementation guide certification.
- Live SHN re-execution without environment credentials.
- Full PIQI external endpoint submission.

## Architectural safeguard

`apps/mvp0` code takes import precedence in the existing `unified/legacy.py` launcher; `src` remains a byte-preserved source harvest. This first integration intentionally preserves the distinction.

## Validation record

See the branch's GitHub Actions workflow. Successful source-branch CI is historical evidence, **not** evidence that the integrated branch passed. Manual UI acceptance remains separately required.
