import argparse
import sys
import os
import json
import datetime
import uuid

# Add parent dir to path so we can import services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import job_registry

def log_run(category: str, job_name: str, trigger_name: str, status: str, error: str = "", metadata: dict = None):
    if metadata is None:
        metadata = {}
    log_entry = {
        "run_id": str(uuid.uuid4()),
        "timestamp": datetime.datetime.now().isoformat(),
        "category": category,
        "job_name": job_name,
        "trigger_name": trigger_name,
        "status": status,
        "error": error,
        "metadata": metadata
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
        # 1. Write instruction and affordance layers
        os.makedirs("global_flags", exist_ok=True)
        job_context = f"##JI:START##\n{job['instruction_layer']}\n##JI:END##\n"
        job_context += f"##AF:START##\n{job.get('affordances', '')}\n##AF:END##\n"

        with open("global_flags/job_context.txt", "w", encoding="utf-8") as f:
            f.write(job_context)

        print("[System] Wrote global_flags/job_context.txt")

        # 2. Clear old flags
        flags_dir = "global_flags/job_flags"
        if os.path.exists(flags_dir):
            import shutil
            shutil.rmtree(flags_dir)
        os.makedirs(flags_dir, exist_ok=True)

        ready_flag = "global_flags/job_ready.flag"
        if os.path.exists(ready_flag):
            os.remove(ready_flag)

        # 3. Handle Scripts
        scripts_raw = job.get("scripts", "").strip()
        scripts_list = [s.strip() for s in scripts_raw.split("|") if s.strip()]

        def get_trigger_text():
            trigger_file = os.path.join("runtime", "jobs", "trigger.txt")
            if os.path.exists(trigger_file):
                with open(trigger_file, "r", encoding="utf-8") as f:
                    return f.read().strip() or "##JOB_START##"
            return "##JOB_START##"

        trigger_text = get_trigger_text()

        if not scripts_list:
            # No scripts to run, directly flip ready flag and trigger job
            print("[System] No scripts to run, flipping ready flag and triggering job.")
            with open(ready_flag, "w") as f:
                f.write("1")

            # Since there are no scripts, we trigger it immediately here
            from utils.helpers import trigger_chat_generation
            filepath, filename = trigger_chat_generation(trigger_text)
            print(f"[System] Triggered execution with file: {filepath}")
        else:
            print(f"[System] Starting {len(scripts_list)} scripts...")
            import subprocess

            valid_scripts = []
            # Start each script in the background
            for script in scripts_list:
                if os.path.exists(script):
                    subprocess.Popen([sys.executable, script])
                    print(f"  -> Started: {script}")
                    valid_scripts.append(script)
                else:
                    print(f"  -> Script not found, skipping: {script}")

            if not valid_scripts:
                # Fallback if no scripts were actually found
                print("[System] No valid scripts found to run, flipping ready flag and triggering job.")
                with open(ready_flag, "w") as f:
                    f.write("1")
                from utils.helpers import trigger_chat_generation
                filepath, filename = trigger_chat_generation(trigger_text)
                print(f"[System] Triggered execution with file: {filepath}")
            else:
                # Start job_flag_helper in the background
                helper_path = os.path.join(os.path.dirname(__file__), "job_flag_helper.py")
                subprocess.Popen([sys.executable, helper_path] + valid_scripts)
                print("[System] Started job_flag_helper.py to monitor script flags.")

        metadata = {
            "affordances": job.get("affordances", ""),
            "scripts": job.get("scripts", ""),
            "max_retries": job.get("max_retries", 1)
        }
        log_run(args.category, args.job_name, job["trigger_name"], "success", metadata=metadata)

    except Exception as e:
        print(f"Error injecting job: {e}")
        metadata = {
            "affordances": job.get("affordances", ""),
            "scripts": job.get("scripts", ""),
            "max_retries": job.get("max_retries", 1)
        }
        log_run(args.category, args.job_name, job.get("trigger_name", ""), "failed", str(e), metadata=metadata)
        sys.exit(1)

if __name__ == "__main__":
    main()
