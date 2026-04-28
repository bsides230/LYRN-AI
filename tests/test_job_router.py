import unittest
import os
import shutil
from fastapi.testclient import TestClient
from start_lyrn import app
from services import job_registry

class TestJobRouter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a test environment
        cls.client = TestClient(app)

        # Ensure jobs directory is clean
        cls.test_jobs_dir = "runtime/jobs"
        if os.path.exists(cls.test_jobs_dir):
            shutil.rmtree(cls.test_jobs_dir)
        os.makedirs(cls.test_jobs_dir, exist_ok=True)

        # Mock token verification for tests
        os.makedirs("global_flags", exist_ok=True)
        with open("global_flags/no_auth", "w") as f:
            f.write("")

    @classmethod
    def tearDownClass(cls):
        # Clean up
        if os.path.exists(cls.test_jobs_dir):
            shutil.rmtree(cls.test_jobs_dir)
        if os.path.exists("global_flags/no_auth"):
            os.remove("global_flags/no_auth")

    def test_trigger_text_endpoints(self):
        # Default trigger text should be ##JOB_START##
        response = self.client.get("/api/jobs/config/trigger", headers={"X-Token": "test"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["trigger_text"], "##JOB_START##")

        # Set new trigger text
        response = self.client.post("/api/jobs/config/trigger", json={"trigger_text": "##TEST_TRIGGER##"}, headers={"X-Token": "test"})
        self.assertEqual(response.status_code, 200)

        # Get updated trigger text
        response = self.client.get("/api/jobs/config/trigger", headers={"X-Token": "test"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["trigger_text"], "##TEST_TRIGGER##")

    def test_rename_category(self):
        # Create a category
        self.client.post("/api/jobs/categories", json={"category": "test_cat1"}, headers={"X-Token": "test"})

        # Rename it
        response = self.client.put("/api/jobs/categories/test_cat1", json={"new_category": "test_cat_renamed"}, headers={"X-Token": "test"})
        self.assertEqual(response.status_code, 200)

        # Verify it was renamed
        response = self.client.get("/api/jobs/categories", headers={"X-Token": "test"})
        self.assertIn("test_cat_renamed", response.json()["categories"])
        self.assertNotIn("test_cat1", response.json()["categories"])

    def test_delete_category(self):
        # Create a category
        self.client.post("/api/jobs/categories", json={"category": "test_cat2"}, headers={"X-Token": "test"})

        # Verify it exists
        response = self.client.get("/api/jobs/categories", headers={"X-Token": "test"})
        self.assertIn("test_cat2", response.json()["categories"])

        # Delete it
        response = self.client.delete("/api/jobs/categories/test_cat2", headers={"X-Token": "test"})
        self.assertEqual(response.status_code, 200)

        # Verify it is deleted
        response = self.client.get("/api/jobs/categories", headers={"X-Token": "test"})
        self.assertNotIn("test_cat2", response.json()["categories"])

if __name__ == '__main__':
    unittest.main()
