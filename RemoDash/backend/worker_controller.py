import os
import sys
import subprocess
import threading
import re
import asyncio
from pathlib import Path
from typing import Optional
from backend.logger import logger

# Shared LLM Stats
extended_llm_stats = {
    "kv_cache_reused": 0,
    "prompt_tokens": 0,
    "prompt_speed": 0.0,
    "eval_tokens": 0,
    "eval_speed": 0.0,
    "total_tokens": 0,
    "load_time": 0.0,
    "total_time": 0.0,
    "tokenization_time_ms": 0.0,
    "generation_time_ms": 0.0
}

class WorkerController:
    """Manages the headless worker process."""
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        # Worker script is in root (or wherever start.bat sets CWD to, but relative to that)
        # If server.py is in root, and we run from app dir, we need to find worker.
        # Assuming we are running from app dir (e.g. LYRN_v5/), worker is in parent.
        # But if running from root, worker is in current.
        # Let's try both.
        self.worker_script = "headless_lyrn_worker.py"

    def _resolve_worker_script(self):
        if Path(self.worker_script).exists():
            return self.worker_script
        if Path("..", self.worker_script).exists():
            return str(Path("..", self.worker_script))
        return self.worker_script

    def get_status(self):
        with self._lock:
            running = self.process is not None and self.process.poll() is None
            llm_status = "unknown"
            error_msg = None

            if running:
                try:
                    flag_path = Path("global_flags/llm_status.txt")
                    if flag_path.exists():
                        llm_status = flag_path.read_text().strip()
                except Exception: pass
            else:
                llm_status = "stopped"

            if llm_status == "error":
                 try:
                    err_path = Path("global_flags/last_error.txt")
                    if err_path.exists(): error_msg = err_path.read_text().strip()
                 except: pass

            return {
                "running": running,
                "pid": self.process.pid if running else None,
                "llm_status": llm_status,
                "error_message": error_msg
            }

    def start_worker(self):
        with self._lock:
            if self.process is not None and self.process.poll() is None:
                return {"success": False, "message": "Worker already running."}

            script = self._resolve_worker_script()
            try:
                self.process = subprocess.Popen(
                    [sys.executable, "-u", script],
                    cwd=os.getcwd(), # Use current app dir as CWD for worker
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                threading.Thread(target=self._monitor_output, args=(self.process.stdout, "WorkerOut"), daemon=True).start()
                threading.Thread(target=self._monitor_output, args=(self.process.stderr, "WorkerErr"), daemon=True).start()
                return {"success": True, "message": "Worker started."}
            except Exception as e:
                return {"success": False, "message": f"Failed to start worker: {e}"}

    def stop_worker(self):
        with self._lock:
            if self.process is None or self.process.poll() is not None:
                return {"success": False, "message": "Worker not running."}
            try:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                self.process = None
                return {"success": True, "message": "Worker stopped."}
            except Exception as e:
                return {"success": False, "message": f"Error stopping worker: {e}"}

    def _monitor_output(self, stream, source):
        try:
            for line in iter(stream.readline, ''):
                if line:
                    clean_line = line.strip()
                    self._parse_stats(clean_line)

                    # Log to backend logger
                    try:
                        loop = asyncio.get_running_loop()
                        asyncio.run_coroutine_threadsafe(logger.emit("Info", clean_line, source), loop)
                    except RuntimeError:
                        # No running loop (startup/shutdown)
                        print(f"[{source}] {clean_line}")
        except Exception: pass
        finally: stream.close()

    def _parse_stats(self, line):
        try:
            # KV Cache
            kv_match = re.search(r'(\d+)\s+prefix-match hit', line)
            if kv_match: extended_llm_stats["kv_cache_reused"] = int(kv_match.group(1))

            # Prompt Eval
            prompt_match = re.search(r'prompt eval time\s*=\s*([\d.]+)\s*ms\s*/\s*(\d+)\s*tokens.*?([\d.]+)\s*ms per token', line)
            if prompt_match:
                ms = float(prompt_match.group(1))
                ms_per_tok = float(prompt_match.group(3))
                extended_llm_stats["tokenization_time_ms"] = ms
                extended_llm_stats["prompt_tokens"] = int(prompt_match.group(2))
                extended_llm_stats["prompt_speed"] = 1000.0 / ms_per_tok if ms_per_tok > 0 else 0.0

            # Eval
            eval_match = re.search(r'eval time\s*=\s*([\d.]+)\s*ms\s*/\s*(\d+)\s*runs.*?([\d.]+)\s*ms per token', line)
            if eval_match:
                ms = float(eval_match.group(1))
                ms_per_tok = float(eval_match.group(3))
                extended_llm_stats["generation_time_ms"] = ms
                extended_llm_stats["eval_tokens"] = int(eval_match.group(2))
                extended_llm_stats["eval_speed"] = 1000.0 / ms_per_tok if ms_per_tok > 0 else 0.0

            # Load Time
            load_match = re.search(r'load time\s*=\s*([\d.]+)\s*ms', line)
            if load_match: extended_llm_stats["load_time"] = float(load_match.group(1))

            # Total Time
            total_match = re.search(r'total time\s*=\s*([\d.]+)\s*ms', line)
            if total_match: extended_llm_stats["total_time"] = float(total_match.group(1)) / 1000.0

            extended_llm_stats["total_tokens"] = extended_llm_stats["prompt_tokens"] + extended_llm_stats["eval_tokens"]
        except: pass

worker_controller = WorkerController()
