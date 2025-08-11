import os
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List

@dataclass
class WatcherJob:
    """Represents a single watcher job."""
    name: str
    start_trigger: str
    end_trigger: str
    output_path: str
    output_filename: str

class JobWatcherManager:
    """Manages watcher jobs that parse text between triggers."""
    def __init__(self, jobs_path: str = "automation/watcher_jobs.json"):
        self.jobs_path = Path(jobs_path)
        self.jobs: Dict[str, WatcherJob] = {}
        self.jobs_path.parent.mkdir(parents=True, exist_ok=True)
        self.load_jobs()

    def load_jobs(self):
        """Loads watcher jobs from the JSON file."""
        if not self.jobs_path.exists():
            self.jobs = {}
            return

        try:
            with open(self.jobs_path, 'r', encoding='utf-8') as f:
                jobs_data = json.load(f)
                for name, data in jobs_data.items():
                    self.jobs[name] = WatcherJob(**data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading watcher jobs: {e}")
            self.jobs = {}

    def save_jobs(self):
        """Saves all current watcher jobs to the JSON file."""
        try:
            jobs_data = {name: job.__dict__ for name, job in self.jobs.items()}
            with open(self.jobs_path, 'w', encoding='utf-8') as f:
                json.dump(jobs_data, f, indent=2)
        except IOError as e:
            print(f"Error saving watcher jobs: {e}")

    def add_job(self, job: WatcherJob):
        """Adds or updates a watcher job."""
        self.jobs[job.name] = job
        self.save_jobs()

    def delete_job(self, job_name: str):
        """Deletes a watcher job."""
        if job_name in self.jobs:
            del self.jobs[job_name]
            self.save_jobs()

    def get_job(self, job_name: str) -> Optional[WatcherJob]:
        """Retrieves a single watcher job by name."""
        return self.jobs.get(job_name)

    def get_all_jobs(self) -> List[WatcherJob]:
        """Returns a list of all watcher jobs."""
        return list(self.jobs.values())

    def run_job(self, job_name: str, text_content: str) -> Optional[str]:
        """
        Runs a specific job, parsing the text_content to find the block
        between start and end triggers and saves it to the specified file.
        Returns the path to the output file on success, None on failure.
        """
        job = self.get_job(job_name)
        if not job:
            print(f"Error: Watcher job '{job_name}' not found.")
            return None

        try:
            # Simple string search to find the content
            start_index = text_content.find(job.start_trigger)
            if start_index == -1:
                print(f"Start trigger '{job.start_trigger}' not found.")
                return None

            start_index += len(job.start_trigger)

            end_index = text_content.find(job.end_trigger, start_index)
            if end_index == -1:
                print(f"End trigger '{job.end_trigger}' not found.")
                return None

            extracted_content = text_content[start_index:end_index].strip()

            # Ensure output path exists
            output_dir = Path(job.output_path)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Create the output file
            output_filepath = output_dir / job.output_filename
            with open(output_filepath, 'w', encoding='utf-8') as f:
                f.write(extracted_content)

            print(f"Successfully extracted content to {output_filepath}")
            return str(output_filepath)

        except Exception as e:
            print(f"Error running watcher job '{job_name}': {e}")
            return None
