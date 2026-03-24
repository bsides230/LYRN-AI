"""
debug_live.py — Live end-to-end debug runner for the LYRN chat flow.

Runs the FULL real pipeline using the actual configured model (no mocking).
Every process in the chain is captured and written to a timestamped
debug report in docs/debug_reports/.

Usage (from repo root):
    python tests/debug_live.py            # uses preset 1 from settings.json
    python tests/debug_live.py --preset 2 # uses a different preset

What it does:
  1. Loads the chosen model_preset from settings.json and temporarily
     applies it to the "active" config so model_runner.py picks it up.
     The original active config is restored when the script exits.
  2. Starts model_runner.py and waits for the model to finish loading.
  3. For each test prompt, runs the full chain:
       job_input.json  →  route_chat.py  →  chat_watcher_bg.py (foreground)
                       →  chat_trigger.txt  →  model_runner  →  output
  4. Captures stdout/stderr from every process.
  5. Writes docs/debug_reports/debug_TIMESTAMP.md with all results.

The watcher is run directly (foreground, captured) instead of via
spawn_chat_watcher.py so all debug output is visible in the report.
"""

import sys
import os
import json
import time
import signal
import threading
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
REPO_ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_FILE   = os.path.join(REPO_ROOT, "settings.json")
MODEL_RUNNER    = os.path.join(REPO_ROOT, "model_runner.py")
WATCHER_SCRIPT  = os.path.join(REPO_ROOT, "automation", "job_scripts", "chat_watcher_bg.py")
ROUTE_SCRIPT    = os.path.join(REPO_ROOT, "automation", "job_scripts", "route_chat.py")
JOB_INPUT       = os.path.join(REPO_ROOT, "jobs", "job_input.json")
CHAT_TRIGGER    = os.path.join(REPO_ROOT, "chat_trigger.txt")
LLM_STATUS      = os.path.join(REPO_ROOT, "global_flags", "llm_status.txt")
STREAM_BUFFER   = os.path.join(REPO_ROOT, "global_flags", "chat_stream_buffer.txt")
FINAL_FLAG      = os.path.join(REPO_ROOT, "global_flags", "final_output_mode.txt")
LOCK_FILE       = os.path.join(REPO_ROOT, "global_flags", "chat_processing.txt")
RAW_OUTPUT      = os.path.join(REPO_ROOT, "jobs", "job_raw_output.txt")
OUTPUT_LOG      = os.path.join(REPO_ROOT, "global_flags", "output_log.jsonl")
REPORT_DIR      = os.path.join(REPO_ROOT, "docs", "debug_reports")

# Which preset to use (can be overridden via --preset N on the command line)
DEFAULT_PRESET  = "1"

MODEL_LOAD_TIMEOUT  = 300   # seconds to wait for model to load
GENERATION_TIMEOUT  = 300   # seconds to wait for a generation to complete
STATUS_POLL         = 0.5   # seconds between status checks

# Test prompts to run through the pipeline
TEST_PROMPTS = [
    "Say hello and confirm you are working correctly. Keep it brief.",
    "What is 2 + 2? Answer directly.",
    "Explain what the ##AF: FINAL_OUTPUT## marker does in one sentence.",
]


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def ts():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def section(title):
    bar = "=" * 60
    return f"\n{bar}\n  {title}\n{bar}\n"


def read_status():
    try:
        return Path(LLM_STATUS).read_text(encoding="utf-8").strip()
    except Exception:
        return "unknown"


def wait_for_status(target_statuses, timeout, label=""):
    deadline = time.time() + timeout
    while time.time() < deadline:
        s = read_status()
        if s in target_statuses:
            return s
        time.sleep(STATUS_POLL)
    return None  # timed out


def clean_flags():
    """Remove runtime flag files so each test starts clean."""
    for path in [STREAM_BUFFER, FINAL_FLAG, LOCK_FILE, RAW_OUTPUT]:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass


