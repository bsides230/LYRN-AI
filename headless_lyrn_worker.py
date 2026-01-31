import os
import sys
import time
import json
import signal
from pathlib import Path
from typing import Optional, List, Dict

# Add the current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llama_cpp import Llama
from settings_manager import SettingsManager
from snapshot_loader import SnapshotLoader
from delta_manager import DeltaManager
from chat_manager import ChatManager
from automation_controller import AutomationController
from oss_tool_manager import OSSToolManager

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
LLM_STATUS_FILE = os.path.join(SCRIPT_DIR, "global_flags", "llm_status.txt")

def set_llm_status(status: str):
    try:
        os.makedirs(os.path.dirname(LLM_STATUS_FILE), exist_ok=True)
        with open(LLM_STATUS_FILE, 'w', encoding='utf-8') as f:
            f.write(status)
    except Exception as e:
        print(f"Error setting LLM status: {e}")

def main():
    print("--- Headless LYRN Worker Starting ---")
    set_llm_status("loading")

    # 1. Initialize Managers
    settings_manager = SettingsManager()

    # Reload settings to ensure we have the latest
    settings_manager.load_or_detect_first_boot()
    settings = settings_manager.settings

    automation_controller = AutomationController()
    oss_tool_manager = OSSToolManager()

    snapshot_loader = SnapshotLoader(settings_manager, automation_controller, oss_tool_manager)
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
            verbose=False # Reduce spam
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
        if os.path.exists(TRIGGER_FILE):
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

        messages = [{"role": "system", "content": system_prompt}]
        if delta_content:
            messages.append({"role": "system", "content": delta_content})

        # Add History
        history = chat_manager.get_chat_history_messages()
        # Filter out the current file if it happens to be in history (unlikely if new)
        # or just assume history is past context.
        messages.extend(history)

        # 2. Read User Input from the Chat File
        chat_file_path = Path(chat_file_path_str)
        if not chat_file_path.exists():
            print(f"Error: Chat file not found: {chat_file_path}")
            return

        with open(chat_file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()

        # Parse user content from "user\nCONTENT"
        # Only take the last user part if the file has history?
        # Standard format: user\nMSG\n\nmodel\nRESP
        # The trigger file usually has just "user\nMSG" at the end or creates a new file.
        # We assume the file *ends* with "user\nMSG" and we append "\n\nmodel\n"

        # Extract the user message using regex for #USER_START#...#USER_END#
        # We look for the LAST occurrence to get the current prompt.
        import re
        user_blocks = re.findall(r"#USER_START#\n(.*?)\n#USER_END#", file_content, re.DOTALL)

        if not user_blocks:
            # Fallback to old format for compatibility or error
            last_user_idx = file_content.rfind("user\n")
            if last_user_idx != -1:
                user_message = file_content[last_user_idx + 5:].strip()
            else:
                print("Error: No user message found in chat file.")
                return
        else:
            user_message = user_blocks[-1].strip()

        # Append to messages
        messages.append({"role": "user", "content": user_message})

        # 3. Generate
        active_config = settings.get("active", {})

        stream = llm.create_chat_completion(
            messages=messages,
            max_tokens=active_config.get("max_tokens", 2048),
            temperature=active_config.get("temperature", 0.7),
            top_p=active_config.get("top_p", 0.95),
            top_k=active_config.get("top_k", 40),
            stream=True
        )

        # 4. Stream output to file
        with open(chat_file_path, "a", encoding="utf-8") as f:
            f.write("\n\n#MODEL_START#\n") # Separator
            for token_data in stream:
                if 'choices' in token_data and len(token_data['choices']) > 0:
                    delta = token_data['choices'][0].get('delta', {})
                    content = delta.get('content', '')
                    if content:
                        f.write(content)
                        f.flush()
            f.write("\n#MODEL_END#\n")

        print("Generation complete.")
        set_llm_status("idle")

    except Exception as e:
        print(f"Error during generation: {e}")
        try:
            with open(chat_file_path, "a", encoding="utf-8") as f:
                f.write(f"\n[Error: {e}]\n")
        except:
            pass
        set_llm_status("error")

if __name__ == "__main__":
    main()
