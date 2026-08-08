import sys
import os
import datetime
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs", "summary_logs")
DELTAS_LIVE_DIR = os.path.join(PROJECT_ROOT, "deltas", "live")

def main():
    if len(sys.argv) < 2:
        print("Usage: python summary_log_handler.py <path_to_handoff_file>")
        sys.exit(1)

    handoff_filepath = sys.argv[1]

    if not os.path.exists(handoff_filepath):
        print(f"[SummaryHandler] Error: Handoff file {handoff_filepath} not found.")
        sys.exit(1)

    try:
        # 1. Read timestamp and payload
        with open(handoff_filepath, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()

        if len(lines) < 2:
            print(f"[SummaryHandler] Error: Invalid handoff file format in {handoff_filepath}.")
            sys.exit(1)

        timestamp_str = lines[0].strip()
        payload = lines[1].strip()

        try:
            timestamp = datetime.datetime.fromisoformat(timestamp_str)
        except ValueError:
            timestamp = datetime.datetime.now()
            print(f"[SummaryHandler] Warning: Could not parse timestamp '{timestamp_str}'. Using current time.")

        # 2. Setup Daily Log DB Directory
        date_str = timestamp.strftime("%Y-%m-%d")
        daily_dir = os.path.join(LOGS_DIR, date_str)
        os.makedirs(daily_dir, exist_ok=True)

        # 3. Find the current summary_log_XXX.md file
        log_num = 1
        current_log_file = None
        entry_count = 0

        while True:
            filename = f"summary_log_{log_num:03d}.md"
            filepath = os.path.join(daily_dir, filename)

            if not os.path.exists(filepath):
                current_log_file = filepath
                entry_count = 0
                break

            # Count entries in existing file
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                count = content.count("### Entry ")

            if count < 100:
                current_log_file = filepath
                entry_count = count
                break

            log_num += 1

        # 4. Append to Daily Markdown Summary Log DB
        new_entry_num = entry_count + 1
        log_entry = f"\n### Entry {new_entry_num}\ntimestamp: {timestamp_str}\n\n{payload}\n"

        with open(current_log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)

        print(f"[SummaryHandler] Appended to {current_log_file}")

        # 5. Update DEL01
        os.makedirs(DELTAS_LIVE_DIR, exist_ok=True)
        del01_filepath = os.path.join(DELTAS_LIVE_DIR, "DEL01.txt")

        del01_content = f"##DEL01:START##{payload}##DEL01:END##\n"
        with open(del01_filepath, 'w', encoding='utf-8') as f:
            f.write(del01_content)

        print(f"[SummaryHandler] Updated {del01_filepath}")

        # 6. Trigger Delta Manifest Compiler
        compiler_script = os.path.join(SCRIPT_DIR, "compile_deltas.py")
        if os.path.exists(compiler_script):
            subprocess.run([sys.executable, compiler_script], check=True)
            print("[SummaryHandler] Triggered delta compiler.")
        else:
            print(f"[SummaryHandler] Error: Compiler script not found at {compiler_script}")

        # Optional: delete the handoff file after successful processing to prevent re-processing
        os.remove(handoff_filepath)

    except Exception as e:
        print(f"[SummaryHandler] Error processing summary log: {e}")

if __name__ == "__main__":
    main()