def write_job_input(user_message):
    os.makedirs(os.path.dirname(JOB_INPUT), exist_ok=True)
    payload = {
        "user_message": user_message,
        "source": "debug_live",
        "timestamp": datetime.now().isoformat(),
    }
    Path(JOB_INPUT).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def kick_model_runner(user_message):
    """Write job_input.json and chat_trigger.txt to trigger model_runner."""
    write_job_input(user_message)
    Path(CHAT_TRIGGER).write_text(JOB_INPUT, encoding="utf-8")


def run_route_chat():
    """Run route_chat.py and return (stdout, stderr, returncode)."""
    result = subprocess.run(
        [sys.executable, ROUTE_SCRIPT],
        capture_output=True, text=True, timeout=15,
        cwd=REPO_ROOT,
        env={**os.environ, "PYTHONPATH": REPO_ROOT},
    )
    return result.stdout, result.stderr, result.returncode


# ---------------------------------------------------------------------------
# Model runner — starts in background, output captured to a rolling buffer
# ---------------------------------------------------------------------------

class ModelRunnerProcess:
    def __init__(self):
        self.proc      = None
        self.log_lines = []
        self._lock     = threading.Lock()
        self._reader   = None

    def start(self):
        self.proc = subprocess.Popen(
            [sys.executable, MODEL_RUNNER],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=REPO_ROOT,
        )
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        print(f"[{ts()}] model_runner.py started (PID {self.proc.pid})")

    def _read_loop(self):
        for line in self.proc.stdout:
            line = line.rstrip("\n")
            with self._lock:
                self.log_lines.append(f"[runner] {line}")

    def get_log(self):
        with self._lock:
            return list(self.log_lines)

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self._reader:
            self._reader.join(timeout=3)
        print(f"[{ts()}] model_runner.py stopped.")


# ---------------------------------------------------------------------------
# Single test run
# ---------------------------------------------------------------------------

def run_test(runner: ModelRunnerProcess, prompt: str, index: int) -> dict:
    """
    Run one full cycle of the pipeline for the given prompt.
    Returns a dict with all captured data for the report.
    """
    result = {
        "index":        index,
        "prompt":       prompt,
        "started_at":   ts(),
        "route_stdout": "",
        "route_stderr": "",
        "route_rc":     None,
        "watcher_stdout": "",
        "watcher_stderr": "",
        "watcher_rc":   None,
        "raw_output":   "",
        "stream_buffer": "",
        "chat_files":   [],
        "status_at_end": "",
        "elapsed_s":    0.0,
        "error":        "",
    }

    t0 = time.time()
    print(f"\n[{ts()}] ── Test {index}: {prompt[:60]!r}")

    # Ensure model is idle before starting
    status = wait_for_status({"idle"}, timeout=10)
    if status != "idle":
        result["error"] = f"Model not idle at test start (status={read_status()!r})"
        return result

    clean_flags()

    # Step A: Write job_input.json
    write_job_input(prompt)
    Path(LOCK_FILE).write_text("processing", encoding="utf-8")
    print(f"[{ts()}]   job_input.json written")

    # Step B: Run route_chat.py
    print(f"[{ts()}]   Running route_chat.py...")
    try:
        r_out, r_err, r_rc = run_route_chat()
    except subprocess.TimeoutExpired:
        result["error"] = "route_chat.py timed out"
        return result
    result["route_stdout"] = r_out
    result["route_stderr"] = r_err
    result["route_rc"]     = r_rc
    print(f"[{ts()}]   route_chat.py → rc={r_rc}")

    if r_rc != 0:
        result["error"] = f"route_chat.py exited {r_rc}"
        return result

    # Step C: Start watcher in foreground (captured) — BEFORE triggering the model
    print(f"[{ts()}]   Starting chat_watcher_bg.py (foreground capture)...")
    watcher_proc = subprocess.Popen(
        [sys.executable, WATCHER_SCRIPT, REPO_ROOT, prompt],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=REPO_ROOT,
    )

    # Step D: Kick model_runner by writing job_input + chat_trigger
    print(f"[{ts()}]   Writing chat_trigger.txt to kick model_runner...")
    Path(CHAT_TRIGGER).write_text(JOB_INPUT, encoding="utf-8")

    # Step E: Wait for watcher to finish
    print(f"[{ts()}]   Waiting for watcher to complete (timeout={GENERATION_TIMEOUT}s)...")
    try:
        w_out, w_err = watcher_proc.communicate(timeout=GENERATION_TIMEOUT)
    except subprocess.TimeoutExpired:
        watcher_proc.kill()
        w_out, w_err = watcher_proc.communicate()
        result["error"] = "watcher timed out"

    result["watcher_stdout"] = w_out
    result["watcher_stderr"] = w_err
    result["watcher_rc"]     = watcher_proc.returncode
    print(f"[{ts()}]   Watcher finished → rc={watcher_proc.returncode}")

    # Collect final state
    try:
        result["raw_output"] = Path(RAW_OUTPUT).read_text(encoding="utf-8", errors="replace")
    except Exception:
        pass

    try:
        result["stream_buffer"] = Path(STREAM_BUFFER).read_text(encoding="utf-8", errors="replace")
    except Exception:
        pass

    chat_dir = os.path.join(REPO_ROOT, "chat")
    if os.path.isdir(chat_dir):
        result["chat_files"] = sorted(
            [str(p) for p in Path(chat_dir).glob("chat_*.txt")],
            key=os.path.getmtime, reverse=True
        )[:3]

    result["status_at_end"] = read_status()
    result["elapsed_s"]     = round(time.time() - t0, 2)

    print(f"[{ts()}]   Done in {result['elapsed_s']}s. Status={result['status_at_end']}")
    return result


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

