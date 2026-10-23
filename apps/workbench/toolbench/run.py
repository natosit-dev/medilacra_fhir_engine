from __future__ import annotations

import argparse
import json
from pathlib import Path

from .credentials import get_profile
from .runner import TestScriptRunner
from .systems import get_system
from .testscript import load_testscript


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a FHIR TestScript against a configured Workbench TestSystem."
    )
    parser.add_argument("--system", required=True, help="TestSystem id")
    parser.add_argument("--testscript", required=True, help="Path to FHIR TestScript JSON")
    parser.add_argument(
        "--credential",
        help="CredentialProfile id; defaults to the TestSystem profile",
    )
    parser.add_argument(
        "--through",
        help="Run setup/actions through this action id instead of the entire script",
    )
    parser.add_argument(
        "--no-artifacts",
        action="store_true",
        help="Do not persist run evidence",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the complete TestRun JSON instead of the compact console view",
    )
    args = parser.parse_args()

    system = get_system(args.system)
    script = load_testscript(args.testscript)
    credential_id = args.credential or system.credential_profile or "none"
    profile = get_profile(credential_id)

    result = TestScriptRunner(
        persist_artifacts=not args.no_artifacts,
        execution_mode="cli",
    ).run(
        script,
        system,
        profile,
        through_action_id=args.through,
    )

    if args.json:
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True, default=str))
    else:
        print(
            f"{result.status}  {result.testscript_name} -> {result.system_name}  "
            f"{result.duration_ms:.1f} ms"
        )
        for action in result.actions:
            http = (
                (action.transport or {}).get("status_code")
                if action.transport
                else None
            )
            suffix = f"  HTTP {http}" if http is not None else ""
            print(
                f"{action.state:<11} {action.kind:<9} "
                f"{action.action_id:<28}{suffix}  {action.label}"
            )
        if result.unsupported_elements:
            print("Unsupported TestScript elements:")
            for element in result.unsupported_elements:
                print(f"  - {element}")
        if result.artifact_dir:
            print(f"Evidence: {result.artifact_dir}")

    if result.status == "PASS":
        return 0
    if result.status == "UNSUPPORTED":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
