import sys
import json
import time
import os
from pathlib import Path

def main():
    print("--- route_chat.py executed ---")

    # We queue the final chat_response_job.
    # To do this safely, we append to the queue.json file like the automation controller does.
    queue_path = Path("automation/job_queue.json")
    queue_lock_path = queue_path.with_suffix(f"{queue_path.suffix}.lock")

    from file_lock import SimpleFileLock

    new_job_dict = {
        "id": f"job_{int(time.time()*1000)}",
        "name": "chat_response_job",
        "priority": 100,
        "when": "now",
        "args": {}
    }

    try:
        with SimpleFileLock(queue_lock_path):
            queue_data = []
            if queue_path.exists() and queue_path.stat().st_size > 0:
                with open(queue_path, 'r', encoding='utf-8') as f:
                    try:
                        queue_data = json.load(f)
                    except json.JSONDecodeError:
                        pass

            queue_data.append(new_job_dict)

            temp_path = queue_path.with_suffix(f"{queue_path.suffix}.tmp")
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(queue_data, f, indent=2)
            os.replace(temp_path, queue_path)

        print("Successfully queued chat_response_job.")
    except Exception as e:
        print(f"Failed to queue chat_response_job: {e}")

    # Return success so the job completes
    sys.exit(0)

if __name__ == "__main__":
    # We must ensure we can import SimpleFileLock from the root
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    main()