def build_report(runner: ModelRunnerProcess, test_results: list, started_at: str,
                 preset_id: str, preset_cfg: dict) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []

    lines.append(f"# LYRN-AI Live Debug Report")
    lines.append(
        f"**Generated:** {now}  |  **Started:** {started_at}  "
        f"|  **Preset:** {preset_id}  |  **Model:** {preset_cfg.get('model_path', 'unknown')}"
    )
    lines.append("")

    # Summary table
    lines.append("## Results Summary")
    lines.append("")
    lines.append("| # | Prompt | RC (route) | RC (watcher) | Elapsed | Marker | Error |")
    lines.append("|---|--------|-----------|-------------|---------|--------|-------|")
    for r in test_results:
        marker = "✓" if r["watcher_stdout"] and "##AF: FINAL_OUTPUT## detected" in r["watcher_stdout"] else "–"
        err    = r["error"][:40] if r["error"] else "—"
        lines.append(
            f"| {r['index']} | {r['prompt'][:40]!r} | {r['route_rc']} "
            f"| {r['watcher_rc']} | {r['elapsed_s']}s | {marker} | {err} |"
        )
    lines.append("")

    # Per-test details
    for r in test_results:
        lines.append(f"---")
        lines.append(f"## Test {r['index']}: {r['prompt']}")
        lines.append(f"**Started:** {r['started_at']}  **Elapsed:** {r['elapsed_s']}s")
        if r["error"]:
            lines.append(f"\n**ERROR:** {r['error']}\n")

        lines.append("\n### route_chat.py output")
        lines.append(f"Return code: `{r['route_rc']}`")
        if r["route_stdout"].strip():
            lines.append("```")
            lines.append(r["route_stdout"].strip())
            lines.append("```")
        if r["route_stderr"].strip():
            lines.append("**stderr:**")
            lines.append("```")
            lines.append(r["route_stderr"].strip())
            lines.append("```")

        lines.append("\n### chat_watcher_bg.py output")
        lines.append(f"Return code: `{r['watcher_rc']}`")
        if r["watcher_stdout"].strip():
            lines.append("```")
            lines.append(r["watcher_stdout"].strip())
            lines.append("```")
        if r["watcher_stderr"].strip():
            lines.append("**stderr:**")
            lines.append("```")
            lines.append(r["watcher_stderr"].strip())
            lines.append("```")

        lines.append("\n### Raw LLM Output")
        if r["raw_output"].strip():
            lines.append("```")
            lines.append(r["raw_output"].strip()[:3000])  # cap at 3000 chars
            if len(r["raw_output"]) > 3000:
                lines.append(f"... [{len(r['raw_output']) - 3000} more chars truncated]")
            lines.append("```")
        else:
            lines.append("_(empty)_")

        lines.append("\n### Stream Buffer (post-marker)")
        if r["stream_buffer"].strip():
            lines.append("```")
            lines.append(r["stream_buffer"].strip()[:1500])
            lines.append("```")
        else:
            lines.append("_(empty — no affordance marker emitted)_")

        lines.append("\n### Chat History Files Written")
        if r["chat_files"]:
            for cf in r["chat_files"]:
                try:
                    content = Path(cf).read_text(encoding="utf-8", errors="replace")
                    lines.append(f"**{os.path.basename(cf)}:**")
                    lines.append("```")
                    lines.append(content.strip()[:1000])
                    lines.append("```")
                except Exception as e:
                    lines.append(f"_(could not read {cf}: {e})_")
        else:
            lines.append("_(none found)_")

        lines.append("")

    # Model runner log
    lines.append("---")
    lines.append("## model_runner.py Log (full session)")
    runner_log = runner.get_log()
    if runner_log:
        lines.append("```")
        lines.append("\n".join(runner_log[-500:]))  # last 500 lines
        if len(runner_log) > 500:
            lines.append(f"... [{len(runner_log) - 500} earlier lines omitted]")
        lines.append("```")
    else:
        lines.append("_(no output captured)_")

    # output_log.jsonl
    lines.append("")
    lines.append("## output_log.jsonl (last 5 entries)")
    try:
        entries = [l for l in Path(OUTPUT_LOG).read_text(encoding="utf-8").splitlines() if l.strip()]
        for raw_entry in entries[-5:]:
            try:
                e = json.loads(raw_entry)
                lines.append(f"\n**{e.get('timestamp','')}** — `{e.get('user_message','')[:60]}`")
                lines.append(f"- marker_detected: `{e.get('marker_detected')}`")
                lines.append(f"- final_output: `{str(e.get('final_output',''))[:120]}`")
            except Exception:
                lines.append(f"  {raw_entry[:120]}")
    except Exception:
        lines.append("_(output_log.jsonl not found or empty)_")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Settings helpers — preset loading and active-config patching
