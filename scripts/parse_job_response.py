import argparse
import sys
import os
import json
import uuid
import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services import job_registry

def extract_json_from_text(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                return json.loads(text[start_idx:end_idx+1])
            except json.JSONDecodeError:
                pass
    return None

def log_parse(run_id: str, status: str, result_data: dict, file_path: str):
    log_entry = {
        "run_id": run_id,
        "timestamp": datetime.datetime.now().isoformat(),
        "status": status,
        "file_path": file_path,
        "parsed_result": result_data
    }
    with open("runtime/jobs/job_parse_log.jsonl", "a", encoding="utf-8") as f:
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

    try:
        affordances_allowed = json.loads(job.get("affordances_json", "[]"))
    except:
        affordances_allowed = ["continue", "retry", "flag_error"]

    max_retries = int(job.get("max_retries", 1))
    retry_error_message = job.get("retry_error_message", "Parser validation failed.")

    with open(args.response_file, "r", encoding="utf-8") as f:
        raw_text = f.read()

    parsed_json = extract_json_from_text(raw_text)

    errors = []
    is_valid = True

    if parsed_json is None:
        is_valid = False
        errors.append("Could not extract valid JSON from output.")
    else:
        if "status" not in parsed_json or parsed_json["status"] not in ["success", "retry", "failed"]:
            is_valid = False
            errors.append("Missing or invalid 'status'. Must be success, retry, or failed.")
        if "result" not in parsed_json:
            is_valid = False
            errors.append("Missing 'result' field.")
        if "available_affordances" not in parsed_json or not isinstance(parsed_json["available_affordances"], list):
            is_valid = False
            errors.append("Missing or invalid 'available_affordances'. Must be a list.")
        else:
            for aff in parsed_json["available_affordances"]:
                if aff not in affordances_allowed:
                    is_valid = False
                    errors.append(f"Affordance '{aff}' is not allowed by job definition.")
        if "errors" not in parsed_json or not isinstance(parsed_json["errors"], list):
            is_valid = False
            errors.append("Missing or invalid 'errors'. Must be a list.")

    run_id = str(uuid.uuid4())
    os.makedirs("runtime/jobs/parsed_outputs", exist_ok=True)
    out_file = f"runtime/jobs/parsed_outputs/{run_id}.json"

    if is_valid:
        # Save valid parsed output
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(parsed_json, f, indent=2)
        log_parse(run_id, "success", parsed_json, out_file)
        print(f"[Success] Valid output parsed and saved to {out_file}")
    else:
        if args.retry_count < max_retries:
            status = "retry"
            final_errors = errors
        else:
            status = "failed"
            final_errors = [retry_error_message] + errors

        err_out = {
            "status": status,
            "result": {},
            "available_affordances": ["flag_error"] if status == "failed" else ["retry"],
            "selected_affordance": "flag_error" if status == "failed" else "retry",
            "notes": "Parser validation failed.",
            "errors": final_errors
        }

        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(err_out, f, indent=2)

        log_parse(run_id, status, err_out, out_file)
        print(f"[{status.capitalize()}] Validation failed. Errors: {errors}")
        print(f"Output saved to {out_file}")

if __name__ == "__main__":
    main()
