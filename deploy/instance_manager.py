#!/usr/bin/env python3
"""Private, single-host Medilacra instance manager (Linux + Docker Compose).

No public listener, no Docker socket in app containers, no automatic secret copies.
The operator's access to Docker is privileged; do not expose this CLI as a web API.
"""
from __future__ import annotations

import argparse
import contextlib
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import uuid

PORT_MIN = 18510
PORT_MAX = 18549
NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,30}$")
IMAGE_RE = re.compile(r"^[a-zA-Z0-9_.:/@-]+$")
WRITER_MOUNTS = {
    "workbench": "apps/workbench/results",
    "shn": "apps/mvp0/connectathon/results",
    "hl7": "apps/mvp0/output",
    "disco": "apps/mvp0/experiments/disco_inferno/output",
    "mvp0-logs": "apps/mvp0/logs",
}
# Paths that contain mutable input or cached data; bind individually. Sources and
# application code remain in the image and are not mounted from the host.
WORKSPACE_MOUNTS = {
    "input": "apps/mvp0/input",
    "cache": "apps/mvp0/data",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def yaml_string(value: str) -> str:
    # JSON strings are valid YAML scalars. Never interpolate unchecked values.
    return json.dumps(value, ensure_ascii=True)


def secure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)


def atomic_json(path: Path, value: dict) -> None:
    """Never leave partial registry/manifest writes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".tmp-", suffix=".json", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def read_json(path: Path, fallback: dict | None = None) -> dict:
    if not path.exists():
        return {} if fallback is None else fallback
    return json.loads(path.read_text(encoding="utf-8"))


@contextlib.contextmanager
def locked(root: Path):
    secure_directory(root)
    secure_directory(root / "registry")
    lock_path = root / "registry" / ".lock"
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        with os.fdopen(fd, "r+") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            yield
    finally:
        pass


def root_paths(root: Path) -> tuple[Path, Path, Path]:
    return root / "registry" / "instances.json", root / "workspaces", root / "runs"


def port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def select_port(registry: dict, requested: int | None) -> int:
    used = {int(record["port"]) for record in registry.values()}
    candidates = [requested] if requested is not None else range(PORT_MIN, PORT_MAX + 1)
    for port in candidates:
        if port is None or not PORT_MIN <= port <= PORT_MAX:
            continue
        if port not in used and port_available(port):
            return port
    raise ValueError("No free port in 18510–18549 (or requested port unavailable)")


def validate_image(image: str) -> str:
    if not IMAGE_RE.fullmatch(image):
        raise ValueError("Image must be a single Docker image reference without whitespace")
    return image


def validate_secret(secret: str | None) -> str | None:
    if not secret:
        return None
    path = Path(secret).expanduser().resolve(strict=True)
    if not path.is_file() or not os.access(path, os.R_OK):
        raise ValueError("Credential path must reference a readable regular file")
    if path.stat().st_mode & 0o077:
        raise ValueError("Credential file must have no group/other permissions (chmod 600)")
    return str(path)


def instance_dirs(root: Path, record: dict) -> tuple[Path, Path]:
    return root / "workspaces" / record["instance_id"], root / "runs" / (f'p{record["port"]}_{record["instance_id"]}')


def compose_text(root: Path, record: dict) -> str:
    workspace, runroot = instance_dirs(root, record)
    volumes = []
    for key, relative in WORKSPACE_MOUNTS.items():
        volumes.append((workspace / key, Path("/opt/medilacra") / relative))
    for key, relative in WRITER_MOUNTS.items():
        volumes.append((runroot / key, Path("/opt/medilacra") / relative))
    # An explicit staging area for uploaded synthetic data / user downloads.
    volumes.append((workspace / "uploads", Path("/workspace/uploads")))
    volumes.append((workspace / "state", Path("/workspace/state")))
    volumes.append((workspace / "streamlit", Path("/home/medilacra/.streamlit")))
    secret = record.get("credential_path")
    if secret:
        volumes.append((Path(secret), Path("/run/secrets/shn-client.json")))
    lines = [
        'services:',
        '  medilacra:',
        f'    image: {yaml_string(record["image"])}',
        f'    container_name: {yaml_string("medilacra-" + record["instance_id"])}',
        f'    user: {yaml_string(str(os.getuid()) + ":" + str(os.getgid()))}',
        '    read_only: false',
        '    cap_drop: [ALL]',
        '    security_opt: ["no-new-privileges:true"]',
        '    init: true',
        '    restart: unless-stopped',
        '    pids_limit: 256',
        '    mem_limit: 2g',
        '    cpus: 1.0',
        '    ports:',
        f'      - {yaml_string("127.0.0.1:" + str(record["port"]) + ":8501")}',
        '    environment:',
        f'      MEDILACRA_INSTANCE_ID: {yaml_string(record["instance_id"])}',
        f'      MEDILACRA_HOST_PORT: {yaml_string(str(record["port"]))}',
        f'      MEDILACRA_SOURCE_REF: {yaml_string(record["image"])}',
        '      HOME: "/home/medilacra"',
        '      XDG_CACHE_HOME: "/workspace/state/cache"',
        '      PYTHONUNBUFFERED: "1"',
    ]
    if secret:
        lines.append('      SHN_CLIENT_FILE: "/run/secrets/shn-client.json"')
    lines.extend([
        '    volumes:',
        *[f'      - {yaml_string(str(host) + ":" + str(container) + (":ro" if secret and str(host) == secret else ":rw"))}' for host, container in volumes],
        '    logging:',
        '      driver: "json-file"',
        '      options:',
        '        max-size: "10m"',
        '        max-file: "3"',
        '',
    ])
    return "\n".join(lines)


def create(root: Path, user: str, image: str, requested_port: int | None = None, secret: str | None = None) -> dict:
    if not NAME_RE.fullmatch(user):
        raise ValueError("User must be a lowercase slug (letters, digits, hyphens)")
    image = validate_image(image)
    secret = validate_secret(secret)
    with locked(root):
        registry_path, _, _ = root_paths(root)
        registry = read_json(registry_path)
        if any(record["user"] == user for record in registry.values()):
            raise ValueError(f"An instance already exists for user {user!r}")
        port = select_port(registry, requested_port)
        record = {
            "instance_id": f"{user}-{uuid.uuid4().hex[:8]}",
            "user": user,
            "port": port,
            "image": image,
            "credential_path": secret,
            "created_at": now_utc(),
            "project": "",  # set below
        }
        record["project"] = "ml-" + record["instance_id"]
        workspace, runroot = instance_dirs(root, record)
        for folder in list(WORKSPACE_MOUNTS) + ["uploads", "state", "streamlit"]:
            secure_directory(workspace / folder)
        for folder in WRITER_MOUNTS:
            secure_directory(runroot / folder)
        compose_file = workspace / "compose.yaml"
        compose_file.write_text(compose_text(root, record), encoding="utf-8")
        compose_file.chmod(0o600)
        atomic_json(runroot / "instance.json", {
            "schema_version": "1.0", "instance_id": record["instance_id"],
            "port": port, "user": user, "image": image, "created_at": record["created_at"],
            "paths": sorted(WRITER_MOUNTS.keys()),
        })
        registry[record["instance_id"]] = record
        atomic_json(registry_path, registry)
        return record


def get_record(root: Path, selector: str) -> dict:
    registry_path, _, _ = root_paths(root)
    records = read_json(registry_path)
    matches = [r for r in records.values() if selector in (r["instance_id"], r["user"])]
    if len(matches) != 1:
        raise ValueError(f"Expected one instance for {selector!r}; found {len(matches)}")
    return matches[0]


def compose_command(root: Path, record: dict, *args: str) -> list[str]:
    workspace, _ = instance_dirs(root, record)
    return ["docker", "compose", "-p", record["project"], "-f", str(workspace / "compose.yaml"), *args]


def manage(root: Path, selector: str, operation: str) -> dict:
    record = get_record(root, selector)
    commands = {"start": ("up", "-d", "--no-build"), "stop": ("stop",), "restart": ("restart",),
                "status": ("ps",), "logs": ("logs", "--tail", "80")}
    if operation not in commands:
        raise ValueError("Unsupported operation")
    command = compose_command(root, record, *commands[operation])
    subprocess.run(command, check=True)
    return record


def print_registry(root: Path) -> None:
    registry_path, _, _ = root_paths(root)
    records = read_json(registry_path)
    # Never print the host credential path.
    public = [{k: r[k] for k in ("instance_id", "user", "port", "image", "created_at")}
              for r in records.values()]
    print(json.dumps(public, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/srv/medilacra"), help="Managed host workspace root")
    sub = parser.add_subparsers(dest="action", required=True)
    create_parser = sub.add_parser("create", help="Provision directories and Compose config (does not launch)")
    create_parser.add_argument("user", help="Lowercase operator identifier")
    create_parser.add_argument("--image", required=True, help="Pinned image reference, ideally image@sha256:...")
    create_parser.add_argument("--port", type=int)
    create_parser.add_argument("--shn-client-file", help="Optional chmod 600 host file, mounted read-only")
    sub.add_parser("list")
    for action in ("start", "stop", "restart", "status", "logs"):
        sub.add_parser(action).add_argument("instance", help="User or instance ID")
    opts = parser.parse_args(argv)
    root = opts.root.expanduser().resolve()
    if os.geteuid() == 0:
        print("ERROR: Run the instance manager as an unprivileged Docker operator, not via sudo/root", file=sys.stderr)
        return 2
    try:
        if opts.action == "create":
            result = create(root, opts.user, opts.image, opts.port, opts.shn_client_file)
            print(json.dumps({k: result[k] for k in ("instance_id", "user", "port", "image")}, indent=2))
        elif opts.action == "list":
            print_registry(root)
        else:
            result = manage(root, opts.instance, opts.action)
            if opts.action not in ("status", "logs"):
                print(f'{opts.action}: {result["instance_id"]} host port {result["port"]}')
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