# ---------------------------------------------------------------------------

def load_settings_json() -> dict:
    return json.loads(Path(SETTINGS_FILE).read_text(encoding="utf-8"))


def save_settings_json(data: dict):
    # settings_manager makes a .bk before saving; mirror that behaviour
    bk = SETTINGS_FILE + ".bk"
    if os.path.exists(SETTINGS_FILE):
        shutil.copy2(SETTINGS_FILE, bk)
    Path(SETTINGS_FILE).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def apply_preset(preset_id: str) -> tuple:
    """
    Copy model_presets[preset_id] into settings.active so model_runner.py
    will use that preset.  Returns (original_active, preset_cfg).
    Raises SystemExit with a helpful message if the preset or model is missing.
    """
    data      = load_settings_json()
    presets   = data.get("settings", {}).get("model_presets", {})

    if preset_id not in presets:
        available = ", ".join(presets.keys()) or "none"
        print(f"ERROR: Preset '{preset_id}' not found in settings.json.")
        print(f"       Available presets: {available}")
        sys.exit(1)

    preset_cfg     = presets[preset_id]
    original_active = dict(data["settings"].get("active", {}))

    # Validate model path
    mp = preset_cfg.get("model_path", "")
    full_mp = os.path.join(REPO_ROOT, mp) if mp and not os.path.isabs(mp) else mp
    if not mp or not os.path.exists(full_mp):
        print(f"ERROR: Model file for preset '{preset_id}' not found: {full_mp!r}")
        print(f"       Update model_presets.{preset_id}.model_path in settings.json.")
        sys.exit(1)

    # Patch active config
    data["settings"]["active"] = dict(preset_cfg)
    # model_runner.py expects an absolute (or repo-relative) path; keep as-is
    save_settings_json(data)
    print(f"[settings] Preset '{preset_id}' applied → active.model_path = {mp!r}")

    return original_active, preset_cfg


