import os
import sys
import threading
import subprocess
import json
import time
import datetime
import shutil
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path

from services.logger import logger
import core.state as state

class ProxyController:
    """Manages the anthropic proxy process."""
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self.proxy_script = "anthropic_proxy.py"
        self.port = 8001

    def get_status(self):
        with self._lock:
            running = self.process is not None and self.process.poll() is None

            # Determine port from port.txt + 1
            try:
                if os.path.exists("port.txt"):
                    with open("port.txt", "r") as f:
                        val = f.read().strip()
                        if val.isdigit():
                            self.port = int(val) + 1
            except: pass

            return {
                "running": running,
                "pid": self.process.pid if running else None,
                "port": self.port
            }

    def start_proxy(self):
        with self._lock:
            if self.process is not None and self.process.poll() is None:
                return {"success": False, "message": "Proxy already running.", "port": self.port}

            try:
                # Start the proxy process
                self.process = subprocess.Popen(
                    [sys.executable, "-u", self.proxy_script],
                    cwd=os.getcwd(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                # Start threads to forward output to logger
                threading.Thread(target=self._monitor_output, args=(self.process.stdout, "ProxyOut"), daemon=True).start()
                threading.Thread(target=self._monitor_output, args=(self.process.stderr, "ProxyErr"), daemon=True).start()

                # Determine port
                try:
                    if os.path.exists("port.txt"):
                        with open("port.txt", "r") as f:
                            val = f.read().strip()
                            if val.isdigit():
                                self.port = int(val) + 1
                except: pass

                return {"success": True, "message": "Proxy started.", "port": self.port}
            except Exception as e:
                return {"success": False, "message": f"Failed to start proxy: {e}"}

    def stop_proxy(self):
        with self._lock:
            if self.process is None or self.process.poll() is not None:
                return {"success": False, "message": "Proxy not running."}

            try:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()

                self.process = None
                return {"success": True, "message": "Proxy stopped."}
            except Exception as e:
                return {"success": False, "message": f"Error stopping proxy: {e}"}

    def _monitor_output(self, stream, source):
        """Reads output from the subprocess and logs it."""
        try:
            for line in iter(stream.readline, ''):
                if line:
                    clean_line = line.strip()
                    if state.main_loop and clean_line:
                        asyncio.run_coroutine_threadsafe(logger.emit("Info", clean_line, source), state.main_loop)
                    elif clean_line:
                        print(f"[{source}] {clean_line}")
        except Exception:
            pass
        finally:
            stream.close()

proxy_controller = ProxyController()


# =====================================================================
# Claude Code Orchestrator
# ---------------------------------------------------------------------
# Self-contained, additive orchestration layer for the Claude Code GUI
# module. Stores per-run metadata, transcripts, and git snapshots under
# claude_runs/. Does NOT touch any other LYRN subsystem.
# =====================================================================

class ClaudeRunManager:
    """Tracks Claude Code runs: lifecycle, transcript, git diff snapshot."""

    STORE_DIR = Path("claude_runs")
    VALID_MODES = ("oneshot", "inspect", "patch")

    def __init__(self):
        self.STORE_DIR.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._index_path = self.STORE_DIR / "index.json"
        self._procs: Dict[str, subprocess.Popen] = {}
        self._log_handles: Dict[str, Any] = {}
        self.runs: Dict[str, Dict[str, Any]] = self._load_index()
        # Any runs left in 'running' state from a prior server process are
        # orphaned -- the subprocess is gone. Mark them so the UI is honest.
        for run in self.runs.values():
            if run.get("status") == "running":
                run["status"] = "interrupted"
                run["ended_at"] = run.get("ended_at") or time.time()
        self._save_index()

    # ---------- Claude CLI resolution ----------
    def _resolve_claude_binary(self) -> Optional[str]:
        """Resolve a concrete claude executable path for non-interactive
        backend execution. Avoids relying on shell init files."""
        env = os.environ
        explicit = (env.get("LYRN_CLAUDE_BIN") or env.get("CLAUDE_BIN") or "").strip()
        candidates: List[Path] = []
        if explicit:
            candidates.append(Path(explicit).expanduser())

        via_path = shutil.which("claude")
        if via_path:
            candidates.append(Path(via_path))

        home = Path(env.get("HOME", "~")).expanduser()
        candidates += [
            home / ".local/bin/claude",
            home / ".npm-global/bin/claude",
            Path("/usr/local/bin/claude"),
            Path("/opt/homebrew/bin/claude"),
        ]

        for c in candidates:
            try:
                p = c.expanduser().resolve()
                if p.exists() and os.access(p, os.X_OK):
                    return str(p)
            except Exception:
                continue
        return None

    def _claude_env(self) -> Dict[str, str]:
        env = os.environ.copy()
        claude_bin = self._resolve_claude_binary()
        if claude_bin:
            env["LYRN_CLAUDE_BIN"] = claude_bin
            bin_dir = str(Path(claude_bin).parent)
            path_val = env.get("PATH", "")
            if bin_dir not in path_val.split(os.pathsep):
                env["PATH"] = bin_dir + (os.pathsep + path_val if path_val else "")

        # Set Anthropic Proxy Environment Variables
        # Attempt to read port from port.txt + 1
        default_port = 8001
        try:
            if os.path.exists("port.txt"):
                with open("port.txt", "r") as f:
                    val = f.read().strip()
                    if val.isdigit():
                        default_port = int(val) + 1
        except:
            pass

        host = os.environ.get("LCC_HOST", "127.0.0.1")
        port = os.environ.get("LCC_PORT", str(default_port))
        base_url = f"http://{host}:{port}"

        env["ANTHROPIC_BASE_URL"] = base_url
        env["ANTHROPIC_AUTH_TOKEN"] = "lyrn"
        env["ANTHROPIC_API_KEY"] = ""
        env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"

        return env

    # ---------- Persistence ----------
    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        if self._index_path.exists():
            try:
                return json.loads(self._index_path.read_text())
            except Exception:
                return {}
        return {}

    def _save_index(self):
        try:
            self._index_path.write_text(json.dumps(self.runs, indent=2))
        except Exception as e:
            print(f"[ClaudeRun] Failed to save index: {e}")

    # ---------- Git helpers (best-effort, no-op if not a git repo) ----------
    def _git(self, cwd: str, *args: str, capture: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args], cwd=cwd, capture_output=capture, text=True, timeout=30
        )

    def _is_git_repo(self, cwd: str) -> bool:
        try:
            r = self._git(cwd, "rev-parse", "--is-inside-work-tree")
            return r.returncode == 0 and r.stdout.strip() == "true"
        except Exception:
            return False

    def _snapshot_baseline(self, cwd: str) -> Optional[str]:
        """Use 'git stash create' to capture the working tree as a commit
        object without altering anything. Returns the SHA, or None."""
        if not self._is_git_repo(cwd):
            return None
        try:
            # Make sure untracked are included by adding them to a temp index.
            # Simpler: stash create only captures tracked. We accept that.
            r = self._git(cwd, "stash", "create")
            sha = r.stdout.strip()
            return sha or self._git(cwd, "rev-parse", "HEAD").stdout.strip()
        except Exception as e:
            print(f"[ClaudeRun] snapshot error: {e}")
            return None

    def _compute_diff(self, cwd: str, baseline_sha: str) -> Dict[str, Any]:
        """Diff working tree against the baseline SHA."""
        try:
            raw = self._git(cwd, "diff", "--no-color", baseline_sha).stdout
            stat = self._git(cwd, "diff", "--numstat", baseline_sha).stdout
            files = []
            for line in stat.strip().splitlines():
                parts = line.split("\t")
                if len(parts) == 3:
                    add, delete, path = parts
                    files.append({
                        "path": path,
                        "additions": int(add) if add.isdigit() else 0,
                        "deletions": int(delete) if delete.isdigit() else 0,
                    })
            return {"raw": raw, "files": files}
        except Exception as e:
            return {"raw": "", "files": [], "error": str(e)}

    def _revert_to_baseline(self, cwd: str, baseline_sha: str) -> bool:
        """Restore working tree to the baseline snapshot (destructive)."""
        try:
            # Hard reset tracked files to the snapshot tree.
            r = self._git(cwd, "checkout", baseline_sha, "--", ".")
            return r.returncode == 0
        except Exception as e:
            print(f"[ClaudeRun] revert error: {e}")
            return False

    # ---------- Validation / argv (single source of truth) ----------
    def resolve_cwd(self, cwd: Optional[str]) -> Dict[str, Any]:
        """Validate a user-supplied cwd. Returns a result dict with either
        ``path`` (resolved) or ``error`` (human-readable)."""
        raw = (cwd or "").strip()
        if not raw:
            return {"ok": False, "error": "Working directory is required."}
        try:
            p = Path(raw).expanduser()
            if not p.exists():
                return {"ok": False, "error": f"Path does not exist: {raw}"}
            if not p.is_dir():
                return {"ok": False, "error": f"Not a directory: {raw}"}
            resolved = str(p.resolve())
        except Exception as e:
            return {"ok": False, "error": f"Invalid path: {e}"}
        return {
            "ok": True,
            "path": resolved,
            "is_git_repo": self._is_git_repo(resolved),
        }

    def build_argv(self, payload: Dict[str, Any]) -> List[str]:
        """Backend is the source of truth for the actual command. The
        frontend preview is informational only."""
        mode = payload.get("mode") or "oneshot"
        argv: List[str] = ["claude"]
        if mode == "oneshot":
            argv.append("--print")
        elif mode == "inspect":
            argv.append("--read-only")
        elif mode == "patch":
            argv.append("--patch-only")

        if payload.get("model"):
            argv += ["--model", str(payload["model"])]
        if payload.get("effort"):
            argv += ["--effort", str(payload["effort"])]
        if payload.get("system_prompt"):
            argv += ["--system-prompt", str(payload["system_prompt"])]
        if payload.get("auto"):
            argv.append("--enable-auto-mode")
        if payload.get("perms"):
            argv.append("--dangerously-skip-permissions")

        task = (payload.get("task") or "").strip()
        if task:
            argv.append(task)
        return argv

    def preview(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        argv = self.build_argv(payload)
        cwd_check = self.resolve_cwd(payload.get("cwd"))
        return {
            "argv": argv,
            "cwd": cwd_check,
            "claude_bin": self._resolve_claude_binary(),
        }

    # ---------- Auth ----------
    def auth_status(self) -> Dict[str, Any]:
        claude_bin = self._resolve_claude_binary()
        if not claude_bin:
            return {
                "available": False,
                "authenticated": False,
                "raw": "claude CLI not installed or not visible in backend PATH",
                "claude_bin": None,
            }
        try:
            r = subprocess.run(
                [claude_bin, "auth", "status"],
                capture_output=True, text=True, timeout=10,
                env=self._claude_env(),
            )
            output = (r.stdout + r.stderr).strip()
            low = output.lower()
            authed = r.returncode == 0 and any(
                marker in low for marker in (
                    "logged in", "authenticated", "account:", "you are signed in",
                )
            )
            return {
                "available": True,
                "authenticated": authed,
                "raw": output,
                "claude_bin": claude_bin,
            }
        except FileNotFoundError:
            return {
                "available": False,
                "authenticated": False,
                "raw": "claude CLI not installed",
                "claude_bin": claude_bin,
            }
        except subprocess.TimeoutExpired:
            return {
                "available": True,
                "authenticated": False,
                "raw": "auth status timed out",
                "claude_bin": claude_bin,
            }
        except Exception as e:
            return {
                "available": False,
                "authenticated": False,
                "raw": str(e),
                "claude_bin": claude_bin,
            }

    # ---------- Run lifecycle ----------
    def list_runs(self) -> List[Dict[str, Any]]:
        with self._lock:
            self._refresh_statuses()
            return sorted(
                [self._summary(r) for r in self.runs.values()],
                key=lambda r: r.get("started_at", 0),
                reverse=True,
            )

    def _summary(self, run: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": run["id"],
            "label": run.get("label", ""),
            "mode": run.get("mode", ""),
            "cwd": run.get("cwd", ""),
            "status": run.get("status", "unknown"),
            "started_at": run.get("started_at", 0),
            "ended_at": run.get("ended_at"),
            "exit_code": run.get("exit_code"),
            "approved": run.get("approved"),
            "has_diff": bool(run.get("baseline_sha")),
        }

    def _refresh_statuses(self):
        for run_id, proc in list(self._procs.items()):
            if proc.poll() is not None:
                run = self.runs.get(run_id)
                if run and run.get("status") == "running":
                    run["status"] = "completed" if proc.returncode == 0 else "failed"
                    run["exit_code"] = proc.returncode
                    run["ended_at"] = time.time()
                    self._save_index()
                self._procs.pop(run_id, None)
                fh = self._log_handles.pop(run_id, None)
                if fh is not None:
                    try: fh.close()
                    except Exception: pass

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            self._refresh_statuses()
            run = self.runs.get(run_id)
            if not run:
                return None
            return dict(run)

    def get_transcript(self, run_id: str) -> str:
        run = self.runs.get(run_id)
        if not run:
            return ""
        path = Path(run.get("transcript_path", ""))
        if path.exists():
            try:
                return path.read_text(errors="replace")
            except Exception:
                return ""
        return ""

    def get_diff(self, run_id: str) -> Dict[str, Any]:
        run = self.runs.get(run_id)
        if not run or not run.get("baseline_sha"):
            return {"raw": "", "files": [], "error": "no baseline snapshot"}
        return self._compute_diff(run["cwd"], run["baseline_sha"])

    def approve(self, run_id: str) -> Dict[str, Any]:
        with self._lock:
            run = self.runs.get(run_id)
            if not run:
                return {"success": False, "message": "run not found"}
            run["approved"] = True
            self._save_index()
            return {"success": True}

    def reject(self, run_id: str) -> Dict[str, Any]:
        with self._lock:
            run = self.runs.get(run_id)
            if not run:
                return {"success": False, "message": "run not found"}
            sha = run.get("baseline_sha")
            if not sha:
                return {"success": False, "message": "no baseline to revert to"}
            ok = self._revert_to_baseline(run["cwd"], sha)
            run["approved"] = False if ok else None
            run["reverted"] = ok
            self._save_index()
            return {"success": ok}

    def delete_run(self, run_id: str) -> Dict[str, Any]:
        with self._lock:
            self._refresh_statuses()
            existing = self.runs.get(run_id)
            if not existing:
                return {"success": False, "message": "run not found"}
            if existing.get("status") == "running":
                return {"success": False, "message": "cannot delete a running run"}
            self.runs.pop(run_id, None)
            try:
                d = self.STORE_DIR / run_id
                if d.exists():
                    shutil.rmtree(d)
            except Exception:
                pass
            self._save_index()
            return {"success": True}

    def start_run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        mode = payload.get("mode") or "oneshot"
        if mode not in self.VALID_MODES:
            return {"success": False, "message": f"unsupported mode: {mode}"}

        cwd_check = self.resolve_cwd(payload.get("cwd"))
        if not cwd_check["ok"]:
            return {"success": False, "message": cwd_check["error"]}
        cwd_resolved = cwd_check["path"]

        task = (payload.get("task") or "").strip()
        if mode == "oneshot" and not task:
            return {"success": False, "message": "Task is required for one-shot runs."}

        argv = self.build_argv({**payload, "mode": mode, "task": task})
        claude_bin = self._resolve_claude_binary()
        if not claude_bin:
            return {
                "success": False,
                "message": (
                    "claude CLI not found. Set LYRN_CLAUDE_BIN/CLAUDE_BIN or "
                    f"ensure PATH includes claude. PATH={os.environ.get('PATH','')}"
                ),
            }
        argv[0] = claude_bin

        run_id = "run_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + os.urandom(2).hex()
        run_dir = self.STORE_DIR / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        transcript_path = run_dir / "transcript.log"

        baseline = self._snapshot_baseline(cwd_resolved)

        try:
            log_fh = open(transcript_path, "w", buffering=1)
            proc = subprocess.Popen(
                argv,
                cwd=cwd_resolved,
                stdout=log_fh,
                stderr=subprocess.STDOUT,
                text=True,
                env=self._claude_env(),
            )
        except FileNotFoundError:
            try: log_fh.close()
            except Exception: pass
            return {"success": False, "message": "claude CLI not found in backend runtime environment"}
        except Exception as e:
            try: log_fh.close()
            except Exception: pass
            return {"success": False, "message": f"failed to start: {e}"}

        run = {
            "id": run_id,
            "label": (payload.get("label") or "").strip(),
            "mode": mode,
            "cwd": cwd_resolved,
            "argv": argv,
            "task": task,
            "baseline_sha": baseline,
            "transcript_path": str(transcript_path),
            "status": "running",
            "started_at": time.time(),
            "ended_at": None,
            "exit_code": None,
            "approved": None,
            "reverted": False,
            "pid": proc.pid,
        }

        with self._lock:
            self.runs[run_id] = run
            self._procs[run_id] = proc
            self._log_handles[run_id] = log_fh
            self._save_index()

        return {"success": True, "run": self._summary(run), "argv": argv}


claude_run_manager = ClaudeRunManager()
