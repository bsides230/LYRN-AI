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
IPC_DIR = SCRIPT_DIR / "ipc"
PROMPTS_DIR = IPC_DIR / "prompts"
RESPONSES_DIR = IPC_DIR / "responses"
LOCK_FILE = IPC_DIR / "ipc.lock"

def log(message):
    """Prints a message to stderr for the GUI to capture."""
    print(f"MODEL_LOADER: {message}", file=sys.stderr, flush=True)

def process_prompt(llm: Llama, prompt_file: Path):
    """
    Reads a prompt file, processes it with the loaded LLM,
    and writes a response file.
    """
    try:
        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt_data = json.load(f)

        log(f"Processing prompt: {prompt_file.name}")

        system_prompt = prompt_data.get("system", "")
        user_prompt = prompt_data.get("user", "")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # --- Actual LLM processing ---
        completion = llm.create_chat_completion(
            messages=messages,
            max_tokens=2048,  # Consider making this an arg
            stream=False # Non-streaming for simple IPC
        )
        response_content = completion['choices'][0]['message']['content']

        response_data = {
            "response": response_content,
            "timestamp": time.time()
        }

        # The response file has the same name as the prompt file.
        response_file = RESPONSES_DIR / prompt_file.name

        with open(response_file, 'w', encoding='utf-8') as f:
            json.dump(response_data, f)

        log(f"Wrote response: {response_file.name}")

    except Exception as e:
        log(f"Error processing prompt {prompt_file.name}: {e}")
    finally:
        # Clean up the prompt file after processing
        try:
            prompt_file.unlink()
        except OSError as e:
            log(f"Error deleting prompt file {prompt_file.name}: {e}")

def watch_for_prompts(llm: Llama):
    """
    Main loop that watches for new files in the prompts directory.
    """
    log(f"Watching for prompts in: {PROMPTS_DIR}")
    while True:
        try:
            # Use a file lock to ensure only one process is checking the queue
            with SimpleFileLock(LOCK_FILE, timeout=5):
                # Get the oldest file in the directory
                prompt_files = sorted(PROMPTS_DIR.iterdir(), key=os.path.getmtime)
                if prompt_files:
                    process_prompt(llm, prompt_files[0])

        except TimeoutError:
            # Another process (e.g., the GUI writing a prompt) has the lock.
            # This is expected, so we just continue and try again shortly.
            pass
        except Exception as e:
            log(f"An unexpected error occurred in the watch loop: {e}")

        # Wait a short time before checking again to avoid busy-waiting
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
    parser.add_argument("--ipc-id", type=str, default=None, help="Unique ID for the IPC directory.")

    args = parser.parse_args()

    global IPC_DIR, PROMPTS_DIR, RESPONSES_DIR, LOCK_FILE
    if args.ipc_id:
        IPC_DIR = SCRIPT_DIR / "ipc" / args.ipc_id
        PROMPTS_DIR = IPC_DIR / "prompts"
        RESPONSES_DIR = IPC_DIR / "responses"
        LOCK_FILE = IPC_DIR / "ipc.lock"
        log(f"Using isolated IPC directory: {IPC_DIR}")

    log("--- LYRN-AI Model Loader ---")
    log(f"IPC ID: {args.ipc_id or 'default'}")
    log(f"Model Path: {args.model_path}")
    log(f"Context Size: {args.n_ctx}")
    log(f"Threads: {args.n_threads}")
    log(f"GPU Layers: {args.n_gpu_layers}")
    log("----------------------------")

    # --- Create IPC directories ---
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    RESPONSES_DIR.mkdir(parents=True, exist_ok=True)

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
    watch_for_prompts(llm)

if __name__ == "__main__":
    main()
