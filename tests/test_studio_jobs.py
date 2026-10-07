"""
Test Suite: Generic Studio Jobs & Delta RWI Flow
Validates:
1. Category registration and retrieval of sample jobs in General.csv.
2. Field completeness and schema conformance for Job Loop Studio.
3. Affordance cycle connectivity for sample jobs.
4. Delta RWI section explanations and input payload.
5. Compilation of Layer 2 manifest.
"""

import os
import sys
import unittest
from pathlib import Path

# Set up project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services import job_registry, delta_service


class TestStudioJobs(unittest.TestCase):

    def setUp(self):
        self.category = "General"
        self.expected_job_names = [
            "respond_to_input",
            "summarize_text",
            "task_planner",
        ]

    def test_01_category_exists_in_registry(self):
        """Verify General exists in registered categories."""
        categories = job_registry.get_categories()
        self.assertIn(self.category, categories, f"'{self.category}' must be in job categories: {categories}")

    def test_02_jobs_present_and_configured(self):
        """Verify all sample jobs exist and are properly configured."""
        jobs = job_registry.get_jobs(self.category)
        self.assertEqual(len(jobs), 3, f"Expected 3 jobs in {self.category}, found {len(jobs)}")

        job_map = {j["job_name"]: j for j in jobs}
        for name in self.expected_job_names:
            self.assertIn(name, job_map, f"Missing job '{name}'")
            job = job_map[name]
            self.assertTrue(job["enabled"], f"Job '{name}' must be enabled")
            self.assertTrue(job["job_id"], f"Job '{name}' must have a valid job_id")
            self.assertTrue(job["instruction_layer"], f"Job '{name}' must have instruction_layer")
            self.assertGreaterEqual(int(job["max_retries"]), 1, f"Job '{name}' max_retries must be >= 1")

    def test_03_affordance_connectivity(self):
        """Verify sample jobs have valid affordance definitions."""
        jobs = {j["job_name"]: j for j in job_registry.get_jobs(self.category)}

        # summarize_text and task_planner transition back to respond_to_input
        self.assertIn("General/respond_to_input", jobs["summarize_text"]["affordances"])
        self.assertIn("General/respond_to_input", jobs["task_planner"]["affordances"])

        # respond_to_input can route to summarize_text or task_planner
        resp_affordances = [a.strip() for a in jobs["respond_to_input"]["affordances"].split("|")]
        self.assertIn("General/summarize_text", resp_affordances)
        self.assertIn("General/task_planner", resp_affordances)

    def test_04_delta_rwi_explanations(self):
        """Verify Delta RWI contains section explanations."""
        rwi_file = PROJECT_ROOT / "deltas" / "sources" / "delta_rwi.txt"
        self.assertTrue(rwi_file.exists(), "delta_rwi.txt must exist")
        rwi_text = rwi_file.read_text(encoding="utf-8")

        self.assertIn("INPUT DELTA", rwi_text)
        self.assertIn("OPERATIONAL DIRECTIVE", rwi_text)

    def test_05_compiled_manifest(self):
        """Verify compiled manifest compiles successfully."""
        manifest = delta_service.compile_manifest()
        self.assertTrue(manifest.startswith("###DELTAS_START###"))
        self.assertTrue(manifest.endswith("###DELTAS_END###"))

        pos_rwi = manifest.find("###DELTA_RWI_START###")
        pos_input = manifest.find("###INPUT_DELTA_START###")

        self.assertNotEqual(pos_rwi, -1, "DELTA_RWI block missing")
        self.assertNotEqual(pos_input, -1, "INPUT_DELTA block missing")
        self.assertLess(pos_rwi, pos_input, "DELTA_RWI must appear before INPUT_DELTA")


if __name__ == "__main__":
    unittest.main()
