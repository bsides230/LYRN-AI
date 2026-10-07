import sys
import os
import time

# Add parent dir to path so we can import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.helpers import trigger_chat_generation

def main():
    if len(sys.argv) < 2:
        print("Usage: python job_flag_helper.py <script1_path> <script2_path> ...")
        sys.exit(1)

    # Arguments are script paths (e.g., 'scripts/my_script.py')
    # We expect flags to be named based on the script name: 'my_script.txt'
    scripts = sys.argv[1:]
    expected_flags = []

    for s in scripts:
        script_name = os.path.basename(s)
        # e.g., 'my_script.py' -> 'my_script.txt'
        flag_name = os.path.splitext(script_name)[0] + ".txt"
        expected_flags.append(flag_name)

    flags_dir = "global_flags/job_flags"
    ready_flag = "global_flags/job_ready.flag"

    print(f"[Helper] Waiting for flags: {expected_flags} in {flags_dir}")

    # Wait for all flags
    while True:
        all_found = True
        for flag in expected_flags:
            flag_path = os.path.join(flags_dir, flag)
            if not os.path.exists(flag_path):
                all_found = False
                break

            # Optionally check if it contains '1'
            with open(flag_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content != "1":
                    all_found = False
                    break

        if all_found:
            break

        time.sleep(1) # Poll every second

    print(f"[Helper] All script flags found. Flipping main ready flag.")

    # Cleanup script flags
    import shutil
    if os.path.exists(flags_dir):
        shutil.rmtree(flags_dir)

    # Flip main flag
    with open(ready_flag, "w", encoding="utf-8") as f:
        f.write("1")

    # Get the trigger text
    trigger_text = "##JOB_START##"
    trigger_file = os.path.join("runtime", "jobs", "trigger.txt")
    if os.path.exists(trigger_file):
        with open(trigger_file, "r", encoding="utf-8") as f:
            trigger_text = f.read().strip() or "##JOB_START##"

    # The user said the trigger sender should just inject a chat_trigger.txt like the system expects.
    # So we call trigger_chat_generation here when everything is ready.
    print("[Helper] Scripts finished, triggering job start.")
    filepath, filename = trigger_chat_generation(trigger_text)
    print(f"[Helper] Triggered execution with file: {filepath}")

    print(f"[Helper] Done. Exiting.")

if __name__ == "__main__":
    main()
