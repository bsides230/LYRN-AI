import argparse
import sys
import os
import json
import datetime
import uuid

# Add parent dir to path so we can import services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import job_registry

def log_run(category: str, job_name: str, trigger_name: str, status: str, error: str = ""):
    log_entry = {
        "run_id": str(uuid.uuid4()),
        "timestamp": datetime.datetime.now().isoformat(),
        "category": category,
        "job_name": job_name,
        "trigger_name": trigger_name,
        "status": status,
        "error": error
    }
    with open("runtime/jobs/job_runs.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")

def main():
    parser = argparse.ArgumentParser(description="Inject a job into the LYRN model runner.")
    parser.add_argument("--category", required=True, help="Job category")
    parser.add_argument("--job-name", required=True, help="Job name")

    args = parser.parse_args()

    job = job_registry.get_job_by_name(args.category, args.job_name)

    if not job:
        print(f"Error: Job '{args.job_name}' not found in category '{args.category}'.")
        log_run(args.category, args.job_name, "", "failed", "job_not_found")
        sys.exit(1)

    if not job["enabled"]:
        print(f"Error: Job '{args.job_name}' is disabled.")
        log_run(args.category, args.job_name, job["trigger_name"], "failed", "job_disabled")
        sys.exit(1)

    try:
        # Write instruction layer
        os.makedirs("global_flags", exist_ok=True)
        with open("global_flags/job_context.txt", "w", encoding="utf-8") as f:
            f.write(job["instruction_layer"])

        print("[System] Wrote global_flags/job_context.txt")

        # Trigger model execution using existing system
        # We need to write the tiny trigger to a chat file and then write to chat_trigger.txt
        from utils.helpers import trigger_chat_generation

        # This writes the trigger_name as user message and triggers it
        filepath, filename = trigger_chat_generation(job["trigger_name"])
        print(f"[System] Triggered execution with file: {filepath}")

        log_run(args.category, args.job_name, job["trigger_name"], "success")

    except Exception as e:
        print(f"Error injecting job: {e}")
        log_run(args.category, args.job_name, job.get("trigger_name", ""), "failed", str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
