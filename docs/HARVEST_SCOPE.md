# Initial harvest scope

## Provenance
- Source: `natosit-dev/medilacra`
- Frozen B-001 revision: `2202e0b5503b60eaffba5e6ff0341df143a58008`
- Existing original modules and JSON copied without intentional edits under `src/`
- Source Git blob SHA for each file recorded in `docs/harvest-manifest.json`.
- All 47 harvested Git blob identities were checked against the source manifest, and the 5-test offline suite passed locally and in GitHub Actions. SHA-256-based payload comparisons and independent behavioral parity against B-001 are **still pending**.

## Included
- Deterministic synthetic patient, encounter and transaction models
- CRD, DTR, PAS and inquiry reference request builders and response summaries
- Scenario definitions, reference TP/TN cases and seed-driven cohort construction
- Negative test mutations, QuestionnaireResponse materialization, existing local file-writing helpers retained for source-compatibility

## Deliberately excluded
- Network-facing SHN client, OAuth, transport/retry layer, shell senders
- `ReferenceSuiteRunner`, `ProviderWorkflow`, evidence collection/export and live run CLI
- Live credentials, token files, local result artifacts, and unrelated Medilacra subsystems
- Original `connectathon/shn_provider/__init__.py` (eagerly imports network workflow); a minimal import-safe shim replaces it

## Completed verification
- 47/47 source files retain original Git blob identities.
- Offline smoke/integrity tests: 5 passed on 2026-10-21 locally (0.16 s) and in GitHub Actions run `39591150740`.

## Pending
1. Compare seeded output behavior and pinned fixture outputs against original `2202e0b`.
2. Establish parity baseline E-001 using redacted B-001 evidence, independent of network.
3. Define stable, public Engine API without changing legacy behavior.
4. Have Workbench and MVP-0 consume a pinned Engine release rather than duplicate code.
5. Version expected results separately from scenarios and bind expectations to source contracts in Workbench.
6. Decide whether generation, demonstration and inspection use one consolidated application surface. See `MILESTONES_AND_APP_TOPOLOGY_2026-10-21.md`.
