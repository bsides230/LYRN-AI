import argparse
import sys
import os
import re
import uuid
import json
import datetime
import subprocess
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services import job_registry


def log_parse(run_id: str, status: str, parsed_result: str, file_path: str, errors: list = None):
    log_entry = {
        "run_id": run_id,
        "timestamp": datetime.datetime.now().isoformat(),
        "status": status,
        "file_path": file_path,
        "parsed_result": parsed_result,
        "errors": errors or []
    }
    log_file = PROJECT_ROOT / "runtime" / "jobs" / "job_parse_log.jsonl"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Parse and validate a job response.")
    parser.add_argument("--category", required=True, help="Job category")
    parser.add_argument("--job-name", required=True, help="Job name")
    parser.add_argument("--response-file", required=True, help="Path to raw model output file")
    parser.add_argument("--retry-count", type=int, default=0, help="Current retry count")
    parser.add_argument("--no-auto-inject", action="store_true", help="Parse and validate without automatically chaining to inject_job")

    args = parser.parse_args()

    auto_chain = not args.no_auto_inject and os.environ.get("LYRN_NO_AUTO_CHAIN") != "1"

    resp_file = Path(args.response_file)
    if not resp_file.exists():
        print(f"Error: Response file {args.response_file} not found.", file=sys.stderr)
        sys.exit(1)

    job = job_registry.get_job_by_name(args.category, args.job_name)
    if not job:
        print(f"Error: Job '{args.job_name}' not found in category '{args.category}'.", file=sys.stderr)
        sys.exit(1)

    affordances_str = job.get("affordances", "")
    affordances_allowed = [a.strip() for a in affordances_str.split("|") if a.strip() and a.strip().lower() != "none"]
    max_retries = int(job.get("max_retries", 1))

    raw_text = resp_file.read_text(encoding="utf-8")

    # Affordance Extraction
    affordance_matches = re.findall(r"##AF:\s*([^#]+)##", raw_text)
    trigger_found = affordance_matches[-1].strip() if affordance_matches else None

    is_valid = True
    errors = []

    next_category = None
    next_job = None

    if trigger_found:
        if not affordances_allowed or trigger_found in affordances_allowed:
            parts = trigger_found.split("/")
            if len(parts) >= 2:
                next_category = parts[0]
                next_job = parts[1]
            else:
                is_valid = False
                errors.append(f"Trigger '{trigger_found}' is not in 'Category/JobName' format.")
        else:
            is_valid = False
            errors.append(f"Trigger '{trigger_found}' is not in allowed affordances list: {affordances_allowed}")
    elif affordances_allowed:
        # Affordances were expected but none emitted
        is_valid = False
        errors.append(f"No valid affordance trigger found in output. Expected one of: {affordances_allowed}")

    run_id = str(uuid.uuid4())
    out_dir = PROJECT_ROOT / "runtime" / "jobs" / "parsed_outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{run_id}.txt"

    if is_valid:
        out_file.write_text(f"Parsed Trigger: {trigger_found}\nRaw Content Length: {len(raw_text)}\n", encoding="utf-8")
        log_parse(run_id, "success", trigger_found or "completed", str(out_file))
        print(f"[Success] Valid completion parsed. Trigger: '{trigger_found}'.")

        # Automatically trigger inject_job for next job if specified
        if auto_chain and next_category and next_job:
            inject_script = PROJECT_ROOT / "scripts" / "inject_job.py"
            print(f"[Parser] Triggering next job: {next_category}/{next_job}")
            subprocess.Popen([
                sys.executable,
                str(inject_script),
                "--category", next_category,
                "--job-name", next_job
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)

    else:
        status = "retry" if args.retry_count < max_retries else "failed"
        out_file.write_text(f"Status: {status}\nErrors: {errors}\n", encoding="utf-8")
        log_parse(run_id, status, str(errors), str(out_file), errors=errors)
        print(f"[{status.capitalize()}] Validation failed. Errors: {errors}")

        if auto_chain and status == "retry":
            print(f"[Parser] Retrying job '{args.category}/{args.job_name}' (attempt {args.retry_count + 1}/{max_retries})...")
            inject_script = PROJECT_ROOT / "scripts" / "inject_job.py"
            subprocess.Popen([
                sys.executable,
                str(inject_script),
                "--category", args.category,
                "--job-name", args.job_name,
                "--retry-count", str(args.retry_count + 1)
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
