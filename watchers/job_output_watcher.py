import argparse
import sys
import os
import re
import csv
import time
import datetime
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
CONTRACTS_FILE = os.path.join(SCRIPT_DIR, "job_output_contracts.tsv")
HANDOFF_DIR = os.path.join(SCRIPT_DIR, "handoff")
CHAT_DIR = os.path.join(PROJECT_ROOT, "chat") # Default chat dir

class JobOutputWatcherHandler(FileSystemEventHandler):
    def __init__(self, contract, on_success, on_fail):
        self.contract = contract
        self.on_success = on_success
        self.on_fail = on_fail
        self.processed_files = set()

    def on_modified(self, event):
        if event.is_directory:
            return

        # Only watch txt files in chat dir
        if not event.src_path.endswith('.txt'):
            return

        # We only want to process the file once per trigger run
        # if the end marker is found.
        self.check_file(event.src_path)

    def check_file(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            start_marker = self.contract['start_marker']
            end_marker = self.contract['end_marker']

            if start_marker in content and end_marker in content:
                print(f"[Watcher] Found markers in {filepath}")
                # Prevent multiple triggers from the same file update
                if filepath in self.processed_files:
                     return
                self.processed_files.add(filepath)

                # Extract payload
                start_idx = content.find(start_marker) + len(start_marker)
                end_idx = content.find(end_marker, start_idx)
                payload = content[start_idx:end_idx].strip()

                # Clean the payload (remove any newlines so it's one logical line)
                payload = payload.replace('\n', '').replace('\r', '')

                # Validate
                fields = payload.split(self.contract['delimiter'])
                expected_count = int(self.contract['field_count'])

                if len(fields) == expected_count:
                    print(f"[Watcher] Payload valid ({expected_count} fields). Exporting...")
                    self.on_success(payload)
                else:
                    print(f"[Watcher] Payload INVALID. Expected {expected_count} fields, got {len(fields)}.")
                    self.on_fail()
        except Exception as e:
            print(f"[Watcher] Error reading file {filepath}: {e}")


def load_contract(job_trigger):
    if not os.path.exists(CONTRACTS_FILE):
        print(f"Error: {CONTRACTS_FILE} not found.")
        sys.exit(1)

    with open(CONTRACTS_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row['job_trigger'] == job_trigger:
                return row
    return None

def main():
    parser = argparse.ArgumentParser(description="Generic Job Output Watcher")
    parser.add_argument("--job", required=True, help="Job trigger to watch for (e.g., summary/overall)")
    parser.add_argument("--chat-dir", default=CHAT_DIR, help="Directory to watch for model output")
    parser.add_argument("--retry-count", type=int, default=0, help="Current retry count")

    args = parser.parse_args()

    contract = load_contract(args.job)
    if not contract:
        print(f"Error: No contract found for job '{args.job}'.")
        sys.exit(1)

    print(f"[Watcher] Started for job: {args.job}")
    print(f"[Watcher] Contract: {contract}")

    max_retries = int(contract['retry_count'])

    def handle_success(payload):
        os.makedirs(HANDOFF_DIR, exist_ok=True)
        output_file_path = os.path.join(HANDOFF_DIR, contract['output_file'])
        timestamp = datetime.datetime.now().isoformat()

        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(f"{timestamp}\n")
            f.write(f"{payload}\n")

        print(f"[Watcher] Handoff file created: {output_file_path}")
        # Exit cleanly after successful extraction
        os._exit(0)

    def handle_fail():
        if args.retry_count < max_retries:
            print(f"[Watcher] Retrying job '{args.job}' ({args.retry_count + 1}/{max_retries})...")
            # Parse the job trigger into category and job name
            parts = args.job.split('/')
            if len(parts) == 2:
                category, job_name = parts
                inject_script = os.path.join(PROJECT_ROOT, "scripts", "inject_job.py")
                # Trigger the job injection for a retry
                subprocess.Popen([sys.executable, inject_script, "--category", category, "--job-name", job_name, "--retry-count", str(args.retry_count + 1)])
            else:
                print(f"[Watcher] Invalid job format for retry: {args.job}")
        else:
            print(f"[Watcher] Max retries reached for job '{args.job}'. Exiting.")
        os._exit(1)

    # Make sure watch dir exists
    if not os.path.exists(args.chat_dir):
        print(f"[Watcher] Chat directory {args.chat_dir} does not exist. Waiting for it...")
        os.makedirs(args.chat_dir, exist_ok=True)

    event_handler = JobOutputWatcherHandler(contract, handle_success, handle_fail)
    observer = Observer()
    observer.schedule(event_handler, args.chat_dir, recursive=False)
    observer.start()

    print(f"[Watcher] Watching directory: {args.chat_dir} for {contract['end_marker']}...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
