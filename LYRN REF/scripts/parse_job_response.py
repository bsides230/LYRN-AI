import argparse
import sys
import os
import re
import uuid
import datetime
import subprocess

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services import job_registry

def log_parse(run_id: str, status: str, parsed_result: str, file_path: str):
    log_entry = {
        "run_id": run_id,
        "timestamp": datetime.datetime.now().isoformat(),
        "status": status,
        "file_path": file_path,
        "parsed_result": parsed_result
    }
    with open("runtime/jobs/job_parse_log.jsonl", "a", encoding="utf-8") as f:
        import json
        f.write(json.dumps(log_entry) + "\n")

def main():
    parser = argparse.ArgumentParser(description="Parse and validate a job response.")
    parser.add_argument("--category", required=True, help="Job category")
    parser.add_argument("--job-name", required=True, help="Job name")
    parser.add_argument("--response-file", required=True, help="Path to raw model output file")
    parser.add_argument("--retry-count", type=int, default=0, help="Current retry count")

    args = parser.parse_args()

    if not os.path.exists(args.response_file):
        print(f"Error: Response file {args.response_file} not found.")
        sys.exit(1)

    job = job_registry.get_job_by_name(args.category, args.job_name)
    if not job:
        print(f"Error: Job '{args.job_name}' not found in category '{args.category}'.")
        sys.exit(1)

    # The old logic read affordances_json, we now use the 'affordances' string.
    affordances_str = job.get("affordances", "")
    affordances_allowed = [a.strip() for a in affordances_str.split("|") if a.strip()]

    max_retries = int(job.get("max_retries", 1))

    with open(args.response_file, "r", encoding="utf-8") as f:
        raw_text = f.read()

    # We look for ##AF: Category/JobName##
    # The user format is `##AF: trigger##` meaning the model emits `##AF: Category/JobName##`
    match = re.search(r"##AF:\s*(.*?)\s*##", raw_text)

    is_valid = False
    errors = []
    trigger_found = None
    next_category = None
    next_job = None

    if match:
        trigger_found = match.group(1).strip()
        # Verify it's in the allowed list
        if not affordances_allowed or trigger_found in affordances_allowed:
            is_valid = True
            parts = trigger_found.split("/")
            if len(parts) >= 2:
                next_category = parts[0]
                next_job = parts[1]
            else:
                is_valid = False
                errors.append(f"Trigger '{trigger_found}' is not in 'Category/JobName' format.")
        else:
            errors.append(f"Trigger '{trigger_found}' is not in allowed affordances list: {affordances_allowed}")
    else:
        errors.append("No ##AF: trigger## found in the output.")

    run_id = str(uuid.uuid4())
    os.makedirs("runtime/jobs/parsed_outputs", exist_ok=True)
    out_file = f"runtime/jobs/parsed_outputs/{run_id}.txt"

    if is_valid:
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(f"Parsed Trigger: {trigger_found}\n")

        log_parse(run_id, "success", trigger_found, out_file)
        print(f"[Success] Valid trigger '{trigger_found}' parsed. Triggering next job.")

        # Call inject_job for the next job
        inject_script = os.path.join(os.path.dirname(__file__), "inject_job.py")
        subprocess.Popen([sys.executable, inject_script, "--category", next_category, "--job-name", next_job])

    else:
        if args.retry_count < max_retries:
            status = "retry"
        else:
            status = "failed"

        with open(out_file, "w", encoding="utf-8") as f:
            f.write(f"Status: {status}\nErrors: {errors}\n")

        log_parse(run_id, status, str(errors), out_file)
        print(f"[{status.capitalize()}] Validation failed. Errors: {errors}")

        # If it failed/retry, we might need to re-inject the current job
        # For now, we will print it. A robust system would call inject_job.py again if retry is needed.
        if status == "retry":
             print("[System] Attempting retry. Re-injecting current job.")
             inject_script = os.path.join(os.path.dirname(__file__), "inject_job.py")
             subprocess.Popen([sys.executable, inject_script, "--category", args.category, "--job-name", args.job_name])

if __name__ == "__main__":
    main()