def restore_active(original_active: dict):
    """Put the original active config back into settings.json."""
    try:
        data = load_settings_json()
        data["settings"]["active"] = original_active
        save_settings_json(data)
        print(f"[settings] Original active config restored.")
    except Exception as e:
        print(f"[settings] WARNING: could not restore active config: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Parse --preset N from argv
    preset_id = DEFAULT_PRESET
    args = sys.argv[1:]
    if "--preset" in args:
        idx = args.index("--preset")
        if idx + 1 < len(args):
            preset_id = args[idx + 1]
        else:
            print("ERROR: --preset requires a value (e.g. --preset 1)")
            sys.exit(1)

    print(section("LYRN-AI Live Debug Runner"))
    print(f"Repo root:    {REPO_ROOT}")
    print(f"Model runner: {MODEL_RUNNER}")
    print(f"Preset:       {preset_id}")
    print(f"Prompts:      {len(TEST_PROMPTS)}")

    # Pre-flight checks
    for label, path in [("model_runner.py", MODEL_RUNNER), ("chat_watcher_bg.py", WATCHER_SCRIPT)]:
        if not os.path.exists(path):
            print(f"ERROR: {label} not found at {path}")
            sys.exit(1)

    # Apply chosen preset to settings.json → model_runner.py will pick it up
    original_active, preset_cfg = apply_preset(preset_id)
    print(f"Model:        {preset_cfg.get('model_path')}")

    os.makedirs(REPORT_DIR, exist_ok=True)
    os.makedirs(os.path.join(REPO_ROOT, "jobs"), exist_ok=True)
    os.makedirs(os.path.join(REPO_ROOT, "global_flags"), exist_ok=True)
    os.makedirs(os.path.join(REPO_ROOT, "chat"), exist_ok=True)

    started_at   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    runner       = ModelRunnerProcess()
    test_results = []

    try:
        # ── Start model_runner ──────────────────────────────────────────────
        print(f"\n[{ts()}] Starting model_runner.py (loading model — this may take a moment)...")
        runner.start()

        status = wait_for_status({"idle"}, timeout=MODEL_LOAD_TIMEOUT)
        if status != "idle":
            print(f"[{ts()}] ERROR: Model did not reach idle within {MODEL_LOAD_TIMEOUT}s "
                  f"(last status: {read_status()!r})")
            print("[runner log so far]")
            for line in runner.get_log()[-20:]:
                print(line)
            sys.exit(1)

        print(f"[{ts()}] Model loaded and ready (preset {preset_id}).")

        # ── Run test prompts ────────────────────────────────────────────────
        for i, prompt in enumerate(TEST_PROMPTS, 1):
            r = run_test(runner, prompt, i)
            test_results.append(r)
            time.sleep(1)  # brief gap between tests

    except KeyboardInterrupt:
        print(f"\n[{ts()}] Interrupted by user.")
    finally:
        runner.stop()
        restore_active(original_active)

    # ── Write report ────────────────────────────────────────────────────────
    report_ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(REPORT_DIR, f"debug_{report_ts}.md")

    print(f"\n[{ts()}] Writing debug report → {report_path} ...")
    report_text = build_report(runner, test_results, started_at, preset_id, preset_cfg)
    Path(report_path).write_text(report_text, encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"  Report:  {report_path}")
    print(f"  Tests:   {len(test_results)}")
    passed = sum(1 for r in test_results if not r["error"] and r["watcher_rc"] == 0)
    print(f"  Passed:  {passed}/{len(test_results)}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
