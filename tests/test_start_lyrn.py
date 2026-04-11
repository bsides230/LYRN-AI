import unittest
from fastapi.testclient import TestClient
import os
import sys

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from start_lyrn import app
import core.state as state

class TestStartLyrnExhaustive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Allow testing protected endpoints without token validation failures
        with open("global_flags/no_auth", "w") as f:
            f.write("")
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists("global_flags/no_auth"):
            os.remove("global_flags/no_auth")

    # --- start_lyrn.py Main/Root Endpoints ---
    def test_read_root(self):
        """Test the root route serves the dashboard.html"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("LYRN Dashboard", response.text)

    def test_static_files(self):
        """Test static file serving from LYRN_v6 directory"""
        response = self.client.get("/modules/ClaudeCode.html")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("Claude Code Control Center", response.text)

    # --- System Router ---
    def test_health_check(self):
        """Test the health check endpoint"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("cpu", data)
        self.assertIn("ram", data)
        self.assertIn("worker", data)

    def test_auth_status(self):
        """Test the auth status endpoint"""
        response = self.client.get("/api/auth/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("required", data)
        self.assertFalse(data["required"])  # because of global_flags/no_auth

    def test_system_worker_status(self):
        response = self.client.get("/api/system/worker_status")
        self.assertEqual(response.status_code, 200)

    # --- Config Router ---
    def test_api_config_get(self):
        """Test getting system config"""
        response = self.client.get("/api/config")
        self.assertEqual(response.status_code, 200)

    # --- FS Router ---
    def test_fs_list_directory(self):
        """Test listing current directory"""
        response = self.client.get("/api/fs/list?path=.")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, dict)
        self.assertIn("children", data)

    # --- Models Router ---
    def test_models_list(self):
        response = self.client.get("/api/models/list")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    # --- Chat Router ---
    def test_chat_trigger_generation(self):
        response = self.client.post("/api/chat/generate", json={"prompt": "hello", "system": ""})
        # If no model is loaded, it might return 400 or a specific error message, but the endpoint exists.
        # We just assert it doesn't 404.
        self.assertNotEqual(response.status_code, 404)

    # --- Claude Router ---
    def test_claude_runs_get(self):
        response = self.client.get("/api/claude/runs")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("runs", data)

    def test_claude_validate_cwd(self):
        response = self.client.post("/api/claude/validate_cwd", json={"cwd": "."})
        self.assertEqual(response.status_code, 200)

    # --- Snapshot Router ---
    def test_snapshot_list(self):
        response = self.client.get("/api/snapshots")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)


if __name__ == '__main__':
    unittest.main()
