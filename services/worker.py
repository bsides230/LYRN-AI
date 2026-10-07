import os
import sys
import threading
import subprocess
import re
from pathlib import Path
from typing import Optional
import asyncio

import core.state as state
from services.logger import logger

class WorkerController:
    """Manages the headless worker process."""
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self.worker_script = "model_runner.py"

    def get_status(self):
        with self._lock:
            running = self.process is not None and self.process.poll() is None

            # Check LLM status flag if running
            llm_status = "unknown"
            error_msg = None

            if running:
                try:
                    flag_path = Path("global_flags/llm_status.txt")
                    if flag_path.exists():
                        llm_status = flag_path.read_text().strip()
                except Exception:
                    pass
            else:
                llm_status = "stopped"

            # Check for error file if status is error
            if llm_status == "error":
                 try:
                    err_path = Path("global_flags/last_error.txt")
                    if err_path.exists():
                        error_msg = err_path.read_text().strip()
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

            try:
                # Start the worker process
                self.process = subprocess.Popen(
                    [sys.executable, "-u", self.worker_script],
                    cwd=os.getcwd(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                # Start threads to forward output to logger
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
        """Reads output from the subprocess and logs it."""
        try:
            for line in iter(stream.readline, ''):
                if line:
                    clean_line = line.strip()

                    # Parse extended stats from llama.cpp logs
                    try:
                        # KV Cache
                        kv_match = re.search(r'(\d+)\s+prefix-match hit', clean_line)
                        if kv_match:
                            state.extended_llm_stats["kv_cache_reused"] = int(kv_match.group(1))

                        # Prompt Eval
                        prompt_match = re.search(r'prompt eval time\s*=\s*([\d.]+)\s*ms\s*/\s*(\d+)\s*tokens.*?([\d.]+)\s*ms per token', clean_line)
                        if prompt_match:
                            ms = float(prompt_match.group(1))
                            tokens = int(prompt_match.group(2))
                            ms_per_tok = float(prompt_match.group(3))
                            state.extended_llm_stats["tokenization_time_ms"] = ms
                            state.extended_llm_stats["prompt_tokens"] = tokens
                            state.extended_llm_stats["prompt_speed"] = 1000.0 / ms_per_tok if ms_per_tok > 0 else 0.0

                        # Eval (Generation)
                        eval_match = re.search(r'eval time\s*=\s*([\d.]+)\s*ms\s*/\s*(\d+)\s*runs.*?([\d.]+)\s*ms per token', clean_line)
                        if eval_match:
                            ms = float(eval_match.group(1))
                            tokens = int(eval_match.group(2))
                            ms_per_tok = float(eval_match.group(3))
                            state.extended_llm_stats["generation_time_ms"] = ms
                            state.extended_llm_stats["eval_tokens"] = tokens
                            state.extended_llm_stats["eval_speed"] = 1000.0 / ms_per_tok if ms_per_tok > 0 else 0.0

                        # Load Time
                        load_match = re.search(r'load time\s*=\s*([\d.]+)\s*ms', clean_line)
                        if load_match:
                            state.extended_llm_stats["load_time"] = float(load_match.group(1))

                        # Total Time
                        total_match = re.search(r'total time\s*=\s*([\d.]+)\s*ms', clean_line)
                        if total_match:
                            state.extended_llm_stats["total_time"] = float(total_match.group(1)) / 1000.0 # Convert to seconds

                        # Update totals
                        state.extended_llm_stats["total_tokens"] = state.extended_llm_stats["prompt_tokens"] + state.extended_llm_stats["eval_tokens"]

                    except Exception:
                        pass

                    if state.main_loop and clean_line:
                        asyncio.run_coroutine_threadsafe(logger.emit("Info", clean_line, source), state.main_loop)
                    elif clean_line:
                        print(f"[{source}] {clean_line}")
        except Exception:
            pass
        finally:
            stream.close()

worker_controller = WorkerController()
