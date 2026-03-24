import os
import sys
import time
import json
import signal
import threading
import contextlib
import io
import re
from pathlib import Path

# Force UTF-8 output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Add current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llama_cpp import Llama
from settings_manager import SettingsManager
from snapshot_loader import SnapshotLoader
from delta_manager import DeltaManager
from chat_manager import ChatManager
from automation_controller import AutomationController
from backend.ds_manager import DSManager

# Global flag for clean shutdown
running = True
model_lock = threading.Lock()

def signal_handler(sig, frame):
    global running
    print("Shutting down worker...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRIGGER_FILE = os.path.join(SCRIPT_DIR, "chat_trigger.txt")
STOP_TRIGGER = os.path.join(SCRIPT_DIR, "stop_trigger.txt")
REBUILD_TRIGGER = os.path.join(SCRIPT_DIR, "rebuild_trigger.txt")
LLM_STATUS_FILE = os.path.join(SCRIPT_DIR, "global_flags", "llm_status.txt")
STATS_FILE = os.path.join(SCRIPT_DIR, "global_flags", "llm_stats.json")
FINAL_OUTPUT_FLAG = os.path.join(SCRIPT_DIR, "global_flags", "final_output_mode.txt")
AFFORDANCE_MARKER = "##AF: FINAL_OUTPUT##"

def set_llm_status(status: str):
    try:
        os.makedirs(os.path.dirname(LLM_STATUS_FILE), exist_ok=True)
        with open(LLM_STATUS_FILE, 'w', encoding='utf-8') as f:
            f.write(status)
    except Exception as e:
        print(f"Error setting LLM status: {e}")

def write_stats(stats_data):
    try:
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats_data, f)
    except Exception as e:
        print(f"Error writing stats: {e}")

def parse_metrics(log_output: str):
    stats = {}
    try:
        # KV Cache
        kv_match = re.search(r'(\d+)\s+prefix-match hit', log_output)
        if kv_match:
            stats["kv_cache_reused"] = int(kv_match.group(1))

        # Prompt Eval
        prompt_match = re.search(r'prompt eval time\s*=\s*([\d.]+)\s*ms\s*/\s*(\d+)\s*tokens.*?([\d.]+)\s*ms per token', log_output)
        if prompt_match:
            ms = float(prompt_match.group(1))
            tokens = int(prompt_match.group(2))
            ms_per_tok = float(prompt_match.group(3))
            stats["tokenization_time_ms"] = ms
            stats["prompt_tokens"] = tokens
            stats["prompt_speed"] = 1000.0 / ms_per_tok if ms_per_tok > 0 else 0.0

        # Eval (Generation)
        eval_match = re.search(r'eval time\s*=\s*([\d.]+)\s*ms\s*/\s*(\d+)\s*runs.*?([\d.]+)\s*ms per token', log_output)
        if eval_match:
            ms = float(eval_match.group(1))
            tokens = int(eval_match.group(2))
            ms_per_tok = float(eval_match.group(3))
            stats["generation_time_ms"] = ms
            stats["eval_tokens"] = tokens
            stats["eval_speed"] = 1000.0 / ms_per_tok if ms_per_tok > 0 else 0.0

        # Load Time
        load_match = re.search(r'load time\s*=\s*([\d.]+)\s*ms', log_output)
        if load_match:
            stats["load_time"] = float(load_match.group(1))

        # Total Time
        total_match = re.search(r'total time\s*=\s*([\d.]+)\s*ms', log_output)
        if total_match:
            stats["total_time"] = float(total_match.group(1)) / 1000.0

        if "prompt_tokens" in stats and "eval_tokens" in stats:
            stats["total_tokens"] = stats["prompt_tokens"] + stats["eval_tokens"]

    except Exception:
        pass
    return stats

