import sys
import subprocess
import os
import json


def main():
    print("--- spawn_chat_watcher.py executed ---")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    watcher_script = os.path.join(script_dir, "chat_watcher_bg.py")
    root_dir = os.path.abspath(os.path.join(script_dir, '../..'))

    # Capture user_message NOW before job_input.json can be overwritten by the next request.
    # This prevents the race condition where the watcher reads a stale/new user_message
    # from job_input.json after LLM generation finishes.
    user_message = ""
    try:
        job_input_path = os.path.join(root_dir, "jobs", "job_input.json")
        with open(job_input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            user_message = data.get("user_message", "")
        print(f"Captured user_message at spawn time: {user_message[:60]}...")
    except Exception as e:
        print(f"Warning: could not read user_message from job_input.json: {e}")

    cmd = [sys.executable, watcher_script, root_dir, user_message]

    if os.name == 'nt':
        subprocess.Popen(
            cmd,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000008,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    else:
        subprocess.Popen(
            cmd,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    print("Spawned background watcher.")
    sys.exit(0)


if __name__ == "__main__":
    main()
