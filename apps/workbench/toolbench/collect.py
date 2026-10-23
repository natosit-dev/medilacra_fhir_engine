from __future__ import annotations

import argparse
from pathlib import Path

from .export import collection_zip_bytes, discover_runs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bundle recorded Workbench transaction evidence without network traffic."
    )
    parser.add_argument(
        "--results",
        default="results",
        help="Results root (default: results)",
    )
    parser.add_argument(
        "--output",
        help="Output ZIP path; defaults to results/collections/<collection-id>.zip",
    )
    args = parser.parse_args()

    runs = discover_runs(args.results)
    payload, manifest = collection_zip_bytes(runs)
    target = (
        Path(args.output)
        if args.output
        else Path(args.results)
        / "collections"
        / f"{manifest['collection_id']}.zip"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)

    summary = manifest["summary"]
    print(
        f"{target}\n"
        f"runs={summary['run_count']} "
        f"transactions={summary['transaction_count']} "
        f"events={summary['event_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
