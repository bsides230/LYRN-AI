import argparse
import json
import os
import time
import sys
from pathlib import Path
from llama_cpp import Llama
from file_lock import SimpleFileLock

# --- Configuration ---
SCRIPT_DIR = Path(__file__).parent.resolve()
SETTINGS_PATH = SCRIPT_DIR / "settings.json"
TRIGGER_FILE = SCRIPT_DIR / "chat_trigger.txt"

def log(message):
    """Prints a message to stderr for the GUI to capture."""
    print(f"MODEL_LOADER: {message}", file=sys.stderr, flush=True)

def load_settings():
    """Loads settings from the shared settings.json file."""
    if not SETTINGS_PATH.exists():
        log("FATAL: settings.json not found.")
        sys.exit(1)
    try:
        with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log(f"FATAL: Error loading settings.json: {e}")
        sys.exit(1)

def build_full_prompt(settings: dict, chat_folder: str) -> str:
    """Constructs the full prompt from snapshots and chat history."""
    prompt_parts = []
    paths = settings.get("paths", {})

    def safe_read(path: str, label: str, required: bool = True) -> str:
        if not path:
            return f"[⚠️ Path for '{label}' not configured in settings.json]"
        if not os.path.exists(path):
            if required:
                return f"[⚠️ Missing {label} file at: {path}]"
            else:
                return ""
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read().strip()

    # This logic is adapted from the old qwen_chat_v2.py
    master_prompt_path = SCRIPT_DIR / "build_prompt" / "master_prompt.txt"
    prompt_parts.append(f"--- START OF BASE PROMPT ---\n{safe_read(str(master_prompt_path), 'Master Prompt')}\n--- END OF BASE PROMPT ---")

    # Load chat history
    if os.path.isdir(chat_folder):
        chat_files = sorted([f for f in os.listdir(chat_folder) if f.startswith("chat_") and f.endswith(".txt")])
        if chat_files:
            prompt_parts.append("\n--- START OF CHAT HISTORY ---")
            for fname in chat_files:
                # We read the file but exclude the very last line if it's just 'model'
                # because we are about to generate the response for it.
                content = safe_read(os.path.join(chat_folder, fname), f"chat file {fname}")
                if content.endswith("\nmodel"):
                    content = content[:-5].strip()
                prompt_parts.append(content)
            prompt_parts.append("--- END OF CHAT HISTORY ---")

    return "\n\n".join(prompt_parts)


def process_chat_request(llm: Llama, settings: dict, chat_file_path_str: str):
    """
    Processes a chat request by building a full prompt and streaming the
    response back into the specified chat file.
    """
    log(f"Processing request for chat file: {chat_file_path_str}")
    chat_file_path = Path(chat_file_path_str)
    chat_folder = chat_file_path.parent

    try:
        full_prompt = build_full_prompt(settings, str(chat_folder))

        messages = [{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": full_prompt}]

        stream = llm.create_chat_completion(
            messages=messages,
            max_tokens=settings.get("active", {}).get("max_tokens", 4096),
            temperature=settings.get("active", {}).get("temperature", 0.7),
            top_p=settings.get("active", {}).get("top_p", 0.95),
            top_k=settings.get("active", {}).get("top_k", 40),
            stream=True,
        )

        # Stream the response back to the same chat file
        with open(chat_file_path, "a", encoding="utf-8") as f:
            for token_data in stream:
                content = token_data['choices'][0]['delta'].get('content', '')
                if content:
                    f.write(content)
                    f.flush() # Ensure the GUI can read the token immediately
            f.write("\n") # Add a final newline for clean separation

        log(f"Finished streaming response to {chat_file_path.name}")

    except Exception as e:
        log(f"Error processing chat request for {chat_file_path.name}: {e}")
        # Write error to file so GUI can see it
        try:
            with open(chat_file_path, "a", encoding="utf-8") as f:
                f.write(f"\n[MODEL_LOADER_ERROR]: {e}\n")
        except Exception as write_e:
            log(f"Failed to write error to chat file: {write_e}")


def handle_startup_prompt(llm: Llama, settings: dict):
    """Handles the special '###startup###' prompt."""
    log("Processing '###startup###' request.")
    try:
        # Build a prompt that only includes the master prompt, no chat history
        master_prompt_path = SCRIPT_DIR / "build_prompt" / "master_prompt.txt"
        with open(master_prompt_path, "r", encoding="utf-8") as f:
            master_prompt = f.read().strip()

        startup_prompt = f"{master_prompt}\n\n---SYSTEM BOOT---"
        messages = [{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": startup_prompt}]

        # We just need to run this to load the model, no real output is needed for the GUI
        _ = llm.create_chat_completion(messages=messages, max_tokens=1)
        log("Startup prompt processed successfully.")
    except Exception as e:
        log(f"Error processing startup prompt: {e}")


def watch_for_trigger(llm: Llama, settings: dict):
    """Main loop that watches for the chat_trigger.txt file."""
    log(f"Watching for trigger file: {TRIGGER_FILE}")
    while True:
        if TRIGGER_FILE.exists():
            try:
                with open(TRIGGER_FILE, 'r', encoding='utf-8') as f:
                    content = f.read().strip()

                # Immediately delete the trigger file to prevent reprocessing
                TRIGGER_FILE.unlink()

                if content == "###startup###":
                    handle_startup_prompt(llm, settings)
                elif content:
                    process_chat_request(llm, settings, content)
                else:
                    log("Trigger file was empty. Ignoring.")

            except Exception as e:
                log(f"Error processing trigger file: {e}")
                if TRIGGER_FILE.exists():
                    try:
                        TRIGGER_FILE.unlink()
                    except OSError:
                        pass # Ignore if it's already gone
        time.sleep(0.1)

def main():
    """
    Main function to set up and run the model loader.
    """
    parser = argparse.ArgumentParser(description="LYRN-AI Model Loader")
    parser.add_argument("--model-path", type=str, required=True, help="Path to the GGUF model file.")
    parser.add_argument("--n_ctx", type=int, default=8192, help="Context size.")
    parser.add_argument("--n_threads", type=int, default=8, help="Number of threads.")
    parser.add_argument("--n_gpu_layers", type=int, default=0, help="Number of GPU layers.")
    args = parser.parse_args()

    log("--- LYRN-AI Model Loader (File-based) ---")
    log(f"Model Path: {args.model_path}")
    log(f"Context Size: {args.n_ctx}")
    log(f"Threads: {args.n_threads}")
    log(f"GPU Layers: {args.n_gpu_layers}")
    log("-----------------------------------------")

    settings = load_settings()

    # --- Load the actual Llama model ---
    try:
        log("Loading model...")
        llm = Llama(
            model_path=args.model_path,
            n_ctx=args.n_ctx,
            n_threads=args.n_threads,
            n_gpu_layers=args.n_gpu_layers,
            verbose=True # Llama.cpp will print its own logs to stderr
        )
        log("Model loaded successfully.")
    except Exception as e:
        log(f"FATAL: Failed to load model. Error: {e}")
        sys.exit(1) # Exit if the model can't be loaded

    # Start the main watch loop
    watch_for_trigger(llm, settings)

if __name__ == "__main__":
    main()
