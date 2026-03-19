import sys
import os
import time
import re
import json
from pathlib import Path


def get_input_from_json(root_dir):
    """Reads the user message from the structured job input file."""
    try:
        input_path = os.path.join(root_dir, "jobs", "job_input.json")
        if os.path.exists(input_path):
            with open(input_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("user_message", "").strip()
    except Exception as e:
        print(f"Error reading job_input.json: {e}")
    return None


def get_input_from_snapshot(root_dir):
    """Fallback: reads user input from legacy dynamic snapshot."""
    try:
        snapshot_path = os.path.join(root_dir, "automation", "dynamic_snapshots", "jobs", "chat_input_context.txt")
        if os.path.exists(snapshot_path):
            with open(snapshot_path, "r", encoding="utf-8") as f:
                content = f.read()
                match = re.search(r'\[Chat Input\]:\n(.*)', content, re.DOTALL)
                if match:
                    return match.group(1).strip()
                return content.strip()
    except Exception as e:
        print(f"Error reading snapshot: {e}")
    return "Unknown Input"


def save_chat_history(root_dir, user_input, model_response):
    """Writes the final user/model pair to a chat history file."""
    try:
        chat_dir = os.path.join(root_dir, "chat")
        os.makedirs(chat_dir, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S_") + str(int(time.time() * 1000) % 1000)
        filename = f"chat_{timestamp}.txt"
        filepath = os.path.join(chat_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"user\n{user_input}\n\nmodel\n{model_response}\n")

        print(f"Saved chat response to {filepath}")
    except Exception as e:
        print(f"Error saving chat history: {e}")


def extract_response(raw_text):
    """
    Extracts the final response from raw model output.
    Tries marker-based extraction first, then falls back to full text.
    """
    raw_text = raw_text.strip()
    if not raw_text:
        return None

    # Try marker-based extraction (if model complied with instructions)
    start_marker = "##Response_START##"
    end_marker = "##Response_END##"
    if start_marker in raw_text and end_marker in raw_text:
        pattern = re.compile(f"{start_marker}(.*?){end_marker}", re.DOTALL)
        match = pattern.search(raw_text)
        if match:
            extracted = match.group(1).strip()
            if extracted:
                print("Extracted response using markers.")
                return extracted

    # Fallback: use the full raw output as the response
    # The raw output file contains ONLY model generation (no user input mixed in)
    print("Using full raw output as response (no markers found).")
    return raw_text


def main():
    if len(sys.argv) < 2:
        print("Missing root directory argument.")
        sys.exit(1)

    root_dir = sys.argv[1]
    raw_output_file = os.path.join(root_dir, "jobs", "job_raw_output.txt")
    lock_file = os.path.join(root_dir, "global_flags", "chat_processing.txt")
    llm_status_path = os.path.join(root_dir, "global_flags", "llm_status.txt")

    print(f"[Watcher] Watching {raw_output_file} for raw model output...")

    start_time = time.time()
    timeout = 1800  # 30 minutes

    while True:
        if time.time() - start_time > timeout:
            print("[Watcher] Timed out.")
            if os.path.exists(lock_file):
                os.remove(lock_file)
                print("[Watcher] Cleared chat_processing.txt lock due to timeout")
            break

        # Check if raw output file exists (model runner creates it when generation starts)
        if os.path.exists(raw_output_file):
            try:
                # Wait for LLM to finish generating before reading
                llm_status = "idle"
                try:
                    with open(llm_status_path, "r", encoding="utf-8") as sf:
                        llm_status = sf.read().strip()
                except Exception:
                    llm_status = "idle"  # assume done if file unreadable

                if llm_status not in ("idle", "error", "stopped"):
                    time.sleep(1)
                    continue

                # LLM is done — read the raw output
                with open(raw_output_file, "r", encoding="utf-8") as f:
                    raw_content = f.read()

                response_text = extract_response(raw_content)

                if response_text:
                    # Get user input from structured input file (preferred) or snapshot (fallback)
                    user_input = get_input_from_json(root_dir)
                    if not user_input:
                        user_input = get_input_from_snapshot(root_dir)

                    # Write the final captured response to chat history
                    save_chat_history(root_dir, user_input, response_text)

                    # Clear the processing lock
                    if os.path.exists(lock_file):
                        os.remove(lock_file)
                        print("[Watcher] Cleared chat_processing.txt lock")

                    print("[Watcher] Capture complete. Exiting.")
                    sys.exit(0)
                else:
                    # Raw output exists but is empty — wait for content
                    time.sleep(1)
                    continue

            except Exception as e:
                print(f"[Watcher] Error reading output file: {e}")

        time.sleep(1)


if __name__ == "__main__":
    main()
