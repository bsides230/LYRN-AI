import os
import sys
import time
import json
import signal
import threading
import contextlib
import io
import re
import datetime
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
STOP_TRIGGER = os.path.join(SCRIPT_DIR, "stop_trigger.txt")
REBUILD_TRIGGER = os.path.join(SCRIPT_DIR, "rebuild_trigger.txt")
CHAT_TRIGGER = os.path.join(SCRIPT_DIR, "chat_trigger.txt")  # Deprecated
GLOBAL_FLAGS_DIR = os.path.join(SCRIPT_DIR, "global_flags")
JOB_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "job_output")
LLM_STATUS_FILE = os.path.join(GLOBAL_FLAGS_DIR, "llm_status.txt")
STATS_FILE = os.path.join(GLOBAL_FLAGS_DIR, "llm_stats.json")
LAST_ERROR_FILE = os.path.join(GLOBAL_FLAGS_DIR, "last_error.txt")

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
    print("--- Model Runner Starting (Job Loop Execution Rail) ---")
    set_llm_status("loading")

    # 1. Initialize Managers
    settings_manager = SettingsManager()

    # Reload settings
    settings_manager.load_or_detect_first_boot()
    settings = settings_manager.settings

    snapshot_loader = SnapshotLoader(settings_manager)

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
    os.makedirs(JOB_OUTPUT_DIR, exist_ok=True)
    os.makedirs(GLOBAL_FLAGS_DIR, exist_ok=True)
    print(f"Watching for job triggers in: {GLOBAL_FLAGS_DIR}")

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

        # Check for deprecated chat_trigger.txt
        if os.path.exists(CHAT_TRIGGER):
            print("[Runner] Deprecated chat_trigger.txt detected and removed.")
            try:
                os.remove(CHAT_TRIGGER)
            except OSError:
                pass

        # Check for incoming job triggers from global_flags/
        trigger_file, trigger_content = check_for_job_trigger(GLOBAL_FLAGS_DIR)
        if trigger_file:
            print(f"[Runner] Job trigger detected: {trigger_file}")

            # Reload settings
            try:
                settings_manager.load_or_detect_first_boot()
                settings = settings_manager.settings
            except Exception:
                pass

            try:
                os.remove(trigger_file)
            except OSError:
                pass

            try:
                process_job(llm, snapshot_loader, settings_manager, trigger_info=trigger_content)
            except Exception as e:
                print(f"Error processing job: {e}")
                set_llm_status("error")

        time.sleep(0.1)

    print("Runner stopped.")
    set_llm_status("stopped")