def main():
    print("--- Model Runner Starting (v4 Logic) ---")
    set_llm_status("loading")

    # 1. Initialize Managers
    settings_manager = SettingsManager()

    # Reload settings
    settings_manager.load_or_detect_first_boot()
    settings = settings_manager.settings

    automation_controller = AutomationController()
    snapshot_loader = SnapshotLoader(settings_manager, automation_controller)
    delta_manager = DeltaManager()
    ds_manager = DSManager()

    role_mappings = {
        "assistant": "final_output",
        "model": "final_output",
        "thinking": "thinking_process",
        "analysis": "thinking_process"
    }

    chat_dir = settings.get("paths", {}).get("chat", "chat")
    chat_manager = ChatManager(chat_dir, settings_manager, role_mappings)

    # 2. Load Model
    active_config = settings.get("active", {})
    model_path = active_config.get("model_path", "")

    if not model_path or not os.path.exists(model_path):
        print(f"Error: Model path not found: {model_path}")
        set_llm_status("error")
        return

    print(f"Loading model: {model_path}")

    # Use v4 logic for model loading: use_mlock=True, use_mmap=False
    try:
        llm = Llama(
            model_path=model_path,
            n_ctx=active_config.get("n_ctx", 2048),
            n_threads=active_config.get("n_threads", 4),
            n_gpu_layers=active_config.get("n_gpu_layers", 0),
            n_batch=active_config.get("n_batch", 512),
            use_mlock=True,
            use_mmap=False,
            chat_format=active_config.get("chat_format"),
            add_bos=True,
            add_eos=True,
            verbose=True
        )
        print("Model loaded successfully.")
        set_llm_status("idle")
    except Exception as e:
        print(f"Failed to load model: {e}")
        set_llm_status("error")
        return

    # 3. Main Loop
    print(f"Watching for trigger: {TRIGGER_FILE}")

    while running:
        # Check for Rebuild Trigger (Just reloads snapshot into memory)
        if os.path.exists(REBUILD_TRIGGER):
            print(f"[Runner] Rebuild trigger detected.")
            try:
                os.remove(REBUILD_TRIGGER)
                settings_manager.load_or_detect_first_boot()
                settings = settings_manager.settings
                snapshot_loader.build_master_prompt_from_components()
                print("[Runner] Snapshot rebuilt.")
            except Exception as e:
                print(f"[Runner] Error rebuilding snapshot: {e}")

        if os.path.exists(TRIGGER_FILE):
            print(f"[Runner] Trigger detected: {TRIGGER_FILE}")

            # Reload settings
            try:
                settings_manager.load_or_detect_first_boot()
                settings = settings_manager.settings
            except Exception:
                pass

            try:
                with open(TRIGGER_FILE, 'r', encoding='utf-8') as f:
                    chat_file_path_str = f.read().strip()

                try:
                    os.remove(TRIGGER_FILE)
                except OSError: pass

                if chat_file_path_str:
                    process_request(llm, chat_file_path_str, snapshot_loader, delta_manager, chat_manager, settings_manager, ds_manager)

            except Exception as e:
                print(f"Error processing trigger: {e}")
                set_llm_status("error")

        time.sleep(0.1)

    print("Runner stopped.")
    set_llm_status("stopped")

def _read_input_payload(input_path: Path) -> dict:
    """
    Reads the input payload from the trigger path.
    Supports new JSON format and legacy text format.
    Returns: {"user_message": str, "job_instructions": str, "source": str}
    """
    if input_path.suffix == '.json':
        # New structured input format
        data = json.loads(input_path.read_text(encoding='utf-8'))
        return {
            "user_message": data.get("user_message", ""),
            "job_instructions": data.get("job_instructions", ""),
            "source": data.get("source", "job")
        }
    else:
        # Legacy text format: user\n{message}\n
        content = input_path.read_text(encoding='utf-8')
        user_message = ""
        if content.startswith("user\n"):
            user_message = content[5:].strip()
        else:
            match = re.search(r"#USER_START#\n(.*?)\n#USER_END#", content, re.DOTALL)
            if match:
                user_message = match.group(1).strip()
            else:
                user_message = content.strip()
        return {
            "user_message": user_message,
            "job_instructions": "",
            "source": "legacy"
        }


def _resolve_raw_output_path(input_path: Path) -> Path:
    """
    Determines the raw output file path based on the input path.
    For jobs/ folder inputs, writes to jobs/job_raw_output.txt.
    For other inputs, writes to a sibling _raw_output.txt file.
    """
    parent = input_path.parent
    if parent.name == "jobs":
        return parent / "job_raw_output.txt"
    else:
        return parent / f"{input_path.stem}_raw_output.txt"


