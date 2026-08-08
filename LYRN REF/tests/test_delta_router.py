import unittest
from fastapi.testclient import TestClient
import os
import shutil
import json

from start_lyrn import app

class TestDeltaRouter(unittest.TestCase):
    def setUp(self):
        # Temporarily bypass auth for testing
        with open("global_flags/no_auth", "w") as f:
            f.write("")
        self.client = TestClient(app)
        self.test_delta_dir = "runtime/deltas"

        # Clean up any existing deltas for clean test
        if os.path.exists(self.test_delta_dir):
            shutil.rmtree(self.test_delta_dir)

    def tearDown(self):
        if os.path.exists("global_flags/no_auth"):
            os.remove("global_flags/no_auth")
        if os.path.exists(self.test_delta_dir):
            shutil.rmtree(self.test_delta_dir)

    def test_create_and_get_delta(self):
        # Create
        data = {
            "name": "Test Delta",
            "script_sequence": "echo 'hello'",
            "trigger_level": "Active",
            "update_time": "10s",
            "notes": "Test notes",
            "enabled": True
        }
        res = self.client.post("/api/deltas", json=data)
        self.assertEqual(res.status_code, 200)
        json_res = res.json()
        self.assertTrue(json_res["success"])
        delta_id = json_res["delta"]["delta_id"]

        # Get all
        res = self.client.get("/api/deltas")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()["deltas"]), 1)
        self.assertEqual(res.json()["deltas"][0]["name"], "Test Delta")

        # Get one
        res = self.client.get(f"/api/deltas/{delta_id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["delta"]["name"], "Test Delta")

    def test_update_delta(self):
        # Create
        data = {
            "name": "Delta 1",
            "enabled": True
        }
        res = self.client.post("/api/deltas", json=data)
        delta_id = res.json()["delta"]["delta_id"]

        # Update
        update_data = {
            "name": "Updated Delta 1",
            "enabled": False
        }
        res = self.client.put(f"/api/deltas/{delta_id}", json=update_data)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["delta"]["name"], "Updated Delta 1")
        self.assertEqual(res.json()["delta"]["enabled"], False)

    def test_delete_delta(self):
        # Create
        data = {"name": "To Delete"}
        res = self.client.post("/api/deltas", json=data)
        delta_id = res.json()["delta"]["delta_id"]

        # Delete
        res = self.client.delete(f"/api/deltas/{delta_id}")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])

        # Verify deletion
        res = self.client.get(f"/api/deltas/{delta_id}")
        self.assertEqual(res.status_code, 404)

if __name__ == '__main__':
    unittest.main()
