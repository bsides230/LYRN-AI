import sys
import os
import time
import re
from pathlib import Path

def get_input_from_snapshot(root_dir):
    try:
        snapshot_path = os.path.join(root_dir, "automation", "dynamic_snapshots", "jobs", "chat_input_context.txt")
        if os.path.exists(snapshot_path):
            with open(snapshot_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Try to extract just the input text
                match = re.search(r'\[Chat Input\]:\n(.*)', content, re.DOTALL)
                if match:
                    return match.group(1).strip()
                return content.strip()
    except Exception as e:
        print(f"Error reading snapshot: {e}")
    return "Unknown Input"

def save_chat_history(root_dir, user_input, model_response):
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

def main():
    if len(sys.argv) < 2:
        print("Missing root directory argument.")
        sys.exit(1)

    root_dir = sys.argv[1]
    output_file = os.path.join(root_dir, "jobs", "job_model_output.txt")
    lock_file = os.path.join(root_dir, "global_flags", "chat_processing.txt")
    snapshot_active_file = os.path.join(root_dir, "automation", "dynamic_snapshots", "jobs", ".active", "chat_input_context.active")

    print(f"Watching {output_file} for response markers...")

    start_time = time.time()
    timeout = 1800 # 30 minutes

    while True:
        if time.time() - start_time > timeout:
            print("Watcher timed out.")
            # Clear lock file on timeout to prevent permanent UI lock
            if os.path.exists(lock_file):
                os.remove(lock_file)
                print("Cleared chat_processing.txt lock due to timeout")
            # Deactivate snapshot on timeout
            if os.path.exists(snapshot_active_file):
                os.remove(snapshot_active_file)
                print("Deactivated chat_input_context snapshot due to timeout")
            break

        if os.path.exists(output_file):
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    content = f.read()

                start_marker = "##Response_START##"
                end_marker = "##Response_END##"

                if start_marker in content and end_marker in content:
                    print("Found response markers!")

                    # Extract the response block
                    pattern = re.compile(f"{start_marker}(.*?){end_marker}", re.DOTALL)
                    match = pattern.search(content)

                    if match:
                        response_text = match.group(1).strip()
                        user_input = get_input_from_snapshot(root_dir)

                        save_chat_history(root_dir, user_input, response_text)

                        # Clear lock file
                        if os.path.exists(lock_file):
                            os.remove(lock_file)
                            print("Cleared chat_processing.txt lock")

                        # Deactivate snapshot
                        if os.path.exists(snapshot_active_file):
                            os.remove(snapshot_active_file)
                            print("Deactivated chat_input_context snapshot")

                        # We are done
                        sys.exit(0)

            except Exception as e:
                print(f"Error reading output file: {e}")

        time.sleep(1)

if __name__ == "__main__":
    main()
