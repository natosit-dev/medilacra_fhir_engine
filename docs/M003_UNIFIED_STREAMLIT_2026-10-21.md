# M-003 — Unified Streamlit front door (integration candidate)

**Date:** 2026-10-21
**Branch:** feat/unified-medilacra
**Status:** Navigation wired; user-driven application acceptance is **PENDING**

**Later acceptance update (2026-10-23):** The initial PENDING status below is historical. Local unified interface and evidence flow were manually accepted for Medilacra v1 with [disclosed deferrals](RELEASE_ACCEPTANCE_2026-10-23.md), chiefly PIQI converter unavailability. Deeper Engine code deduplication/parity is not claimed.

## Objective

Run both functioning applications from one root Streamlit entry point before any domain/transport refactor. Preserve the full synthetic-clinical and operational-capability perspectives. The UI remains intentionally thin.

## Existing code imported intact

The subtree imports are already present at:

- \`apps/mvp0/\` — frozen Medilacra revision \`2202e0b5503b60eaffba5e6ff0341df143a58008\`, including the original \`medi_lacra_app.py\`, 11 Streamlit pages, provider ePA, PIQI and bulk utilities.
- \`apps/workbench/\` — original Workbench, including five Streamlit pages for Test Systems, Connection Lab, Authentication, TestScript Runner and Evidence.
- \`src/\` — M-001 harvested FHIR Engine package.

This milestone adds \`app.py\`, \`unified/page_catalog.py\`, and \`unified/legacy.py\`. No existing MVP-0 or Workbench page is edited.

## Start locally

From the repository root, with your existing \`dev310\` environment active:

\`\`\`bash
cd ~/code/medilacra_fhir_engine
git pull --ff-only
python -m pip install -r requirements-unified.txt
python -m streamlit run app.py
\`\`\`

Run tests independently (the whole MVP-0 historical suite has separate dependencies):

\`\`\`bash
python -m pytest -q tests
(cd apps/workbench && python -m pytest -q tests)
(cd apps/mvp0 && python -m connectathon.shn_provider.reference_run --help)
\`\`\`

## Expected application navigation

1. **Clinical Reality:** HL7 Generator, Generate & Persist, Message Configuration, Site & Scenario Setup.
2. **Operational Reality:** Workbench Test Systems, Connection Lab, Auth, TestScript Runner; MVP-0 Connectivity and IRIS SQL Viewer.
3. **Workflows & Experiments:** SHN Provider ePA, PIQI Connectathon 43, DiScO Inferno.
4. **Inspection & Tools:** Workbench Evidence, MVP-0 Admin, Note Coder, AI Admin.

Total: **17 existing Streamlit entry points** (original Medilacra main app plus 11 MVP-0 page files and 5 Workbench page files), plus a new Home page.

## Preserving behavior

Each original page is executed with its application directory as the current working directory. Both application roots are placed ahead of the M-001 \`src/\` harvest on the Python import path so the original fully implemented MVP-0 modules take precedence during the first integration. Relative paths inside Workbench (e.g. \`config/\`, \`testscripts/\`, \`results/\`) and MVP-0 (e.g. \`data/\`, \`input/\`, \`connectathon/\`) therefore resolve as they did when each app launched separately.

The original implementations remain independent under one UI. In particular, **this does not yet implement one shared engine or cross-app case identity**. Capability mappings and single-run configuration snapshots remain future milestones.

## Important limitations to validate

- **Single-user local compatibility only.** \`os.chdir\` changes the process working directory, and Python \`sys.modules\` is shared. Concurrent sessions/background work are not isolated. Do not deploy this launcher for shared multiuser production use.
- Some historical pages require optional services, DSNs, credentials, reference datasets, environment settings or models. The navigation can surface them without those services being configured. Missing prerequisites must be reported per page; do not count menu presence as functional acceptance.
- \`SHN_CLIENT_FILE\` should point to the **existing local ignored** credentials. Do not copy or commit secrets into the new repository. The original Workbench's profile may reference relative local secret paths; preserve them under \`apps/workbench/\` or adjust private local references.
- FHIR Engine's current harvested modules and MVP-0's original modules intentionally overlap. MVP-0 wins for integrated UI behavior until source parity and ownership are settled.
- The repositories have different GPL license versions. **Resolve compatibility before distribution**; no general release is implied.
- Some cross-application Streamlit pages may need import/dependency corrections once tested in the unified process. Those repairs should remain minimal and evidence-backed.

## Acceptance (NOT yet verified through a browser)

- [ ] Home and all 17 original pages load without unexpected import/path errors.
- [ ] Clinical: generate and inspect synthetic HL7 results, persist to DuckDB if configured.
- [ ] Operational: configure TestSystem, obtain auth using existing private profile, run and inspect a generic TestScript.
- [ ] Workflows: create a synthetic case and run the existing offline ePA builder; run TP-01 live against hosted SHN only with explicit local credentials and user intent.
- [ ] Evidence: inspect/export the run without exposing credentials.
- [ ] Launch and rerun across pages without losing the ability to use either original app.
- [ ] Record broken features, setup prerequisites and fixes before calling M-003 complete.

## Post-acceptance navigation reduction (2026-10-22)

After the user's first browser acceptance pass, four unused or obsolete
pages were removed from both navigation **and the unified repository source**:

- `apps/mvp0/pages/4_IRIS SQL Viewer.py` (obsolete ODBC interface)
- `apps/mvp0/pages/0_medi_lacra_admin.py` (redundant administrative page)
- `apps/mvp0/pages/6_Note_Coder.py` (broken/unneeded)
- `apps/mvp0/pages/7_AI Admin.py` (unneeded)

Current UI: **13 original application views plus Home**. This reduction does not
delete any shared package, test implementation or generated clinical data.
The historic upstream MVP-0 repository remains unchanged; Git history
preserves these files. Run `python -m pytest -q tests` after pulling.

**Next:** after acceptance, introduce a shared clinical/operational case workspace and gradually consolidate duplicate domain and execution code.
