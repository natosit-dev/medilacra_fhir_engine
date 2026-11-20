"""On-demand, metadata-only index of Medilacra's shared output subtrees.

Do not read artifact payloads or follow symlinks; no background watcher needed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile


def index_instance(root: Path, instance_id: str) -> dict:
    registry = json.loads((root / "registry" / "instances.json").read_text())
    if instance_id not in registry:
        matching = [k for k, value in registry.items() if value["user"] == instance_id]
        if len(matching) != 1:
            raise ValueError("instance not found or ambiguous")
        instance_id = matching[0]
    entry = registry[instance_id]
    runroot = root / "runs" / f'p{entry["port"]}_{entry["instance_id"]}'
    if not runroot.is_dir():
        raise FileNotFoundError(runroot)
    files = []
    for path in sorted(runroot.rglob("*")):
        if path.is_symlink() or not path.is_file() or path.name == "instance.json":
            continue
        rel = path.relative_to(runroot).as_posix()
        stat = path.stat()
        files.append({"path": rel, "bytes": stat.st_size,
                      "modified_ns": stat.st_mtime_ns})
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "instance_id": instance_id,
        "host_port": entry["port"],
        "output_root": str(runroot),
        "file_count": len(files),
        "total_bytes": sum(f["bytes"] for f in files),
        "files": files,
    }


def save_index(root: Path, document: dict) -> Path:
    path = root / "runs" / "indices" / f'p{document["host_port"]}_{document["instance_id"]}.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=".index-", suffix=".tmp")
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(document, out, indent=2, sort_keys=True)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instance", help="instance ID or user slug")
    parser.add_argument("--root", type=Path, default=Path("/srv/medilacra"))
    args = parser.parse_args()
    record = index_instance(args.root.resolve(), args.instance)
    path = save_index(args.root.resolve(), record)
    print(json.dumps({"index": str(path), "files": record["file_count"],
                      "total_bytes": record["total_bytes"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
