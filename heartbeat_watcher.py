import os
import re
import time
import json
import shutil
from pathlib import Path
from datetime import datetime
import uuid
from file_lock import SimpleFileLock
from affordance_manager import AffordanceManager

# --- Configuration ---
WATCH_DIR = Path("automation/heartbeat_outputs")
CHAT_LOG_DIR = Path("chat") # Directory where structured chat logs are saved
SUMMARY_FILE = Path("memory/conversation_summary.txt")
DELTAS_DIR = Path("deltas")
JOB_QUEUE_FILE = Path("automation/job_queue.json")
WATCH_INTERVAL_SECONDS = 2

# --- Helper Functions ---

def create_delta_file(scope: str, target: str, op: str, path: str, value: str, value_mode: str = "RAW"):
    """
    A standalone function to create a delta file.
    Mirrors the core logic of the DeltaManager.
    """
    now = datetime.utcnow()
    date_path = DELTAS_DIR / now.strftime("%Y/%m/%d")
    date_path.mkdir(parents=True, exist_ok=True)

    delta_id = f"delta_{now.strftime('%Y%m%dT%H%M%S%f')}_{uuid.uuid4().hex[:8]}"
    delta_filename = f"{delta_id}.txt"
    delta_filepath = date_path / delta_filename

    delta_content = f"DELTA|{scope}|{target}|{op}|{path}|{value_mode}|{value}"

    # Crash-safe write
    temp_filepath = delta_filepath.with_suffix(f".tmp.{uuid.uuid4().hex}")
    try:
        with open(temp_filepath, 'w', encoding='utf-8') as f:
            f.write(delta_content)
            f.flush()
            os.fsync(f.fileno())
        os.rename(temp_filepath, delta_filepath)
        print(f"[Watcher] Created delta: {delta_filepath}")
    except Exception as e:
        print(f"[Watcher] Error creating delta file: {e}")
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)

def add_job_to_queue(name: str, priority: str, when: str, args: str):
    """
    Appends a new job to the shared job queue JSON file in a process-safe manner.
    """
    lock_path = JOB_QUEUE_FILE.with_suffix(".lock")
    try:
        with SimpleFileLock(lock_path):
            queue_data = []
            if JOB_QUEUE_FILE.exists() and JOB_QUEUE_FILE.stat().st_size > 0:
                with open(JOB_QUEUE_FILE, 'r', encoding='utf-8') as f:
                    try:
                        queue_data = json.load(f)
                    except json.JSONDecodeError:
                        print(f"[Watcher] Warning: Job queue file {JOB_QUEUE_FILE} is corrupted. Starting fresh.")
                        queue_data = []

            new_job = {
                "name": name,
                "priority": priority,
                "when": when,
                "args": json.loads(args) if args.strip().startswith('{') else args
            }
            queue_data.append(new_job)

            # Use a temporary file for atomic write inside the lock
            temp_queue_file = JOB_QUEUE_FILE.with_suffix(".tmp")
            with open(temp_queue_file, 'w', encoding='utf-8') as f:
                json.dump(queue_data, f, indent=2)
            shutil.move(temp_queue_file, JOB_QUEUE_FILE)

            print(f"[Watcher] Added job to queue: {name}")

    except (TimeoutError, IOError) as e:
        print(f"[Watcher] Error adding job to queue: {e}")