def check_for_job_trigger(flags_dir: str):
    """
    Checks global_flags directory for incoming job triggers.
    Returns (trigger_file_path, trigger_payload) if found, else (None, None).
    """
    if not os.path.exists(flags_dir):
        return None, None

    # 1. Primary trigger: job_ready.flag
    ready_flag = os.path.join(flags_dir, "job_ready.flag")
    if os.path.isfile(ready_flag):
        content = ""
        try:
            with open(ready_flag, "r", encoding="utf-8") as f:
                content = f.read().strip()
        except Exception:
            pass
        return ready_flag, content

    # 2. Explicit job trigger: job_trigger.txt
    job_trigger = os.path.join(flags_dir, "job_trigger.txt")
    if os.path.isfile(job_trigger):
        content = ""
        try:
            with open(job_trigger, "r", encoding="utf-8") as f:
                content = f.read().strip()
        except Exception:
            pass
        return job_trigger, content

    # 3. Any other *.trigger or job_*.flag files
    try:
        for entry in os.listdir(flags_dir):
            entry_path = os.path.join(flags_dir, entry)
            if not os.path.isfile(entry_path):
                continue
            if entry.endswith(".trigger") or (entry.startswith("job_") and entry.endswith(".flag")):
                content = ""
                try:
                    with open(entry_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                except Exception:
                    pass
                return entry_path, content
    except Exception:
        pass

    return None, None

def process_job(llm, snapshot_loader, settings_manager, trigger_info: str = ""):
    with model_lock:
        set_llm_status("busy")

        # Cleanup stop trigger before generation
        try:
            if os.path.exists(STOP_TRIGGER):
                os.remove(STOP_TRIGGER)
        except OSError:
            pass

        # Ensure job_output directory exists
        os.makedirs(JOB_OUTPUT_DIR, exist_ok=True)

        # Determine output target file in job_output/
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        output_filename = f"job_output_{timestamp}.txt"
        if trigger_info and trigger_info.endswith(".txt") and not trigger_info.startswith("#") and "\n" not in trigger_info:
            output_filename = os.path.basename(trigger_info)
        output_path = os.path.join(JOB_OUTPUT_DIR, output_filename)

        try:
            # 1. Static Prefix: Snapshot / base RWI via snapshot_loader (retains KV cache prefix hit)
            system_prompt = snapshot_loader.load_base_prompt()
            messages = [{"role": "system", "content": system_prompt}]

            # 2. State Context: Layer 2 Delta Working Memory (safeguarded: cleanly bypassed if missing)
            compiled_manifest_path = Path(SCRIPT_DIR) / "deltas" / "compiled_manifest.txt"
            try:
                if compiled_manifest_path.exists():
                    delta_content = compiled_manifest_path.read_text(encoding='utf-8').strip()
                    if delta_content:
                        messages.append({"role": "system", "content": delta_content})
            except (FileNotFoundError, OSError, Exception) as e:
                print(f"[Runner] Delta manifest not loaded ({e}), cleanly bypassing Layer 2.")

            # 3. Job Tail: Active job instructions (##JI:START## ... ##JI:END##), affordances (##AF:START## ... ##AF:END##), and trigger (##JOB_START##)
            job_context_path = Path(SCRIPT_DIR) / "global_flags" / "job_context.txt"
            job_content = ""
            if job_context_path.exists():
                try:
                    job_content = job_context_path.read_text(encoding='utf-8').strip()
                    try:
                        job_context_path.unlink()
                    except OSError:
                        pass
                except Exception as e:
                    print(f"Error reading job context: {e}")

            trigger_text = "##JOB_START##"
            trigger_file = Path(SCRIPT_DIR) / "runtime" / "jobs" / "trigger.txt"
            if trigger_file.exists():
                try:
                    loaded_trigger = trigger_file.read_text(encoding='utf-8').strip()
                    if loaded_trigger:
                        trigger_text = loaded_trigger
                except Exception:
                    pass

            job_tail_parts = []
            if job_content:
                job_tail_parts.append(job_content)
            job_tail_parts.append(trigger_text)
            job_tail = "\n\n".join(job_tail_parts)

            messages.append({"role": "user", "content": job_tail})

            # Stream Generation
            active_config = settings_manager.settings.get("active", {})
            log_capture_buffer = io.StringIO()

            print(f"[Runner] Executing job... Output target: {output_path}")

            with contextlib.redirect_stderr(log_capture_buffer):
                stream = llm.create_chat_completion(
                    messages=messages,
                    max_tokens=active_config.get("max_tokens", 2048),
                    temperature=active_config.get("temperature", 0.7),
                    top_p=active_config.get("top_p", 0.95),
                    top_k=active_config.get("top_k", 40),
                    stream=True
                )

                with open(output_path, "w", encoding="utf-8") as f:
                    for token_data in stream:
                        if os.path.exists(STOP_TRIGGER):
                            print("[Runner] Stop trigger detected.")
                            try:
                                os.remove(STOP_TRIGGER)
                            except OSError:
                                pass
                            f.write("\n\n[Stopped]")
                            f.flush()
                            break

                        if 'choices' in token_data and len(token_data['choices']) > 0:
                            delta = token_data['choices'][0].get('delta', {})
                            text = delta.get('content', '')
                            if text:
                                f.write(text)
                                f.flush()

            # Parse Metrics from Captured Log
            log_output = log_capture_buffer.getvalue()
            print(log_output, file=sys.stderr)

            stats = parse_metrics(log_output)
            if stats:
                write_stats(stats)

            print(f"[Runner] Job execution complete. Written to: {output_path}")
            set_llm_status("idle")

        except Exception as e:
            print(f"Error during job execution: {e}")
            try:
                with open(output_path, "a", encoding="utf-8") as f:
                    f.write(f"\n[Error: {e}]\n")
            except Exception:
                pass
            try:
                with open(LAST_ERROR_FILE, "w", encoding="utf-8") as f_err:
                    f_err.write(str(e))
            except Exception:
                pass
            set_llm_status("error")

if __name__ == "__main__":
    main()