def process_request(llm, chat_file_path_str: str, snapshot_loader, delta_manager, chat_manager, settings_manager, ds_manager):
    with model_lock:
        set_llm_status("busy")

        # Cleanup stop trigger
        try:
            if os.path.exists(STOP_TRIGGER):
                os.remove(STOP_TRIGGER)
        except: pass

        input_path = Path(chat_file_path_str)
        if not input_path.exists():
            print(f"Error: Input file not found: {input_path}")
            set_llm_status("idle")
            return

        try:
            # 1. Read Input Payload
            payload = _read_input_payload(input_path)
            user_message = payload["user_message"]
            job_instructions = payload["job_instructions"]
            source = payload["source"]

            print(f"[Runner] Source: {source} | job_instructions set: {bool(job_instructions.strip())} | User: {user_message[:60]}...")

            # 2. Determine Raw Output Path (separate from input)
            raw_output_path = _resolve_raw_output_path(input_path)

            # Clear any stale raw output
            if raw_output_path.exists():
                raw_output_path.unlink()

            # 3. Build Context
            # Master Prompt
            system_prompt = snapshot_loader.load_base_prompt()

            # Dynamic Snapshots (Jobs & Projects)
            dynamic_snapshot_content = ds_manager.get_active_snapshots_content()

            # Deltas
            delta_content = ""
            if settings_manager.get_setting("enable_deltas", True):
                delta_content = delta_manager.get_delta_content()

            # Construct Messages
            # Order: System Prompt -> Dynamic Snapshots -> History -> Deltas ->
            #        FINAL_OUTPUT flag -> job_instructions -> User Message
            messages = [{"role": "system", "content": system_prompt}]

            if dynamic_snapshot_content:
                messages.append({"role": "system", "content": f"--- Active Dynamic Snapshots ---\n{dynamic_snapshot_content}"})

            # History (no file exclusion needed — input is JSON, not a chat file)
            history = chat_manager.get_chat_history_messages(exclude_paths=[])
            messages.extend(history)

            # Deltas (Injected after history, before new input)
            if delta_content:
                messages.append({"role": "system", "content": delta_content})

            # Inject job_instructions as the LAST system message before the user turn.
            # Position matters: placing it here (after history/deltas) keeps it fresh in the
            # model's context window immediately before it generates.
            if job_instructions and job_instructions.strip():
                messages.append({"role": "system", "content": job_instructions})
                print("[Runner] Injected job_instructions before user turn.")

            # Append current user message (merge if last was also user to maintain alternating roles)
            if messages and messages[-1].get("role") == "user":
                messages[-1]["content"] += "\n\n" + user_message
            else:
                messages.append({"role": "user", "content": user_message})

            active_config = settings_manager.settings.get("active", {})
            log_capture_buffer = io.StringIO()

            # ── Phase 1: Thinking + Signal ──────────────────────────────────────────
            # Model thinks through the request and outputs ##AF: FINAL_OUTPUT## only.
            # This output is NOT written to raw_output_path (not streamed to user).
            print("[Runner] Phase 1: Thinking/signal generation starting...")
            phase1_output = ""
            marker_detected_p1 = False
            grace_count = 0
            GRACE_CHARS = 50  # Allow up to 50 chars after marker before breaking early

            with contextlib.redirect_stderr(log_capture_buffer):
                p1_stream = llm.create_chat_completion(
                    messages=messages,
                    max_tokens=active_config.get("max_tokens", 2048),
                    temperature=active_config.get("temperature", 0.7),
                    top_p=active_config.get("top_p", 0.95),
                    top_k=active_config.get("top_k", 40),
                    stream=True
                )
                for token_data in p1_stream:
                    if os.path.exists(STOP_TRIGGER):
                        try: os.remove(STOP_TRIGGER)
                        except: pass
                        break
                    if 'choices' in token_data and token_data['choices']:
                        text = token_data['choices'][0].get('delta', {}).get('content', '')
                        if text:
                            phase1_output += text
                            if not marker_detected_p1 and AFFORDANCE_MARKER in phase1_output:
                                marker_detected_p1 = True
                                print(f"[Runner] Phase 1: Affordance marker detected — entering grace period.")
                            elif marker_detected_p1:
                                grace_count += len(text)
                                if grace_count >= GRACE_CHARS:
                                    print(f"[Runner] Phase 1: Grace period elapsed — stopping early.")
                                    break

            if not marker_detected_p1:
                print(f"[Runner] WARNING: Affordance marker NOT found in phase 1 ({len(phase1_output)} chars). "
                      f"Appending marker as fallback.")
                phase1_output = (phase1_output.rstrip() or "") + "\n" + AFFORDANCE_MARKER

            print(f"[Runner] Phase 1 complete. Output: {len(phase1_output)} chars.")

            # Save phase 1 output for history/logging (watcher reads this)
            last_thinking_file = os.path.join(SCRIPT_DIR, "global_flags", "last_thinking.txt")
            try:
                os.makedirs(os.path.dirname(last_thinking_file), exist_ok=True)
                with open(last_thinking_file, "w", encoding="utf-8") as f:
                    f.write(phase1_output)
                print(f"[Runner] Phase 1 saved to last_thinking.txt")
            except Exception as e:
                print(f"[Runner] Error saving last_thinking.txt: {e}")

            # Set final output flag BEFORE phase 2 begins.
            # The watcher detects this flag and streams all phase 2 content as final output.
            try:
                os.makedirs(os.path.dirname(FINAL_OUTPUT_FLAG), exist_ok=True)
                with open(FINAL_OUTPUT_FLAG, "w") as ff:
                    ff.write("active")
                print("[Runner] Final output flag set. Phase 2 will stream to user.")
            except Exception as e:
                print(f"[Runner] Error setting final output flag: {e}")

            # ── Phase 2: Response (streamed to user) ────────────────────────────────
            # Add phase 1 as assistant turn, ##RECORD## as user turn.
            # Model generates the actual response, written to raw_output_path for streaming.
            print("[Runner] Phase 2: Response generation starting...")
            phase2_messages = messages + [
                {"role": "assistant", "content": phase1_output.strip()},
                {"role": "user", "content": "##RECORD##"}
            ]

            print(f"[Runner] Generating phase 2 response to: {raw_output_path}")

            with contextlib.redirect_stderr(log_capture_buffer):
                p2_stream = llm.create_chat_completion(
                    messages=phase2_messages,
                    max_tokens=active_config.get("max_tokens", 2048),
                    temperature=active_config.get("temperature", 0.7),
                    top_p=active_config.get("top_p", 0.95),
                    top_k=active_config.get("top_k", 40),
                    stream=True
                )
                with open(raw_output_path, "w", encoding="utf-8") as f:
                    for token_data in p2_stream:
                        if os.path.exists(STOP_TRIGGER):
                            print("[Runner] Stop trigger detected in phase 2.")
                            try: os.remove(STOP_TRIGGER)
                            except: pass
                            f.write("\n\n[Stopped]")
                            break
                        if 'choices' in token_data and token_data['choices']:
                            text = token_data['choices'][0].get('delta', {}).get('content', '')
                            if text:
                                f.write(text)
                                f.flush()

            print(f"[Runner] Phase 2 complete. Raw output: {raw_output_path}")

            # 5. Parse Metrics from Captured Log (both phases)
            log_output = log_capture_buffer.getvalue()
            print(log_output, file=sys.stderr)

            stats = parse_metrics(log_output)
            if stats:
                write_stats(stats)

            print(f"[Runner] Two-phase generation complete. Raw output: {raw_output_path}")
            set_llm_status("idle")

        except Exception as e:
            print(f"Error during generation: {e}")
            # Write error to raw output so capture layer can detect it
            try:
                raw_output_path = _resolve_raw_output_path(input_path)
                with open(raw_output_path, "w", encoding="utf-8") as f:
                    f.write(f"[Error: {e}]")
            except: pass
            set_llm_status("error")

if __name__ == "__main__":
    main()
