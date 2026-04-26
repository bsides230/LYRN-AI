import os
import csv
import uuid
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

JOBS_DIR = Path("runtime/jobs/categories")
JOBS_DIR.mkdir(parents=True, exist_ok=True)

CSV_FIELDNAMES = [
    "job_id",
    "job_name",
    "trigger_name",
    "instruction_layer",
    "enabled",
    "created_at",
    "updated_at",
    "notes"
]

def _get_category_path(category: str) -> Path:
    # Ensure category name is safe
    safe_category = "".join(c for c in category if c.isalnum() or c in ("_", "-"))
    return JOBS_DIR / f"{safe_category}.csv"

def get_categories() -> List[str]:
    categories = []
    if not JOBS_DIR.exists():
        return categories
    for file in JOBS_DIR.glob("*.csv"):
        categories.append(file.stem)
    return sorted(categories)

def create_category(category: str) -> bool:
    path = _get_category_path(category)
    if path.exists():
        return False

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
    return True

def get_jobs(category: str) -> List[Dict[str, Any]]:
    path = _get_category_path(category)
    if not path.exists():
        return []

    jobs = []
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse boolean
            row["enabled"] = row["enabled"].lower() == "true"
            jobs.append(row)
    return jobs

def get_job_by_name(category: str, job_name: str) -> Optional[Dict[str, Any]]:
    jobs = get_jobs(category)
    for job in jobs:
        if job["job_name"] == job_name:
            return job
    return None

def save_job(category: str, job_data: Dict[str, Any]) -> Dict[str, Any]:
    path = _get_category_path(category)

    # Auto-create category if missing
    if not path.exists():
        create_category(category)

    jobs = get_jobs(category)
    now = datetime.datetime.now().isoformat()

    # Check if updating or creating
    existing_idx = -1
    if "job_id" in job_data and job_data["job_id"]:
        for i, j in enumerate(jobs):
            if j["job_id"] == job_data["job_id"]:
                existing_idx = i
                break
    else:
        # Check by name for collision
        for i, j in enumerate(jobs):
            if j["job_name"] == job_data.get("job_name"):
                existing_idx = i
                break

    if existing_idx >= 0:
        # Update
        existing_job = jobs[existing_idx]
        existing_job["job_name"] = job_data.get("job_name", existing_job["job_name"])
        existing_job["trigger_name"] = job_data.get("trigger_name", existing_job["trigger_name"])
        existing_job["instruction_layer"] = job_data.get("instruction_layer", existing_job["instruction_layer"])
        existing_job["enabled"] = str(job_data.get("enabled", existing_job["enabled"])).lower() == "true"
        existing_job["updated_at"] = now
        existing_job["notes"] = job_data.get("notes", existing_job.get("notes", ""))
        jobs[existing_idx] = existing_job
        saved_job = existing_job
    else:
        # Create
        new_job = {
            "job_id": str(uuid.uuid4()),
            "job_name": job_data.get("job_name", ""),
            "trigger_name": job_data.get("trigger_name", ""),
            "instruction_layer": job_data.get("instruction_layer", ""),
            "enabled": str(job_data.get("enabled", True)).lower() == "true",
            "created_at": now,
            "updated_at": now,
            "notes": job_data.get("notes", "")
        }
        jobs.append(new_job)
        saved_job = new_job

    # Write back to CSV
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for j in jobs:
            # Ensure enabled is string for CSV
            row = dict(j)
            row["enabled"] = "true" if j["enabled"] else "false"
            writer.writerow(row)

    return saved_job