def run_affordance(affordance_name: str, text_content: str, affordance_manager: AffordanceManager) -> Optional[str]:
    """
    Runs a specific affordance, parsing the text_content to find the block
    between start and end triggers and saves it to the specified file.
    Returns the path to the output file on success, None on failure.
    """
    affordance = affordance_manager.get_affordance(affordance_name)
    if not affordance:
        print(f"[Watcher] Error: Affordance '{affordance_name}' not found.")
        return None

    try:
        start_index = text_content.find(affordance.start_trigger)
        if start_index == -1:
            print(f"Start trigger '{affordance.start_trigger}' not found for affordance '{affordance_name}'.")
            return None
        start_index += len(affordance.start_trigger)

        end_index = text_content.find(affordance.end_trigger, start_index)
        if end_index == -1:
            print(f"End trigger '{affordance.end_trigger}' not found for affordance '{affordance_name}'.")
            return None

        extracted_content = text_content[start_index:end_index].strip()

        output_dir = Path(affordance.output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_filepath = output_dir / affordance.output_filename
        with open(output_filepath, 'w', encoding='utf-8') as f:
            f.write(extracted_content)

        print(f"[Watcher] Successfully ran affordance '{affordance_name}'. Output: {output_filepath}")
        return str(output_filepath)

    except Exception as e:
        print(f"[Watcher] Error running affordance '{affordance_name}': {e}")
        return None

def process_heartbeat_file(filepath: Path, affordance_manager: AffordanceManager):
    """
    Reads a heartbeat file, parses it, and performs the required file operations.
    """
    print(f"[Watcher] Processing heartbeat file: {filepath.name}")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Simple regex to get all blocks
        block_pattern = re.compile(r"###(HB_\w+)_START###\s*(.*?)\s*###_END###", re.DOTALL)
        blocks = {name: data.strip() for name, data in block_pattern.findall(content)}

        # --- Process Conversation Summary Delta ---
        summary_key = "HB_CONVERSATION_SUMMARY_DELTA_START"
        if summary_key in blocks and blocks[summary_key]:
            summary_delta = blocks[summary_key]
            SUMMARY_FILE.parent.mkdir(exist_ok=True)
            with open(SUMMARY_FILE, 'a', encoding='utf-8') as f:
                f.write(summary_delta + "\n")
            print(f"[Watcher] Appended to {SUMMARY_FILE}")

        # --- Process Memory Deltas ---
        memory_key = "HB_MEMORY_DELTAS_START"
        if "HB_MEMORY_START" in blocks: # Support old key for now
            memory_key = "HB_MEMORY_START"

        if memory_key in blocks and blocks[memory_key]:
            memory_deltas = blocks[memory_key]
            for line in memory_deltas.split('\n'):
                line = line.strip()
                if not line or not line.upper().startswith("DELTA|"):
                    continue
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 6:
                    # Handle value that might contain the delimiter
                    value = '|'.join(parts[5:])
                    _, scope, target, op, path = parts[:5]
                    create_delta_file(scope, target, op, path, value, "RAW") # Mode is simplified for now

        # --- Process Automation Triggers ---
        automation_key = "HB_AUTOMATION_TRIGGERS_START"
        if "HB_ACTIONS_START" in blocks: # Also check for generic actions block
            automation_key = "HB_ACTIONS_START"

        if automation_key in blocks and blocks[automation_key]:
            automation_triggers = blocks[automation_key]
            chat_pair_id = blocks.get("HB_META_START", "").split("CHAT_PAIR_ID:")[1].split("\n")[0].strip()

            for line in automation_triggers.split('\n'):
                line = line.strip()
                if line.upper().startswith("JOB|"):
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) == 4: # JOB|name|priority|when|args - simplify for now
                        _, name, priority, args_str = parts
                        add_job_to_queue(name, priority, "now", args_str)
                elif line.upper().startswith("AFFORD|"):
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 2:
                        affordance_name = parts[1]
                        if not chat_pair_id:
                            print(f"[Watcher] Cannot run affordance '{affordance_name}', CHAT_PAIR_ID not found in heartbeat.")
                            continue

                        # The chat pair ID is like "cp_YYYY-MM-DDTHH-MM-SSZ_xxxx"
                        # The structured logger is like "chat_YYYYMMDD_HHMMSS_ffffff.txt"
                        # We need to find the corresponding file.
                        # This is a simplification; a real system might need a more robust lookup.
                        try:
                            # Extract timestamp from cp_YYYY-MM-DDTHH-MM-SSZ_xxxx
                            hb_timestamp_str = chat_pair_id.split('_')[1].split('Z')[0]
                            hb_dt = datetime.strptime(hb_timestamp_str, "%Y-%m-%dT%H-%M-%S")

                            # Look for a file in that same second
                            best_match = None
                            min_diff = float('inf')
                            for log_file in CHAT_LOG_DIR.glob("chat_*.txt"):
                                log_ts_str = log_file.stem.split('_')[1]
                                log_dt = datetime.strptime(log_ts_str, "%Y%m%d")
                                if log_dt.date() == hb_dt.date(): # At least check the same day for performance
                                    log_full_dt = datetime.strptime(log_file.stem.split('_')[1] + '_' + log_file.stem.split('_')[2], "%Y%m%d_%H%M%S_%f")
                                    time_diff = abs((log_full_dt - hb_dt).total_seconds())
                                    if time_diff < min_diff and time_diff < 5: # Allow a 5-second window
                                        min_diff = time_diff
                                        best_match = log_file

                            if best_match:
                                with open(best_match, 'r', encoding='utf-8') as f_chat:
                                    chat_content = f_chat.read()
                                run_affordance(affordance_name, chat_content, affordance_manager)
                            else:
                                print(f"[Watcher] Could not find a matching chat log for CHAT_PAIR_ID: {chat_pair_id}")

                        except Exception as e:
                            print(f"[Watcher] Error processing affordance trigger: {e}")


        # Finally, delete the processed file
        os.remove(filepath)
        print(f"[Watcher] Deleted processed file: {filepath.name}")

    except Exception as e:
        print(f"[Watcher] Failed to process {filepath.name}: {e}")
        error_dir = WATCH_DIR / "error"
        error_dir.mkdir(exist_ok=True)
        shutil.move(str(filepath), str(error_dir / filepath.name))


def main():
    """Main watch loop."""
    print("[Watcher] Starting Heartbeat Watcher...")
    WATCH_DIR.mkdir(parents=True, exist_ok=True)
    CHAT_LOG_DIR.mkdir(parents=True, exist_ok=True)

    affordance_manager = AffordanceManager()

    print(f"[Watcher] Watching directory: {WATCH_DIR.resolve()}")

    while True:
        try:
            files = sorted(
                (p for p in WATCH_DIR.glob("*.txt")),
                key=lambda p: p.stat().st_mtime
            )

            if files:
                process_heartbeat_file(files[0], affordance_manager)

            time.sleep(WATCH_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print("[Watcher] Shutting down.")
            break
        except Exception as e:
            print(f"[Watcher] An unexpected error occurred: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
