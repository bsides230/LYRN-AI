"""
LYRN API Client (LyrnClient).
Provides complete HTTP API control over the LYRN backend server,
matching the API interactions used by the LYRN v6 dashboard interface.
"""

import os
import sys
import time
import json
import socket
import urllib.request
import urllib.parse
import urllib.error
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List, Generator, Callable

# Locate project root (directory containing start_lyrn.py)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class LyrnApiError(Exception):
    """Exception raised when an API request to LYRN fails."""
    def __init__(self, status_code: int, message: str, details: Any = None):
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code
        self.message = message
        self.details = details


@dataclass
class BenchmarkResult:
    """Encapsulates the metrics and output of a real-time inference benchmark run."""
    test_id: str
    state: str
    output_text: str
    duration_seconds: float
    prompt_tokens: int = 0
    prompt_speed: float = 0.0
    eval_tokens: int = 0
    eval_speed: float = 0.0
    total_tokens: int = 0
    kv_cache_reused: int = 0
    tokenization_time_ms: float = 0.0
    generation_time_ms: float = 0.0
    hw_telemetry: Dict[str, Any] = field(default_factory=dict)
    raw_stats: Dict[str, Any] = field(default_factory=dict)


class LyrnClient:
    """
    HTTP REST Client to fully control LYRN backend server.
    All control operations execute strictly through official API endpoints.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: float = 15.0,
        project_root: Optional[Path] = None,
    ):
        self.project_root = project_root or PROJECT_ROOT
        self.timeout = timeout

        # Resolve port and base_url
        if base_url:
            self.base_url = base_url.rstrip("/")
        else:
            port = self._detect_port()
            self.base_url = f"http://localhost:{port}"

        # Resolve admin token
        if token:
            self.token = token
        else:
            self.token = self._detect_token()

        self._server_proc: Optional[subprocess.Popen] = None

    def _detect_port(self) -> int:
        """Reads port.txt from project root if present, defaults to 8080."""
        port_file = self.project_root / "port.txt"
        if port_file.exists():
            try:
                val = port_file.read_text(encoding="utf-8").strip()
                if val.isdigit():
                    return int(val)
            except Exception:
                pass
        return 8080

    def _detect_token(self) -> str:
        """Reads admin_token.txt from project root if present."""
        token_file = self.project_root / "admin_token.txt"
        if token_file.exists():
            try:
                return token_file.read_text(encoding="utf-8").strip()
            except Exception:
                pass
        return ""

    # ==========================================
    # HTTP Transport
    # ==========================================

    def request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        auth_required: bool = True,
    ) -> Any:
        """
        Executes an HTTP request to the LYRN API with standard headers.
        """
        url = f"{self.base_url}/{path.lstrip('/')}"
        if params:
            query = urllib.parse.urlencode(params)
            url = f"{url}?{query}"

        headers = {
            "User-Agent": "LyrnControlHarness/1.0",
            "Accept": "application/json",
        }
        if auth_required and self.token:
            headers["X-Token"] = self.token

        body_bytes = None
        if data is not None:
            headers["Content-Type"] = "application/json"
            body_bytes = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method.upper())
        req_timeout = timeout if timeout is not None else self.timeout

        try:
            with urllib.request.urlopen(req, timeout=req_timeout) as resp:
                resp_content = resp.read().decode("utf-8")
                if resp_content:
                    try:
                        return json.loads(resp_content)
                    except json.JSONDecodeError:
                        return resp_content
                return {}
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
                parsed_err = json.loads(error_body)
                detail = parsed_err.get("detail", error_body)
            except Exception:
                detail = error_body or str(e)
            raise LyrnApiError(e.code, detail, details=error_body)
        except urllib.error.URLError as e:
            raise LyrnApiError(0, f"Connection failed to {self.base_url}: {e.reason}")
        except socket.timeout:
            raise LyrnApiError(408, f"Request to {url} timed out after {req_timeout}s")

    # ==========================================
    # Server Lifecycle Management
    # ==========================================

    def is_server_alive(self, timeout: float = 2.0) -> bool:
        """Pings GET /health to check if the server is responding."""
        try:
            res = self.request("GET", "/health", timeout=timeout, auth_required=False)
            return isinstance(res, dict) and res.get("status") == "ok"
        except Exception:
            return False

    def start_server(self, wait: bool = True, timeout: float = 30.0) -> subprocess.Popen:
        """
        Launches the LYRN backend server (start_lyrn.py) if not already running.
        Saves process ID to server.pid.
        """
        if self.is_server_alive():
            print(f"[Client] LYRN server is already active at {self.base_url}")
            return self._server_proc

        start_script = self.project_root / "start_lyrn.py"
        if not start_script.exists():
            raise FileNotFoundError(f"Server script not found: {start_script}")

        log_path = self.project_root / "server.log"
        log_file = open(log_path, "a", encoding="utf-8")

        print(f"[Client] Launching server on {self.base_url} (logging to {log_path.name})...")
        flags = 0
        if sys.platform == "win32":
            detached = getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
            create_group = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
            flags = detached | create_group

        self._server_proc = subprocess.Popen(
            [sys.executable, str(start_script)],
            cwd=str(self.project_root),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=flags,
        )

        # Write server.pid
        pid_file = self.project_root / "server.pid"
        try:
            pid_file.write_text(str(self._server_proc.pid), encoding="utf-8")
        except Exception:
            pass

        if wait:
            self.wait_for_server(timeout=timeout)

        return self._server_proc

    def wait_for_server(self, timeout: float = 30.0, check_interval: float = 0.5) -> bool:
        """Polls /health until the server is responsive or timeout expires."""
        start_time = time.time()
        print(f"[Client] Waiting for server at {self.base_url} to become ready...", end="", flush=True)
        while time.time() - start_time < timeout:
            if self.is_server_alive(timeout=1.0):
                print(" Ready.")
                return True
            time.sleep(check_interval)
            print(".", end="", flush=True)
        print(" Timed out.")
        raise TimeoutError(f"Server at {self.base_url} failed to respond within {timeout}s")

    def stop_server(self) -> bool:
        """Stops the backend server process if managed or found via server.pid."""
        # Try internal handle
        if self._server_proc and self._server_proc.poll() is None:
            print("[Client] Terminating managed server process...")
            self._server_proc.terminate()
            try:
                self._server_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._server_proc.kill()
            self._server_proc = None
            return True

        # Try server.pid file
        pid_file = self.project_root / "server.pid"
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text(encoding="utf-8").strip())
                import psutil
                if psutil.pid_exists(pid):
                    proc = psutil.Process(pid)
                    proc.terminate()
                    proc.wait(timeout=5)
                    print(f"[Client] Terminated server PID {pid}")
                    return True
            except Exception as e:
                print(f"[Client] Could not stop PID: {e}")
            finally:
                try:
                    pid_file.unlink()
                except Exception:
                    pass

        return False

    # ==========================================
    # System & Telemetry Endpoints
    # ==========================================

    def get_health(self) -> Dict[str, Any]:
        """Calls GET /health. Returns CPU, RAM, GPU, Disk, Worker, and LLM stats."""
        return self.request("GET", "/health", auth_required=False)

    def get_auth_status(self) -> Dict[str, Any]:
        """Calls GET /api/auth/status."""
        return self.request("GET", "/api/auth/status", auth_required=False)

    def verify_token(self) -> bool:
        """Calls POST /api/verify_token. Returns True if valid."""
        try:
            res = self.request("POST", "/api/verify_token")
            return res.get("status") == "valid"
        except LyrnApiError:
            return False

    # ==========================================
    # Worker Lifecycle Endpoints
    # ==========================================

    def get_worker_status(self) -> Dict[str, Any]:
        """
        Calls GET /api/system/worker_status.
        Returns: {'running': bool, 'pid': int|None, 'llm_status': str, 'error_message': str|None}
        """
        return self.request("GET", "/api/system/worker_status")

    def start_worker(self, wait_ready: bool = True, timeout: float = 60.0) -> Dict[str, Any]:
        """
        Calls POST /api/system/start_worker to boot model_runner.py.
        If wait_ready=True, polls until running=True and llm_status='idle'.
        """
        res = self.request("POST", "/api/system/start_worker")
        if wait_ready:
            self.wait_for_worker_idle(timeout=timeout)
        return res

    def wait_for_worker_idle(self, timeout: float = 60.0, check_interval: float = 0.5) -> Dict[str, Any]:
        """Polls worker status until llm_status is 'idle'."""
        start_time = time.time()
        print("[Client] Waiting for model worker to load and become idle...", end="", flush=True)
        while time.time() - start_time < timeout:
            status = self.get_worker_status()
            llm_status = status.get("llm_status")
            if status.get("running") and llm_status == "idle":
                print(" Idle & Ready.")
                return status
            if llm_status == "error":
                err = status.get("error_message") or "Unknown worker load error"
                print(f" ERROR: {err}")
                raise RuntimeError(f"Worker reported error: {err}")
            time.sleep(check_interval)
            print(".", end="", flush=True)
        print(" Timed out.")
        raise TimeoutError(f"Model worker failed to enter 'idle' state within {timeout}s")

    def stop_worker(self) -> Dict[str, Any]:
        """Calls POST /api/system/stop_worker."""
        return self.request("POST", "/api/system/stop_worker")

    def clear_stats(self) -> Dict[str, Any]:
        """Calls POST /api/system/clear_stats."""
        return self.request("POST", "/api/system/clear_stats")

    # ==========================================
    # Model Inspection & Benchmark Endpoints
    # ==========================================

    def list_models(self) -> List[Dict[str, Any]]:
        """Calls GET /api/models/list."""
        return self.request("GET", "/api/models/list")

    def inspect_model(self, name: str) -> Dict[str, Any]:
        """Calls GET /api/models/inspect?name={name}."""
        return self.request("GET", "/api/models/inspect", params={"name": name})

    def trigger_benchmark(self, prompt: str) -> str:
        """
        Calls POST /api/models/test_benchmark with prompt.
        Returns the generated test_id (e.g. 'bench_20260924_...txt').
        """
        res = self.request("POST", "/api/models/test_benchmark", data={"prompt": prompt})
        if not res.get("success") or not res.get("test_id"):
            raise LyrnApiError(500, f"Benchmark trigger failed: {res}")
        return res["test_id"]

    def get_benchmark_status(self, test_id: str) -> Dict[str, Any]:
        """
        Calls GET /api/models/test_status/{test_id}.
        Returns dict with keys: 'test_id', 'state', 'output', 'stats'.
        """
        return self.request("GET", f"/api/models/test_status/{test_id}")

    def stop_benchmark(self) -> Dict[str, Any]:
        """Calls POST /api/models/test_stop."""
        return self.request("POST", "/api/models/test_stop")

    def stream_benchmark(
        self,
        prompt: str,
        timeout: float = 120.0,
        poll_interval: float = 0.25,
        on_token: Optional[Callable[[str], None]] = None,
        on_progress: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> BenchmarkResult:
        """
        Executes a real-time inference benchmark test:
        1. Ensures worker is in idle state
        2. Triggers POST /api/models/test_benchmark
        3. Polls GET /api/models/test_status/{test_id} in real time
        4. Yields/invokes `on_token` callback for each new token chunk received
        5. Collects and parses hardware and generation speed metrics
        6. Returns structured BenchmarkResult
        """
        w_status = self.get_worker_status()
        if w_status.get("llm_status") == "busy":
            self.wait_for_worker_idle(timeout=timeout)

        test_id = self.trigger_benchmark(prompt)
        start_time = time.time()
        last_length = 0
        final_state = "unknown"
        final_output = ""
        final_stats: Dict[str, Any] = {}

        while time.time() - start_time < timeout:
            status_data = self.get_benchmark_status(test_id)
            state = status_data.get("state", "unknown")
            output = status_data.get("output", "")
            stats = status_data.get("stats", {})

            # Stream delta tokens
            if len(output) > last_length:
                delta = output[last_length:]
                last_length = len(output)
                if on_token:
                    on_token(delta)

            if on_progress:
                on_progress(state, stats)

            final_state = state
            final_output = output
            final_stats = stats

            if state in ("complete", "stopped"):
                break
            if state == "error":
                raise RuntimeError(f"Benchmark error encountered: {output}")

            time.sleep(poll_interval)

        duration = time.time() - start_time

        # If stats not fully populated, check health llm_stats as fallback
        if not final_stats.get("eval_speed"):
            try:
                h = self.get_health()
                llm_st = h.get("llm_stats", {})
                if llm_st:
                    final_stats.update(llm_st)
            except Exception:
                pass

        return BenchmarkResult(
            test_id=test_id,
            state=final_state,
            output_text=final_output,
            duration_seconds=duration,
            prompt_tokens=int(final_stats.get("prompt_tokens", 0)),
            prompt_speed=float(final_stats.get("prompt_speed", 0.0)),
            eval_tokens=int(final_stats.get("eval_tokens", 0)),
            eval_speed=float(final_stats.get("eval_speed", 0.0)),
            total_tokens=int(final_stats.get("total_tokens", 0)),
            kv_cache_reused=int(final_stats.get("kv_cache_reused", 0)),
            tokenization_time_ms=float(final_stats.get("tokenization_time_ms", 0.0)),
            generation_time_ms=float(final_stats.get("generation_time_ms", 0.0)),
            hw_telemetry=final_stats.get("hw_telemetry", {}),
            raw_stats=final_stats,
        )

    # ==========================================
    # Job Loop Studio Endpoints
    # ==========================================

    def get_job_categories(self) -> List[str]:
        """Calls GET /api/jobs/categories."""
        res = self.request("GET", "/api/jobs/categories")
        return res.get("categories", [])

    def get_jobs(self, category: str) -> List[Dict[str, Any]]:
        """Calls GET /api/jobs/{category}."""
        res = self.request("GET", f"/api/jobs/{category}")
        return res.get("jobs", [])

    def inject_job(self, category: str, job_name: str) -> Dict[str, Any]:
        """Calls POST /api/jobs/inject/run."""
        return self.request(
            "POST",
            "/api/jobs/inject/run",
            data={"category": category, "job_name": job_name},
            timeout=90.0,
        )

    def list_job_outputs(self) -> List[Dict[str, Any]]:
        """Calls GET /api/jobs/outputs/list."""
        res = self.request("GET", "/api/jobs/outputs/list")
        return res.get("outputs", [])

    def get_job_output(self, filename: str) -> Dict[str, Any]:
        """Calls GET /api/jobs/outputs/file/{filename}."""
        return self.request("GET", f"/api/jobs/outputs/file/{filename}")

    def inject_and_await_job(
        self,
        category: str,
        job_name: str,
        timeout: float = 90.0,
        poll_interval: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Injects a job via API and waits for the model worker to execute it and return to idle.
        Returns the output file contents and execution metadata.
        """
        # Ensure worker is idle before injecting
        w_status = self.get_worker_status()
        if w_status.get("llm_status") == "busy":
            self.wait_for_worker_idle(timeout=timeout)

        # Snapshot current output files before injection
        pre_outputs = {o["filename"]: o.get("mtime", 0) for o in self.list_job_outputs()}

        # Inject job
        inject_res = self.inject_job(category, job_name)

        # Wait for worker state transition (idle -> busy -> idle)
        start_time = time.time()
        seen_busy = False

        while time.time() - start_time < timeout:
            status = self.get_worker_status()
            llm_st = status.get("llm_status", "idle")

            if llm_st == "busy":
                seen_busy = True
            elif seen_busy and llm_st == "idle":
                # Worker finished!
                break

            time.sleep(poll_interval)

        # Retrieve new or modified output file
        post_outputs = self.list_job_outputs()
        newest_file = None
        for o in post_outputs:
            fname = o["filename"]
            if fname not in pre_outputs or o.get("mtime", 0) > pre_outputs.get(fname, 0):
                newest_file = fname
                break

        if not newest_file and post_outputs:
            newest_file = post_outputs[0]["filename"]

        content = ""
        if newest_file:
            out_res = self.get_job_output(newest_file)
            content = out_res.get("content", "")

        return {
            "injection": inject_res,
            "output_file": newest_file,
            "content": content,
            "duration": time.time() - start_time,
        }

    # ==========================================
    # Layer 2 Delta Working Memory Endpoints
    # ==========================================

    def get_delta_blocks(self) -> List[Dict[str, Any]]:
        """Calls GET /api/deltas/blocks."""
        return self.request("GET", "/api/deltas/blocks")

    def compile_deltas(self) -> Dict[str, Any]:
        """Calls POST /api/deltas/compile."""
        return self.request("POST", "/api/deltas/compile")

    def update_delta(
        self,
        block_id_or_file: str,
        content: str,
        recompile: bool = True,
    ) -> Dict[str, Any]:
        """Calls POST /api/deltas/update."""
        return self.request(
            "POST",
            "/api/deltas/update",
            data={
                "block_id": block_id_or_file,
                "content": content,
                "recompile": recompile,
            },
        )

    def get_delta_manifest(self) -> Dict[str, Any]:
        """Calls GET /api/deltas/manifest."""
        return self.request("GET", "/api/deltas/manifest")

    # ==========================================
    # System Configuration Endpoints
    # ==========================================

    def get_active_config(self) -> Dict[str, Any]:
        """Calls GET /api/config/active."""
        return self.request("GET", "/api/config/active")

    def get_presets(self) -> Dict[str, Any]:
        """Calls GET /api/config/presets."""
        return self.request("GET", "/api/config/presets")
