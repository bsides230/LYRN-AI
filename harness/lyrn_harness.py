"""
LYRN Diagnostic and Test Harness (LyrnTestHarness).
Executes end-to-end verification across Server Health, Authentication,
Layer 2 Delta Working Memory, Worker Lifecycle, Real-time Streaming Inference,
and Job Loop Execution.
"""

import time
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from .lyrn_client import LyrnClient, BenchmarkResult, LyrnApiError


@dataclass
class HarnessCheckResult:
    """Individual test check outcome."""
    name: str
    passed: bool
    message: str
    duration: float
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HarnessReport:
    """Consolidated summary report of all harness checks."""
    checks: List[HarnessCheckResult]
    total_duration: float
    passed_count: int
    failed_count: int
    benchmark: Optional[BenchmarkResult] = None

    @property
    def all_passed(self) -> bool:
        return self.failed_count == 0

    def print_summary(self):
        print("\n" + "=" * 70)
        print("                 LYRN SYSTEM TEST HARNESS REPORT")
        print("=" * 70)
        for check in self.checks:
            status_icon = "[PASS]" if check.passed else "[FAIL]"
            print(f"{status_icon:<8} | {check.name:<32} | {check.duration:6.2f}s | {check.message}")

        print("-" * 70)
        print(f"Results: {self.passed_count} Passed, {self.failed_count} Failed, Total Time: {self.total_duration:.2f}s")
        if self.benchmark:
            print("-" * 70)
            print("Real-time Inference Telemetry:")
            print(f"  * Prompt Speed:     {self.benchmark.prompt_speed:8.2f} tokens/sec ({self.benchmark.prompt_tokens} tokens)")
            print(f"  * Generation Speed: {self.benchmark.eval_speed:8.2f} tokens/sec ({self.benchmark.eval_tokens} tokens)")
            print(f"  * Total Tokens:     {self.benchmark.total_tokens}")
            print(f"  * KV Cache Hits:    {self.benchmark.kv_cache_reused}")
            print(f"  * Generation Time:  {self.benchmark.generation_time_ms / 1000.0:.2f}s")
        print("=" * 70 + "\n")


