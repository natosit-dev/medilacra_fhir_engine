# SHN v1 — Client JSON setup

**Internal pilot/release candidate: 2026-10-23.** This guide describes SHN
provider-test OAuth client credentials for the unified Medilacra application.

## One client file for both testing paths

The file must be stored **on the machine running Streamlit**, not in the browser.
Do not upload its contents to the application or put it in the Git repository.
Use the SHN-issued client JSON with at least the following keys:

```json
{
  "client_id": "<your issued client ID>",
  "client_secret": "<your issued client secret>"
}
```

Replace the placeholders only in your private local JSON file.

### Option A — Enter the server-side path in the UI

1. Launch from the unified repository: `python -m streamlit run app.py`.
2. Select **Operational Reality → Authentication**.
3. Enter the **absolute path** of the existing private JSON file in **SHN client JSON file path**.
4. The page confirms **both required keys exist**. This is **not** an OAuth login test.
5. Select **SHN Provider Test Endpoint** and **SHN Provider Test — client_secret**.
6. Click **Acquire/Prepare Credentials**. A successful OAuth token response will show as an active authentication state without displaying a token.
7. Navigate to **Workflows & Experiments → SHN Provider ePA**. It uses the same file for this Streamlit browser session.
8. **Operational Reality → FHIR TestScript Runner** uses the same file whenever the SHN credential profile is selected.

Changing the path in Authentication takes effect in both pages, without
editing a CredentialProfile JSON. Paths are stored in Streamlit session state
only; different browser sessions can select different client files.
Restarting a session resets the value to the startup default.

### Option B — Set a startup default (also supports standalone CLI)

```bash
export SHN_CLIENT_FILE="$HOME/.config/medilacra/shn-client.json"
python -m streamlit run app.py
```

Both the historical MVP-0 SHN client and Workbench's example CredentialProfile
honor `SHN_CLIENT_FILE`. The file must already exist. Do not put the secret itself
in this environment variable; it contains a **path**, not the JSON contents.

When the variable is not set, the unified app looks for:
1. `apps/workbench/config/credentials/local/secrets/shn-client.json`
2. `apps/mvp0/connectathon/shn_live_baseline_00301/client.json` (historical MVP-0 location).

If neither exists, it suggests the first path. Both are gitignored local files.

### Check locally without printing the secret

```bash
test -f "$SHN_CLIENT_FILE" && echo "File exists" || echo "File not found"
```

For a local secret file use restrictive filesystem permissions such as
`chmod 600`. Do not paste client JSON, tokens, or full credential exports into
GitHub issues, chat or test logs.

## What successful setup proves

- **Client JSON found**: the file is readable JSON with two required keys.
- **Authenticated**: token acquisition from SHN succeeded for the selected
  client credentials.
- **Business function verified**: an actual SHN test case ran and its
  request/response evidence was retained and inspected. This is independent
  from OAuth success.

Use **SHN Provider ePA** for TP/TN reference tests against the provider
gateway. Use FHIR TestScript Runner only with a TestScript compatible with
the chosen TestSystem; do not point IRIS Patient CRUD at the SHN ePA gateway.

**Acceptance status:** The checklist below was originally written before the October 23 user acceptance run. See [accepted baseline and remaining limits](RELEASE_ACCEPTANCE_2026-10-23.md) for actual results, rather than interpreting the original empty boxes as missing tests.

## Internal v1 acceptance gates

- [ ] UI path entry and startup environment variable each load the intended
      client file, without displaying secret values.
- [ ] Authentication acquires a token from the intended SHN environment.
- [ ] SHN Provider ePA can execute a known-good TP-01 and export sanitized
      evidence; pending authorization is reported as pending, not approval.
- [ ] Workbench uses the same client and records evidence from a compatible
      SHN test.
- [ ] IRIS no-auth CapabilityStatement still works.
- [ ] Browser test of all retained Streamlit pages and exports.
- [ ] Verify process isolation before using the current working-directory
      compatibility launcher with multiple simultaneous users. At present
      `unified/legacy.py` calls `os.chdir()` per page, which is process-wide.
      Single-user local pilot use is the supported execution mode.
- [ ] Resolve combined-code licensing before redistribution/general release.

**No credentials, production system access or actual SHN request are required
to run the offline unit tests.**
