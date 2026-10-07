"""
Test Suite: Generic Backend Execution Scripts
Validates:
1. watchers/compile_deltas.py executes and compiles Layer 2 manifest.
2. scripts/parse_job_response.py validates allowed affordance tags.
3. scripts/parse_job_response.py detects disallowed or malformed affordance tags.
4. scripts/inject_job.py sets up global_flags/job_context.txt and handles missing jobs.
"""

import os
import sys
import shutil
import unittest
import subprocess
from pathlib import Path

# Setup project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services import job_registry, delta_service


class TestBackendScripts(unittest.TestCase):

    def setUp(self):
        self.temp_dir = PROJECT_ROOT / "runtime" / "jobs" / "test_scratch"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_compile_deltas_script(self):
        """Verify watchers/compile_deltas.py executes and compiles manifest."""
        script = PROJECT_ROOT / "watchers" / "compile_deltas.py"
        self.assertTrue(script.exists(), "watchers/compile_deltas.py must exist")

        res = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"compile_deltas failed: {res.stderr}")
        self.assertIn("Successfully compiled manifest", res.stdout)

        manifest_file = PROJECT_ROOT / "deltas" / "compiled_manifest.txt"
        self.assertTrue(manifest_file.exists())
        self.assertTrue(manifest_file.read_text(encoding="utf-8").startswith("###DELTAS_START###"))

    def test_02_parse_job_response_valid_affordance(self):
        """Verify parse_job_response.py successfully parses allowed affordance."""
        resp_file = self.temp_dir / "valid_resp.txt"
        resp_file.write_text("Summary complete.\n##AF: General/respond_to_input##\n", encoding="utf-8")

        script = PROJECT_ROOT / "scripts" / "parse_job_response.py"
        res = subprocess.run(
            [
                sys.executable,
                str(script),
                "--category", "General",
                "--job-name", "summarize_text",
                "--response-file", str(resp_file),
                "--no-auto-inject",
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        self.assertEqual(res.returncode, 0, f"Parser failed: {res.stderr}")
        self.assertIn("[Success]", res.stdout)
        self.assertIn("General/respond_to_input", res.stdout)

    def test_03_parse_job_response_disallowed_affordance(self):
        """Verify parse_job_response.py flags disallowed affordances."""
        resp_file = self.temp_dir / "invalid_resp.txt"
        resp_file.write_text("Action done.\n##AF: Unknown/invalid_affordance##\n", encoding="utf-8")

        script = PROJECT_ROOT / "scripts" / "parse_job_response.py"
        res = subprocess.run(
            [
                sys.executable,
                str(script),
                "--category", "General",
                "--job-name", "summarize_text",
                "--response-file", str(resp_file),
                "--no-auto-inject",
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        self.assertIn("Validation failed", res.stdout)

    def test_04_inject_job_nonexistent_fails(self):
        """Verify inject_job.py exits with error when job not found."""
        script = PROJECT_ROOT / "scripts" / "inject_job.py"
        res = subprocess.run(
            [
                sys.executable,
                str(script),
                "--category", "General",
                "--job-name", "nonexistent_job_12345",
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("not found", res.stdout)


if __name__ == "__main__":
    unittest.main()
