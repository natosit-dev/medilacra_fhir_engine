"""Offline acceptance tests for the AWS deployment wrapper (no Docker needed)."""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from deploy import entrypoint, instance_manager as manager, output_index


class TestManager(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "medilacra"

    def test_two_users_isolated_and_loopback_only(self):
        with patch.object(manager, "port_available", return_value=True):
            a = manager.create(self.root, "nat", "medilacra:test", 18510)
            b = manager.create(self.root, "tester2", "medilacra:test", 18511)
        self.assertNotEqual(a["instance_id"], b["instance_id"])
        for entry in (a, b):
            workspace, runroot = manager.instance_dirs(self.root, entry)
            self.assertTrue((workspace / "compose.yaml").exists())
            self.assertTrue((runroot / "instance.json").exists())
            compose = (workspace / "compose.yaml").read_text()
            self.assertIn(f"127.0.0.1:{entry['port']}:8501", compose)
            self.assertNotIn("/var/run/docker.sock", compose)
            self.assertNotIn("0.0.0.0:", compose)
            self.assertIn(str(runroot / "shn"), compose)
        with self.assertRaisesRegex(ValueError, "already exists"):
            manager.create(self.root, "nat", "medilacra:test")
        with self.assertRaisesRegex(ValueError, "unavailable"):
            manager.create(self.root, "tester3", "medilacra:test", 18510)
        self.assertEqual(manager.get_record(self.root, "nat")["port"], 18510)
        self.assertEqual(manager.get_record(self.root, b["instance_id"])["port"], 18511)

    def test_invalid_arguments_do_not_modify_registry(self):
        for user in ("../nat", "UPPER", "a b"):
            with self.assertRaises(ValueError):
                manager.create(self.root, user, "medilacra:test")
        with self.assertRaises(ValueError):
            manager.create(self.root, "nat", "image\nvolumes: evil")
        with self.assertRaises(ValueError):
            manager.create(self.root, "nat", "image:test", 8501)

    def test_compose_invocation_is_scoped_to_instance(self):
        with patch.object(manager, "port_available", return_value=True):
            entry = manager.create(self.root, "nat", "medilacra:test", 18510)
        with patch.object(manager.subprocess, "run") as run:
            manager.manage(self.root, "nat", "start")
        cmd = run.call_args.args[0]
        self.assertEqual(cmd[:2], ["docker", "compose"])
        self.assertEqual(cmd[cmd.index("-p") + 1], entry["project"])
        self.assertEqual(cmd[-3:], ["up", "-d", "--no-build"])

    def test_secret_not_duplicated_into_registry_output(self):
        secret = Path(self.tmp.name) / "client.json"
        secret.write_text('{"client_id":"dummy","client_secret":"dummy"}')
        secret.chmod(0o600)
        with patch.object(manager, "port_available", return_value=True):
            entry = manager.create(self.root, "nat", "medilacra:test", 18510, str(secret))
        workspace, _ = manager.instance_dirs(self.root, entry)
        compose = (workspace / "compose.yaml").read_text()
        self.assertIn(":/run/secrets/shn-client.json:ro", compose)
        self.assertNotIn("dummy", compose)
        self.assertEqual(compose.count("SHN_CLIENT_FILE"), 1)
        with redirect_stdout(io.StringIO()) as out:
            manager.print_registry(self.root)
        self.assertNotIn(str(secret), out.getvalue())

    def test_index_multiple_file_types_no_content_access(self):
        with patch.object(manager, "port_available", return_value=True):
            instance = manager.create(self.root, "nat", "medilacra:test", 18510)
        _, runs = manager.instance_dirs(self.root, instance)
        (runs / "workbench" / "run-x").mkdir()
        (runs / "workbench" / "run-x" / "events.jsonl").write_text('{"event":1}\n')
        (runs / "workbench" / "secret-link").symlink_to(Path(self.tmp.name) / "out-of-scope")
        index = output_index.index_instance(self.root, "nat")
        self.assertEqual(index["instance_id"], instance["instance_id"])
        self.assertEqual(index["file_count"], 1)
        self.assertEqual(index["files"][0]["path"], "workbench/run-x/events.jsonl")
        file = output_index.save_index(self.root, index)
        self.assertEqual(json.loads(file.read_text())["file_count"], 1)


class TestLogs(unittest.TestCase):
    def test_structured_event_and_secret_suppression(self):
        with patch.dict(entrypoint.os.environ, {"MEDILACRA_INSTANCE_ID": "nat-a", "MEDILACRA_HOST_PORT": "18510"}):
            with redirect_stdout(io.StringIO()) as output:
                event = entrypoint.emit("instance.starting", {"internal_port": 8501})
        self.assertEqual(json.loads(output.getvalue()), event)
        self.assertEqual(event["instance_id"], "nat-a")
        self.assertEqual(entrypoint.safe_line("Authorization: Bearer secret-value"), "[suppressed: potential credential material]")
        self.assertEqual(entrypoint.safe_line("client_secret=not-for-logs"), "[suppressed: potential credential material]")
        self.assertEqual(entrypoint.safe_line("Streamlit ready\n"), "Streamlit ready")


if __name__ == "__main__":
    unittest.main()
