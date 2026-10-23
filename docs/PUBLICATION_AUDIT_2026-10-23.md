# Medilacra v1 — Publication Audit / Pre-public Checklist (2026-10-23)

**Status: NOT CLEARED FOR PUBLIC REPOSITORY VISIBILITY.** This is distinct from the functional release acceptance, which passed. Do not switch the existing private GitHub repository to public solely on the strength of current-tree secret-file ignores.

## Specific findings from the private candidate

1. **Tracked staging artifacts:** `apps/mvp0/.tmp.driveupload/` contains **299 tracked files**, **5,027,654 bytes** total as of feature commit `f8eeeda`, including three particularly large entries: `2573` (2,469,689 bytes), `417` (1,722,914 bytes), `741` (155,301 bytes). The function/content and distribution rights of these files have not been established. Some could not be decoded as UTF-8 through the connector. They must be inspected privately rather than assumed harmless.
2. **Terminology redistribution:** `apps/mvp0/ref/cpt_labels.csv` contains billing-code descriptions. Confirm source and license. CPT terminology/descriptors can carry third-party restrictions even if code is GPLv2. `apps/mvp0/ref/icd_labels.csv` likewise merits attribution/source verification.
3. **Exported HL7 schema:** `apps/mvp0/schemas/HL7v25_from_IRIS.xml` identifies an InterSystems IRIS export. Confirm that publishing the extracted schema is permitted under applicable source licenses and the HL7 standards license.
4. **Code/license provenance:** project root `LICENSE` and nested Workbench `LICENSE` are GNU GPL v2; determine whether every included imported source module is project-owned or otherwise GPLv2-compatible. The Python dependencies retain separate licenses.
5. **Git history:** making the **existing repository** public exposes reachable historical commits/blobs, including content removed in later commits. Merely deleting files or adding `.gitignore` does **not** purge history.
6. **Default branch:** `main` remains an earlier library-only state (`08f326c` at audit); the accepted unified app is on `feat/unified-medilacra`. Merge the reviewed code or select the appropriate default branch before announcing the release.
7. **Secrets:** current candidate has no tracked `apps/workbench/config/credentials/local/secrets/shn-client.json`; `apps/workbench/.gitignore` excludes `config/credentials/local/`. This checks that local credential location, **not all repository history**.

## Local examination before changing visibility

Run in a fresh local checkout or verified worktree. **Do not paste potentially sensitive file contents into public issues or chat.**

```bash
cd ~/code/medilacra_v1_verify

# Identify staged files without printing content:
git ls-files 'apps/mvp0/.tmp.driveupload/*' | wc -l
du -sh apps/mvp0/.tmp.driveupload
file apps/mvp0/.tmp.driveupload/{2573,417,741}

# Review exact tracked paths and history that public readers will receive:
git log --all --oneline -- apps/mvp0/.tmp.driveupload
git ls-files apps/mvp0/ref apps/mvp0/schemas

# Check only whether the local SHN client JSON is ignored/tracked:
git check-ignore -v apps/workbench/config/credentials/local/secrets/shn-client.json
git ls-files -- apps/workbench/config/credentials/local/secrets/shn-client.json
```

A secrets scanner run against **all reachable Git history** is also recommended; review findings privately. Inspection must cover the whole tracked staging directory, not just the three largest files.

## Decisions needed before public publication

- [ ] Classify staging artifacts; remove and, if necessary, rewrite private history **before** public visibility. If original history must be preserved privately, publish a separately curated clean-root repository or carefully managed public snapshot instead.
- [ ] Confirm redistribution/attribution rights for CPT labels, other term sets and exported IRIS/HL7 schema.
- [ ] Verify GPLv2 applicability for imported source and licensing notices.
- [ ] Review all historical commits for secrets/PHI/private test material.
- [ ] Bring accepted app to public default branch and run CI on release commit.
- [ ] Create a release tag and release notes only **after** the audit clears.

**Do not confuse local v1 functional acceptance with permission to publish every tracked historical file.**
