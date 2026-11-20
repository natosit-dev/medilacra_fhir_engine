"""Deployment identity appears in existing SHN and Workbench evidence contexts."""
from __future__ import annotations

from unittest.mock import patch

from apps.workbench.toolbench.logging import execution_context as workbench_context
from apps.mvp0.connectathon.shn_provider.run_logging import execution_context as shn_context


def test_deployment_identity_in_both_run_loggers():
    environment = {
        "MEDILACRA_INSTANCE_ID": "nat-test0001",
        "MEDILACRA_HOST_PORT": "18510",
        "MEDILACRA_SOURCE_REF": "medilacra-unified@sha256:example",
    }
    with patch.dict("os.environ", environment):
        for context in (workbench_context("pytest"), shn_context("pytest")):
            assert context["medilacra_instance_id"] == environment["MEDILACRA_INSTANCE_ID"]
            assert context["medilacra_host_port"] == environment["MEDILACRA_HOST_PORT"]
            assert context["medilacra_source_ref"] == environment["MEDILACRA_SOURCE_REF"]
            assert context["log_schema_version"] in ("0.1", "1.0")
