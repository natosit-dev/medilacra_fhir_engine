# Medilacra private AWS instance MVP

**Status:** Implementation plus offline tests; not yet deployed to EC2, built as a container, or validated against real SHN/IRIS endpoints. Deployment branch: `feat/aws-instance-mvp-20261120`.

## Harvested behavior

The application is still the unified Streamlit `app.py`, `unified/page_catalog.py`, and `unified/legacy.py` from `medilacra_fhir_engine`. Existing SHN CRD/DTR/PAS reference runners and Workbench TestScript execution remain unchanged. Existing SHN `run.json` / `events.jsonl` and Workbench evidence formats are preserved, not rewritten. October 23 accepted local reference: commit `82c184146afcac3979ed86808ddf91c6d5fc207d`.

## New deployment wrapper

- `deploy/Dockerfile`: unified app in Python 3.10; records resolved dependency versions inside the image. Dependency ranges and base image must be locked to an approved digest for fully reproducible releases.
- `deploy/instance_manager.py`: CLI `create`, `list`, `start`, `stop`, `restart`, `status`, `logs`. Uses Docker Compose and an atomic locked registry. No destructive deletion in v0.1; stopped instances retain ports until a reviewed deprovisioning mechanism is implemented.
- `deploy/entrypoint.py`: Streamlit launcher and JSON operational events with instance/port/image identity. Best-effort credential-line suppression is not a guarantee for arbitrary exception output or sensitive payloads.
- `deploy/output_index.py`: on-demand, metadata-only inventory of the shared run root; does not read payloads, follow symlinks or run a background watcher.
- `deploy/tests`: offline tests of ports, instance separation, secret mounts, registry, Compose arguments and logging.

**Runtime:** one container and Streamlit process per operator; host ports `18510`–`18549` bind exclusively to EC2 `127.0.0.1`; Streamlit listens on container port `8501`. An SSM tunnel grants private workstation access without a public listener. A per-user port is **not** application authentication. The existing `unified/legacy.py` process-wide `os.chdir()` remains unsafe for concurrent sessions *inside the same container*; a container per operator only solves cross-container process sharing. Do not treat this as certified multi-tenant hosting.

**Storage:** `/srv/medilacra/workspaces/<instance-id>/` stores user input, caches, uploads and configuration; `/srv/medilacra/runs/p<port>_<instance-id>/` stores separate `workbench`, `shn`, `hl7`, `disco`, and `mvp0-logs` output paths via bind mounts. All runs are discoverable from one root while individual instances cannot write into one another's mounted directories. Host Docker administrators can still access them all. Existing experiment run IDs are preserved; the port is a human-readable path hint, not the identity key.

## Initial installation on `shn-testing-medilacra`

Target EC2: `i-09b7b758d9e24926f`. Docker Engine/Compose host installation previously passed `hello-world`; that **does not** prove this new image builds.

Work as an authorized **non-root** Docker operator; the manager refuses root execution so it doesn't accidentally run application containers as UID 0.

```bash
sudo install -d -o "$USER" -g "$(id -gn)" -m 700 /srv/medilacra
git clone https://github.com/natosit-dev/medilacra_fhir_engine.git
cd medilacra_fhir_engine
git switch feat/aws-instance-mvp-20261120
git status --short
git rev-parse HEAD
docker build -f deploy/Dockerfile --build-arg MEDILACRA_SOURCE_SHA="$(git rev-parse HEAD)" -t medilacra-unified:mvp .
python3 deploy/instance_manager.py create nat --image medilacra-unified:mvp --port 18510
python3 deploy/instance_manager.py start nat
python3 deploy/instance_manager.py status nat
python3 deploy/instance_manager.py list
python3 deploy/instance_manager.py logs nat
```

From **local WSL** (not from inside an SSM remote shell), open the browser tunnel and leave its terminal running:

```bash
aws sso login --profile shn-testing
aws ssm start-session --profile shn-testing --region us-east-1 \
  --target i-09b7b758d9e24926f \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["18510"],"localPortNumber":["18510"]}'
```

Browse to `http://localhost:18510`. The second operator should use a separate port and SSM tunnel, e.g. `18511`.

## WinSCP/SFTP from Windows

After installing an authorized SSH public key for the EC2 `ubuntu` account, use a second **local WSL** tunnel:

```bash
aws ssm start-session --profile shn-testing --region us-east-1 \
  --target i-09b7b758d9e24926f \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["22"],"localPortNumber":["12022"]}'
```

WinSCP SFTP settings: host `127.0.0.1`, port `12022`, user `ubuntu`, authorized private key. Verify the SSH host-key fingerprint independently. Upload approved synthetic fixtures only to the assigned `workspaces/<instance-id>/uploads` path, and inspect evidence in `runs/`. Sharing the host `ubuntu` account does not provide OS-level user isolation. Session Manager does not log SSH/SFTP payloads.

## Credentials, logging and evidence boundaries

An optional `--shn-client-file /secure/path/shn-client.json` during `create` requires a preprovisioned, mode-600 host file. It is mounted read-only to `/run/secrets/shn-client.json` and that **path**, not the secret, is exported as `SHN_CLIENT_FILE`. Retrieval and rotation from `shn-testing/` Secrets Manager are **not implemented yet**.

Docker logs use rotation (10MB x 3), with JSON operational events from the launcher. CloudWatch shipping has **not** been configured. Keep SHN and Workbench run evidence in its native versioned format; never conflate HTTP transport success with a passing test assertion. S3 backup and ECR push/pull by digest are future AWS acceptance gates.

Inspect the central output folder:

```bash
python3 deploy/output_index.py nat
find /srv/medilacra/runs -maxdepth 3 -type f | sort
python3 -m unittest discover -s deploy/tests -v
```

## Real acceptance gates — not yet passed

1. Image builds at a frozen, clean Git SHA; inspect resolved dependencies, image contents and first private Streamlit health; rerun the original accepted offline tests and manually exercise the unified UI.
2. Start two containers concurrently, exercise distinct SHN/Workbench test cases and identical filenames, verify separate DuckDB and artifact writes, stop/recreate each and verify persistence. Test two tabs within one instance explicitly.
3. Transfer synthetic fixture and evidence ZIP with WinSCP via SSM, verify permissions and server host key.
4. Verify scoped ECR, Secrets Manager, CloudWatch and evidence S3 operations; then verify actual SHN and IRIS test endpoints before making any connectivity claims. IRIS currently binds `52773` only to its own EC2 loopback.
5. Complete a second-operator handoff and record outputs in the SHN AWS field log.

**Deliberately deferred:** web self-provisioning, identity proxy, autoscaling, background cohort workers, continuous folder monitoring, all-version log migration, multi-tenant security certification and complete PIQITT/DiScO standalone process deployment.