class LyrnTestHarness:
    """
    Automated control and test harness for the LYRN system.
    Runs verification suites and provides real-time telemetry streaming.
    """

    def __init__(self, client: Optional[LyrnClient] = None):
        self.client = client or LyrnClient()

    # ==========================================
    # Check 1: Server Health & Telemetry
    # ==========================================
    def check_health(self) -> HarnessCheckResult:
        start = time.time()
        try:
            # Ensure server is running
            self.client.start_server(wait=True, timeout=25.0)
            health = self.client.get_health()

            cpu = health.get("cpu", "N/A")
            ram = health.get("ram", {})
            ram_pct = ram.get("percent", "N/A")
            worker_st = health.get("worker", {}).get("llm_status", "unknown")
            active_model = health.get("llm_stats", {}).get("model_name", "None")

            msg = f"Server OK (CPU: {cpu}%, RAM: {ram_pct}%, Worker: {worker_st}, Model: {active_model})"
            return HarnessCheckResult("Server Health & Telemetry", True, msg, time.time() - start, health)
        except Exception as e:
            return HarnessCheckResult("Server Health & Telemetry", False, str(e), time.time() - start)

    # ==========================================
    # Check 2: Token Authentication
    # ==========================================
    def check_auth(self) -> HarnessCheckResult:
        start = time.time()
        try:
            valid = self.client.verify_token()
            if valid:
                msg = f"Admin token verified successfully ({self.client.token[:6]}...)"
                return HarnessCheckResult("Token Authentication", True, msg, time.time() - start)
            else:
                return HarnessCheckResult("Token Authentication", False, "Admin token rejected", time.time() - start)
        except Exception as e:
            return HarnessCheckResult("Token Authentication", False, str(e), time.time() - start)

    # ==========================================
    # Check 3: Layer 2 Delta Working Memory
    # ==========================================
    def check_deltas(self) -> HarnessCheckResult:
        start = time.time()
        try:
            blocks = self.client.get_delta_blocks()
            block_names = [b.get("name") or b.get("id") for b in blocks]

            compile_res = self.client.compile_deltas()
            manifest_size = compile_res.get("manifest_size", 0)

            manifest_res = self.client.get_delta_manifest()
            content_len = len(manifest_res.get("content", ""))

            msg = f"Blocks: {len(blocks)} ({', '.join(block_names)}), Manifest: {content_len} chars"
            return HarnessCheckResult(
                "Layer 2 Delta Working Memory",
                True,
                msg,
                time.time() - start,
                {"blocks": block_names, "manifest_size": manifest_size},
            )
        except Exception as e:
            return HarnessCheckResult("Layer 2 Delta Working Memory", False, str(e), time.time() - start)

    # ==========================================
    # Check 4: Worker Lifecycle (Start & Ready)
    # ==========================================
    def check_worker_lifecycle(self, timeout: float = 60.0) -> HarnessCheckResult:
        start = time.time()
        try:
            status = self.client.get_worker_status()
            if not status.get("running"):
                print("[Harness] Starting model worker (loading GGUF into memory)...")
                self.client.start_worker(wait_ready=True, timeout=timeout)
            elif status.get("llm_status") != "idle":
                print(f"[Harness] Worker is running ({status.get('llm_status')}), waiting for idle state...")
                self.client.wait_for_worker_idle(timeout=timeout)

            status = self.client.get_worker_status()
            pid = status.get("pid")
            llm_st = status.get("llm_status")
            msg = f"Worker running (PID: {pid}, LLM Status: {llm_st})"
            return HarnessCheckResult("Worker Process & Model Loading", True, msg, time.time() - start, status)
        except Exception as e:
            return HarnessCheckResult("Worker Process & Model Loading", False, str(e), time.time() - start)

    # ==========================================
    # Check 5: Real-time Streaming Inference Benchmark
    # ==========================================
    def check_realtime_inference(
        self,
        prompt: str = "Explain what an episodic memory system does in an AI architecture in 2 sentences.",
        timeout: float = 90.0,
        stream_to_stdout: bool = True,
    ) -> tuple[HarnessCheckResult, Optional[BenchmarkResult]]:
        start = time.time()
        try:
            if stream_to_stdout:
                print("\n" + "-" * 60)
                print(f"[Harness Benchmark Prompt]: \"{prompt}\"")
                print("[Streaming Output]: ", end="", flush=True)

            def on_token_cb(delta: str):
                if stream_to_stdout:
                    sys.stdout.write(delta)
                    sys.stdout.flush()

            bench_result = self.client.stream_benchmark(
                prompt=prompt,
                timeout=timeout,
                on_token=on_token_cb,
            )

            if stream_to_stdout:
                print("\n" + "-" * 60)

            passed = (
                bench_result.state in ("complete", "idle", "busy")
                and len(bench_result.output_text.strip()) > 0
            )

            msg = (
                f"Generated {bench_result.eval_tokens} tokens @ {bench_result.eval_speed:.2f} t/s "
                f"(Prompt: {bench_result.prompt_tokens} tokens @ {bench_result.prompt_speed:.2f} t/s, "
                f"KV Hits: {bench_result.kv_cache_reused})"
            )

            check = HarnessCheckResult(
                "Realtime Inference Benchmark",
                passed,
                msg,
                time.time() - start,
                {"benchmark": bench_result},
            )
            return check, bench_result
        except Exception as e:
            check = HarnessCheckResult("Realtime Inference Benchmark", False, str(e), time.time() - start)
            return check, None

    # ==========================================
    # Check 6: Job Loop Execution (API Injected)
    # ==========================================
    def check_job_loop(
        self,
        category: str = "General",
        job_name: str = "respond_to_input",
        timeout: float = 90.0,
    ) -> HarnessCheckResult:
        start = time.time()
        try:
            categories = self.client.get_job_categories()
            if category not in categories:
                return HarnessCheckResult(
                    "Job Loop Studio Injection",
                    False,
                    f"Category '{category}' not found in registered categories: {categories}",
                    time.time() - start,
                )

            jobs = self.client.get_jobs(category)
            job_match = next((j for j in jobs if j.get("job_name") == job_name), None)
            if not job_match:
                return HarnessCheckResult(
                    "Job Loop Studio Injection",
                    False,
                    f"Job '{job_name}' not found in category '{category}'",
                    time.time() - start,
                )

            print(f"[Harness] Injecting job '{category}/{job_name}' via API...")
            job_run_result = self.client.inject_and_await_job(
                category=category,
                job_name=job_name,
                timeout=timeout,
            )

            out_file = job_run_result.get("output_file")
            content = job_run_result.get("content", "")
            duration = job_run_result.get("duration", 0.0)

            passed = bool(out_file)
            msg = f"Job executed in {duration:.1f}s -> Output: {out_file} ({len(content)} chars)"

            return HarnessCheckResult(
                "Job Loop Studio Injection",
                passed,
                msg,
                time.time() - start,
                job_run_result,
            )
        except Exception as e:
            return HarnessCheckResult("Job Loop Studio Injection", False, str(e), time.time() - start)

    # ==========================================
    # Full Test Suite Execution
    # ==========================================
    def run_full_suite(
        self,
        benchmark_prompt: str = "Explain what an episodic memory system does in an AI architecture in 2 sentences.",
        job_category: str = "General",
        job_name: str = "respond_to_input",
    ) -> HarnessReport:
        """
        Runs the full automated test suite:
        1. Server Health
        2. Authentication
        3. Layer 2 Deltas
        4. Worker Lifecycle & Model Loading
        5. Real-time Inference Benchmark (with streaming output & metrics)
        6. Job Loop Injection
        """
        suite_start = time.time()
        checks: List[HarnessCheckResult] = []
        benchmark_res: Optional[BenchmarkResult] = None

        print("\n[Harness] Starting LYRN Autonomous Verification Suite...")

        # 1. Health
        c1 = self.check_health()
        checks.append(c1)
        print(f" -> [{c1.name}]: {'PASS' if c1.passed else 'FAIL'} - {c1.message}")

        # 2. Auth
        c2 = self.check_auth()
        checks.append(c2)
        print(f" -> [{c2.name}]: {'PASS' if c2.passed else 'FAIL'} - {c2.message}")

        # 3. Deltas
        c3 = self.check_deltas()
        checks.append(c3)
        print(f" -> [{c3.name}]: {'PASS' if c3.passed else 'FAIL'} - {c3.message}")

        # 4. Worker Lifecycle
        c4 = self.check_worker_lifecycle()
        checks.append(c4)
        print(f" -> [{c4.name}]: {'PASS' if c4.passed else 'FAIL'} - {c4.message}")

        # 5. Real-time Inference Benchmark
        if c4.passed:
            c5, benchmark_res = self.check_realtime_inference(prompt=benchmark_prompt)
            checks.append(c5)
            print(f" -> [{c5.name}]: {'PASS' if c5.passed else 'FAIL'} - {c5.message}")
        else:
            checks.append(HarnessCheckResult("Realtime Inference Benchmark", False, "Skipped due to worker startup failure", 0.0))

        # 6. Job Loop Execution
        if c4.passed:
            c6 = self.check_job_loop(category=job_category, job_name=job_name)
            checks.append(c6)
            print(f" -> [{c6.name}]: {'PASS' if c6.passed else 'FAIL'} - {c6.message}")
        else:
            checks.append(HarnessCheckResult("Job Loop Studio Injection", False, "Skipped due to worker startup failure", 0.0))

        total_duration = time.time() - suite_start
        passed_count = sum(1 for c in checks if c.passed)
        failed_count = sum(1 for c in checks if not c.passed)

        report = HarnessReport(
            checks=checks,
            total_duration=total_duration,
            passed_count=passed_count,
            failed_count=failed_count,
            benchmark=benchmark_res,
        )

        report.print_summary()
        return report
