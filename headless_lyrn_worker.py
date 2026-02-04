import os
import sys
import time
import json
import signal
from pathlib import Path
from typing import Optional, List, Dict

# Force UTF-8 output to prevent Windows charmap errors
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Add the current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llama_cpp import Llama
from settings_manager import SettingsManager
from snapshot_loader import SnapshotLoader
from delta_manager import DeltaManager
from chat_manager import ChatManager
from automation_controller import AutomationController

# Global flag for clean shutdown
running = True

def signal_handler(sig, frame):
    global running
    print("Shutting down worker...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRIGGER_FILE = os.path.join(SCRIPT_DIR, "chat_trigger.txt")
REBUILD_TRIGGER = os.path.join(SCRIPT_DIR, "rebuild_trigger.txt")
LLM_STATUS_FILE = os.path.join(SCRIPT_DIR, "global_flags", "llm_status.txt")
STATS_FILE = os.path.join(SCRIPT_DIR, "global_flags", "llm_stats.json")

def set_llm_status(status: str):
    try:
        os.makedirs(os.path.dirname(LLM_STATUS_FILE), exist_ok=True)
        with open(LLM_STATUS_FILE, 'w', encoding='utf-8') as f:
            f.write(status)
    except Exception as e:
        print(f"Error setting LLM status: {e}")

def write_stats(tps, tokens_generated, model_name):
    try:
        data = {
            "tps": round(tps, 2),
            "last_tokens": tokens_generated,
            "model_name": os.path.basename(model_name),
            "timestamp": time.time()
        }
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error writing stats: {e}")

def main():
    print("--- Headless LYRN Worker Starting ---")
    set_llm_status("loading")

    # 1. Initialize Managers
    settings_manager = SettingsManager()

    # Reload settings to ensure we have the latest
    settings_manager.load_or_detect_first_boot()
    settings = settings_manager.settings

    automation_controller = AutomationController()

    snapshot_loader = SnapshotLoader(settings_manager, automation_controller)
    delta_manager = DeltaManager()

    # ChatManager requires role mappings
    role_mappings = {
        "assistant": "final_output",
        "model": "final_output",
        "thinking": "thinking_process",
        "analysis": "thinking_process"
    }
    chat_manager = ChatManager(settings["paths"]["chat"], settings_manager, role_mappings)

    # 2. Load Model
    active_config = settings.get("active", {})
    model_path = active_config.get("model_path", "")

    if not model_path or not os.path.exists(model_path):
        print(f"Error: Model path not found: {model_path}")
        set_llm_status("error")
        return

    print(f"Loading model: {model_path}")
    print(f"Config: {json.dumps(active_config, indent=2)}")

    try:
        llm = Llama(
            model_path=model_path,
            n_ctx=active_config.get("n_ctx", 2048),
            n_threads=active_config.get("n_threads", 4),
            n_gpu_layers=active_config.get("n_gpu_layers", 0),
            n_batch=active_config.get("n_batch", 512),
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
        # Check for Rebuild Trigger
        if os.path.exists(REBUILD_TRIGGER):
            print(f"[Worker] Rebuild trigger detected.")
            try:
                os.remove(REBUILD_TRIGGER)

                # Reload settings
                settings_manager.load_or_detect_first_boot()
                settings = settings_manager.settings

                set_llm_status("loading")
                print("[Worker] Rebuilding snapshot...")
                snapshot_loader.build_master_prompt_from_components()
                print("[Worker] Snapshot rebuilt successfully.")
                set_llm_status("idle")
            except Exception as e:
                print(f"[Worker] Error rebuilding snapshot: {e}")
                set_llm_status("error")

        if os.path.exists(TRIGGER_FILE):
            print(f"[Worker] Trigger detected: {TRIGGER_FILE}")

            # Reload settings to ensure fresh preferences (e.g. history length)
            try:
                settings_manager.load_or_detect_first_boot()
                settings = settings_manager.settings
            except Exception as e:
                print(f"[Worker] Error reloading settings: {e}")

            try:
                with open(TRIGGER_FILE, 'r', encoding='utf-8') as f:
                    content = f.read().strip()

                # Delete trigger immediately
                try:
                    os.remove(TRIGGER_FILE)
                except OSError:
                    pass # Already deleted?

                if content:
                    process_request(llm, content, snapshot_loader, delta_manager, chat_manager, settings)

            except Exception as e:
                print(f"Error processing trigger: {e}")
                set_llm_status("error")

        time.sleep(0.1)

    print("Worker stopped.")
    set_llm_status("stopped")

def process_request(llm, chat_file_path_str: str, snapshot_loader, delta_manager, chat_manager, settings):
    """
    Processes a chat request triggered by a file path in chat_trigger.txt.
    """
    set_llm_status("busy")
    print(f"Processing request for: {chat_file_path_str}")

    try:
        # 1. Rebuild Context
        # Master Prompt
        system_prompt = snapshot_loader.load_base_prompt()

        # Deltas
        delta_content = delta_manager.get_delta_content()

        # Chat History (Structured)
        # Note: We need to exclude the current chat file if it's already in the history folder,
        # but ChatManager scans the folder.
        # Assuming ChatManager.get_chat_history_messages() returns everything.
        # We might need to filter or just rely on the fact that we are appending to a file
        # that might effectively be the "next" turn.

        # However, following the model_loader logic, we construct the prompt from history + current file content.

        print(f"[Worker] Building prompt components...")
        print(f"[Worker] System Prompt Length: {len(system_prompt)}")
        print(f"[Worker] Delta Content Length: {len(delta_content) if delta_content else 0}")

        # IMPORTANT:
        # This snapshot prompt is treated as a stable prefix for KV cache reuse.
        # Do NOT rebuild, reorder, or mutate unless REBUILD_TRIGGER is active.
        messages = [{"role": "system", "content": system_prompt}]

        # Add Deltas as a separate system message if present
        if delta_content:
            messages.append({"role": "system", "content": delta_content})

        # Add History
        # We do NOT exclude the current path, allowing ChatManager to parse the full history
        # including previous turns in the current file.
        history = chat_manager.get_chat_history_messages(exclude_paths=[])
        messages.extend(history)

        # 2. Identify Current User Input (for logging)
        chat_file_path = Path(chat_file_path_str)
        if not chat_file_path.exists():
            print(f"Error: Chat file not found: {chat_file_path}")
            return

        # We inspect the last message in the constructed prompt to log the user input
        if len(messages) > 1:
            last_msg = messages[-1]
            if last_msg['role'] == 'user':
                print(f"User: {last_msg['content']}", flush=True)
            else:
                print(f"Last message role: {last_msg['role']}", flush=True)
        else:
            print("Warning: No history found for current request.")
        print(f"[Worker] Total messages in prompt: {len(messages)}")
        for i, msg in enumerate(messages):
            print(f"  [{i}] Role: {msg['role']}, Content Length: {len(msg['content'])}")

        # 3. Generate
        active_config = settings.get("active", {})
        start_time = time.time()
        token_count = 0
        first_token_time = None

        stream = llm.create_chat_completion(
            messages=messages,
            max_tokens=active_config.get("max_tokens", 2048),
            temperature=active_config.get("temperature", 0.7),
            top_p=active_config.get("top_p", 0.95),
            top_k=active_config.get("top_k", 40),
            stream=True
        )

        # 4. Stream output to file
        full_response = ""
        with open(chat_file_path, "a", encoding="utf-8") as f:
            f.write("\n\n#MODEL_START#\n") # Separator
            for token_data in stream:
                if 'choices' in token_data and len(token_data['choices']) > 0:
                    delta = token_data['choices'][0].get('delta', {})
                    content = delta.get('content', '')
                    if content:
                        if first_token_time is None:
                            first_token_time = time.time()
                        token_count += 1
                        f.write(content)
                        f.flush()
                        full_response += content
            f.write("\n#MODEL_END#\n")

        end_time = time.time()

        # Stats Calculation
        total_duration = end_time - start_time

        # Decode Speed (Generation Speed)
        # Avoid division by zero
        if first_token_time and end_time > first_token_time:
            decode_duration = end_time - first_token_time
            # Using token_count for decode speed (approximating that time taken was for all tokens)
            # Strictly it should be (token_count - 1) / (last - first), but user wants consistency with "stats"
            decode_tps = token_count / decode_duration if decode_duration > 0 else 0
        else:
            decode_tps = 0

        # Write stats using the decode TPS (user preference)
        write_stats(decode_tps, token_count, active_config.get("model_path", "Unknown"))

        print(f"Model: {full_response}", flush=True)
        print(f"Generation complete. {token_count} tokens. Total Time: {total_duration:.2f}s. Speed: {decode_tps:.2f} T/s")
        set_llm_status("idle")

    except Exception as e:
        print(f"Error during generation: {e}")
        try:
            with open(chat_file_path, "a", encoding="utf-8") as f:
                f.write(f"\n[Error: {e}]\n")
        except:
            pass
        set_llm_status("error")

    finally:
        # Do NOT call llm.reset() here.
        # We want to preserve the KV cache for the stable prefix (snapshot).
        # Context "wiping" is handled logically by constructing a fresh message list
        # for each request, but physically we keep the model state to reuse the prefix.
        pass

if __name__ == "__main__":
    main()
