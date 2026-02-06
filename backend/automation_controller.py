import os
import sys
import json
import shutil
import time
import subprocess
import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List
from backend.utils import SimpleFileLock

@dataclass
class Job:
    name: str
    priority: int = 100
    when: str = "now"
    args: Dict[str, Any] = field(default_factory=dict)
    prompt: str = ""
    scripts: List[str] = field(default_factory=list)

class AutomationController:
    def __init__(self, job_definitions_path: str = "automation/jobs", queue_path: str = "automation/job_queue.json"):
        self.job_definitions_path = Path(job_definitions_path)
        self.queue_path = Path(queue_path)
        self.queue_lock_path = self.queue_path.with_suffix(f"{self.queue_path.suffix}.lock")
        self.history_path = Path("automation/job_history.json")
        self.scripts_path = Path("automation/job_scripts")
        self.job_definitions = {}

        # Ensure Dirs
        self.job_definitions_path.mkdir(parents=True, exist_ok=True)
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.scripts_path.mkdir(parents=True, exist_ok=True)

        self._load_job_definitions()
        if not self.queue_path.exists():
            self._write_queue_unsafe([])

    def _load_job_definitions(self):
        jobs_json_path = self.job_definitions_path / "jobs.json"
        if not jobs_json_path.exists():
            self._create_default_jobs()
            return
        try:
            with open(jobs_json_path, 'r', encoding='utf-8') as f:
                self.job_definitions = json.load(f)
        except (json.JSONDecodeError, IOError):
            self.job_definitions = {}

    def _create_default_jobs(self):
        default_jobs = {
            "summary_job": {"instructions": "Create a concise summary."},
            "keyword_job": {"instructions": "Extract keywords as JSON."}
        }
        self.job_definitions = default_jobs
        try:
            with open(self.job_definitions_path / "jobs.json", 'w', encoding='utf-8') as f:
                json.dump(self.job_definitions, f, indent=2)
        except IOError: pass

    def _read_queue_unsafe(self) -> List[Dict]:
        try:
            if self.queue_path.exists() and self.queue_path.stat().st_size > 0:
                with open(self.queue_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except: pass
        return []

    def _write_queue_unsafe(self, queue_data: List[Dict]):
        try:
            temp_path = self.queue_path.with_suffix(f"{self.queue_path.suffix}.tmp")
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(queue_data, f, indent=2)
            shutil.move(temp_path, self.queue_path)
        except OSError: pass

    def save_job_definition(self, job_name: str, instructions: str, trigger: str = "", scripts: List[str] = None):
        job_data = {"instructions": instructions, "trigger": trigger, "scripts": scripts or []}
        path = self.job_definitions_path / "jobs.json"
        lock = path.with_suffix('.json.lock')
        try:
            with SimpleFileLock(lock):
                if path.exists():
                    with open(path, 'r', encoding='utf-8') as f: all_jobs = json.load(f)
                else: all_jobs = {}
                all_jobs[job_name] = job_data
                with open(path, 'w', encoding='utf-8') as f: json.dump(all_jobs, f, indent=2)
            self.job_definitions[job_name] = job_data
        except Exception: pass

    def delete_job_definition(self, job_name: str):
        path = self.job_definitions_path / "jobs.json"
        lock = path.with_suffix('.json.lock')
        try:
            with SimpleFileLock(lock):
                if path.exists():
                    with open(path, 'r', encoding='utf-8') as f: all_jobs = json.load(f)
                    if job_name in all_jobs:
                        del all_jobs[job_name]
                        with open(path, 'w', encoding='utf-8') as f: json.dump(all_jobs, f, indent=2)
            if job_name in self.job_definitions:
                del self.job_definitions[job_name]
        except Exception: pass

    def add_job(self, name: str, priority: int = 100, when: str = "now", args: Optional[Dict[str, Any]] = None, job_id: Optional[str] = None):
        if name not in self.job_definitions: return
        new_job = {
            "id": job_id if job_id else f"job_{int(time.time()*1000)}",
            "name": name, "priority": priority, "when": when, "args": args or {}
        }
        try:
            with SimpleFileLock(self.queue_lock_path):
                q = self._read_queue_unsafe()
                q.append(new_job)
                self._write_queue_unsafe(q)
        except TimeoutError: pass

    def get_queue(self) -> List[Dict]:
        try:
            with SimpleFileLock(self.queue_lock_path): return self._read_queue_unsafe()
        except TimeoutError: return []

    def remove_job_from_queue(self, job_id: str):
        try:
            with SimpleFileLock(self.queue_lock_path):
                q = self._read_queue_unsafe()
                self._write_queue_unsafe([j for j in q if j.get("id") != job_id])
        except TimeoutError: pass

    def get_next_due_job(self) -> Optional[Job]:
        try:
            with SimpleFileLock(self.queue_lock_path):
                q = self._read_queue_unsafe()
                if not q: return None
                now = datetime.datetime.now()
                due_idx = -1
                for i, job in enumerate(q):
                    when = job.get("when", "now")
                    if when == "now":
                        due_idx = i; break
                    try:
                        dt = datetime.datetime.fromisoformat(when.replace("Z", "+00:00"))
                        # Naive check
                        if dt.tzinfo is None: dt = dt.replace(tzinfo=None) # Simple
                        if dt <= now: due_idx = i; break
                    except: due_idx = i; break # Fail safe

                if due_idx != -1:
                    j = q.pop(due_idx)
                    self._write_queue_unsafe(q)

                    # Construct
                    jd = self.job_definitions.get(j["name"], {})
                    instr = jd.get("instructions", "")
                    for k,v in j.get("args", {}).items():
                        instr = instr.replace(f"{{{k}}}", str(v))

                    return Job(
                        name=j["name"], priority=j.get("priority", 100),
                        when=j.get("when", "now"), args=j.get("args", {}),
                        prompt=instr, scripts=jd.get("scripts", [])
                    )
                return None
        except TimeoutError: return None

    def get_available_scripts(self) -> List[str]:
        if not self.scripts_path.exists(): return []
        return sorted([f.name for f in self.scripts_path.glob("*.py")])

    def execute_job_scripts(self, job: Job) -> Dict[str, Any]:
        results = []
        all_success = True
        for sname in job.scripts:
            spath = self.scripts_path / sname
            if not spath.exists():
                results.append({"script": sname, "status": "error", "message": "Not found"})
                all_success = False; break
            try:
                cmd = [sys.executable, str(spath), job.prompt]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=60, encoding='utf-8')
                status = "success" if res.returncode == 0 else "failed"
                results.append({
                    "script": sname, "status": status,
                    "code": res.returncode, "stdout": res.stdout, "stderr": res.stderr
                })
                if status == "failed":
                    all_success = False; break
            except Exception as e:
                results.append({"script": sname, "status": "error", "message": str(e)})
                all_success = False; break

        final = "success" if all_success else "failed"
        self.log_job_history(job.name, results, final)
        return {"status": final, "results": results}

    def log_job_history(self, job_name: str, results: List[Dict], status: str, filepath: str = None):
        entry = {
            "id": f"hist_{int(time.time()*1000)}",
            "job_name": job_name, "timestamp": datetime.datetime.now().isoformat(),
            "status": status, "scripts_run": len(results), "details": results
        }
        if filepath: entry["filepath"] = filepath
        try:
            hist = []
            if self.history_path.exists():
                with open(self.history_path, 'r', encoding='utf-8') as f: hist = json.load(f)
            hist.insert(0, entry)
            if len(hist) > 100: hist = hist[:100]
            with open(self.history_path, 'w', encoding='utf-8') as f: json.dump(hist, f, indent=2)
        except Exception: pass

    def get_job_history(self) -> List[Dict]:
        if not self.history_path.exists(): return []
        try:
            with open(self.history_path, 'r', encoding='utf-8') as f: return json.load(f)
        except: return []

    def clear_job_history(self):
        try:
            with open(self.history_path, 'w', encoding='utf-8') as f: json.dump([], f)
            # Clear output
            for f in Path("jobs").glob("*.txt"):
                try: f.unlink()
                except: pass
        except: pass

    def get_cycles(self):
        path = self.job_definitions_path / "cycles.json"
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f: return json.load(f)
            except: pass
        return {}

    def save_cycle(self, name, triggers):
        path = self.job_definitions_path / "cycles.json"
        try:
            cycles = self.get_cycles()
            cycles[name] = {"triggers": triggers}
            with open(path, 'w', encoding='utf-8') as f: json.dump(cycles, f, indent=2)
        except: pass

    def delete_cycle(self, name):
        path = self.job_definitions_path / "cycles.json"
        try:
            cycles = self.get_cycles()
            if name in cycles:
                del cycles[name]
                with open(path, 'w', encoding='utf-8') as f: json.dump(cycles, f, indent=2)
        except: pass

# Global Instance
automation_controller = AutomationController()
