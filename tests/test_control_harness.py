"""
Unit Tests for LYRN Control and Test Harness.
Validates:
1. LyrnClient configuration auto-detection (port.txt, base_url).
2. X-Token header injection and request construction.
3. LyrnApiError handling.
4. BenchmarkResult and HarnessReport data models.
5. Mocked API calls for server health and deltas.
"""

import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import json
import io

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from harness.lyrn_client import LyrnClient, LyrnApiError, BenchmarkResult
from harness.lyrn_harness import LyrnTestHarness, HarnessCheckResult, HarnessReport


class TestControlHarness(unittest.TestCase):

    def setUp(self):
        self.client = LyrnClient(token="test_token_12345678901234567890")

    def test_01_client_auto_detection(self):
        """Verifies client auto-detects port from port.txt."""
        client = LyrnClient()
        self.assertTrue(client.base_url.startswith("http://localhost:"))
        self.assertIn("8080", client.base_url)

    def test_02_custom_overrides(self):
        """Verifies custom URL and token overrides work properly."""
        client = LyrnClient(base_url="http://127.0.0.1:9000", token="custom_secret_123")
        self.assertEqual(client.base_url, "http://127.0.0.1:9000")
        self.assertEqual(client.token, "custom_secret_123")

    @patch("urllib.request.urlopen")
    def test_03_request_sends_x_token_header(self, mock_urlopen):
        """Verifies standard requests send the X-Token header and Content-Type."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"status": "ok"}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        res = self.client.request("POST", "/api/test", data={"key": "value"})

        self.assertEqual(res, {"status": "ok"})
        req_arg = mock_urlopen.call_args[0][0]
        self.assertEqual(req_arg.headers["X-token"], "test_token_12345678901234567890")
        self.assertEqual(req_arg.headers["Content-type"], "application/json")

    @patch("urllib.request.urlopen")
    def test_04_api_error_raised_on_http_error(self, mock_urlopen):
        """Verifies HTTP errors are cleanly caught and wrapped in LyrnApiError."""
        import urllib.error
        err_fp = io.BytesIO(b'{"detail": "Unauthorized access"}')
        http_err = urllib.error.HTTPError("http://localhost:8080/api/test", 401, "Unauthorized", {}, err_fp)
        mock_urlopen.side_effect = http_err

        with self.assertRaises(LyrnApiError) as ctx:
            self.client.request("GET", "/api/test")

        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("Unauthorized", ctx.exception.message)

    def test_05_benchmark_result_data_model(self):
        """Verifies BenchmarkResult stores fields properly."""
        b = BenchmarkResult(
            test_id="bench-1",
            state="completed",
            output_text="Test response",
            duration_seconds=2.5,
            prompt_tokens=50,
            prompt_speed=125.0,
            eval_tokens=20,
            eval_speed=8.0,
            total_tokens=70,
            kv_cache_reused=50,
            tokenization_time_ms=10.0,
            generation_time_ms=2490.0,
        )
        self.assertEqual(b.test_id, "bench-1")
        self.assertEqual(b.total_tokens, 70)
        self.assertEqual(b.eval_speed, 8.0)
        self.assertEqual(b.kv_cache_reused, 50)

    def test_06_harness_check_result_and_report(self):
        """Verifies HarnessCheckResult and HarnessReport data models."""
        c1 = HarnessCheckResult(name="Health", passed=True, message="OK", duration=0.1)
        c2 = HarnessCheckResult(name="Auth", passed=True, message="Authenticated", duration=0.2)
        report = HarnessReport(checks=[c1, c2], total_duration=0.3, passed_count=2, failed_count=0)

        self.assertTrue(report.all_passed)
        self.assertEqual(len(report.checks), 2)
        self.assertEqual(report.passed_count, 2)
        self.assertEqual(report.failed_count, 0)

    @patch.object(LyrnClient, "start_server")
    @patch.object(LyrnClient, "get_health")
    def test_07_harness_check_health(self, mock_health, mock_start):
        """Verifies check_health in test harness."""
        mock_health.return_value = {"status": "ok", "app": "LYRN"}
        harness = LyrnTestHarness(self.client)
        result = harness.check_health()

        self.assertTrue(result.passed)
        self.assertEqual(result.name, "Server Health & Telemetry")

    @patch.object(LyrnClient, "get_delta_manifest")
    @patch.object(LyrnClient, "compile_deltas")
    @patch.object(LyrnClient, "get_delta_blocks")
    def test_08_harness_check_deltas(self, mock_get_delta_blocks, mock_compile, mock_manifest):
        """Verifies check_deltas compiles manifest and reads delta blocks."""
        mock_manifest.return_value = {"content": "###DELTAS_START###...###DELTAS_END###"}
        mock_compile.return_value = {"status": "compiled"}
        mock_get_delta_blocks.return_value = [{"id": "input_delta", "name": "Input Delta", "enabled": True}]
        harness = LyrnTestHarness(self.client)
        result = harness.check_deltas()

        self.assertTrue(result.passed)
        self.assertEqual(result.name, "Layer 2 Delta Working Memory")


if __name__ == "__main__":
    unittest.main()
