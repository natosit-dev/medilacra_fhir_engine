"""Deployment identity appears in existing SHN and Workbench evidence contexts.

The legacy MVP-0 package has its own connectathon namespace. Import/test it
in a subprocess with that application's actual working directory, rather than
changing global sys.path for unrelated Engine tests.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

from apps.workbench.toolbench.logging import execution_context as workbench_context


def test_deployment_identity_in_both_run_loggers():
    environment = {
        "MEDILACRA_INSTANCE_ID": "nat-test0001",
        "MEDILACRA_HOST_PORT": "18510",
        "MEDILACRA_SOURCE_REF": "medilacra-unified@sha256:example",
    }
    with patch.dict(os.environ, environment):
        workbench = workbench_context("pytest")
        root = Path(__file__).resolve().parents[1]
        command = (
            "import json; "
            "from connectathon.shn_provider.run_logging import execution_context; "
            "print(json.dumps(execution_context('pytest')))"
        )
        completed = subprocess.run(
            [sys.executable, "-c", command],
            cwd=root / "apps" / "mvp0",
            capture_output=True,
            text=True,
            check=True,
            timeout=20,
        )
        shn = json.loads(completed.stdout.strip())
    for context in (workbench, shn):
        assert context["medilacra_instance_id"] == environment["MEDILACRA_INSTANCE_ID"]
        assert context["medilacra_host_port"] == environment["MEDILACRA_HOST_PORT"]
        assert context["medilacra_source_ref"] == environment["MEDILACRA_SOURCE_REF"]
        assert context["log_schema_version"] in ("0.1", "1.0")
