import os
import re
import time
import json
from pathlib import Path
from datetime import datetime

# --- Configuration ---
WATCH_DIR = Path("../chat")
TASKS_DIR = Path("../build_prompt/tasks")
GOALS_DIR = Path("../build_prompt/goals")
WATCH_INTERVAL_SECONDS = 2
PROCESSED_FILES_LOG = Path("processed_files.log")

def ensure_dirs_exist():
    """Ensure the watch, tasks, and goals directories exist."""
    WATCH_DIR.mkdir(parents=True, exist_ok=True)
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    GOALS_DIR.mkdir(parents=True, exist_ok=True)

def get_processed_files() -> set:
    """Reads the list of already processed files."""
    if not PROCESSED_FILES_LOG.exists():
        return set()
    try:
        with open(PROCESSED_FILES_LOG, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    except IOError as e:
        print(f"[Watcher] Error reading processed files log: {e}")
        return set()

def add_to_processed_log(filename: str):
    """Adds a filename to the log of processed files."""
    try:
        with open(PROCESSED_FILES_LOG, 'a', encoding='utf-8') as f:
            f.write(filename + "\n")
    except IOError as e:
        print(f"[Watcher] Error writing to processed files log: {e}")

def update_index_file(directory: Path):
    """Scans a directory for .txt files and writes their names to an _index.json file."""
    try:
        index_path = directory / "_index.json"
        # The local index just needs the filenames. The master prompt builder will construct the full path.
        files = sorted([p.name for p in directory.glob("*.txt")])

        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(files, f, indent=2)
        print(f"[Watcher] Updated index file: {index_path}")
    except Exception as e:
        print(f"[Watcher] Error updating index file for {directory}: {e}")

def process_chat_file(filepath: Path) -> tuple[bool, bool]:
    """
    Reads a chat file, parses it, and saves tasks/goals.
    Returns a tuple indicating if (tasks_were_added, goals_were_added).
    """
    tasks_added = False
    goals_added = False
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Process Tasks
        task_pattern = re.compile(r"###TASK_START###(.*?)###TASK_END###", re.DOTALL)
        tasks = task_pattern.findall(content)
        if tasks:
            tasks_added = True
        for i, task_content in enumerate(tasks):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            task_filename = f"task_{timestamp}_{i+1}.txt"
            task_filepath = TASKS_DIR / task_filename
            with open(task_filepath, 'w', encoding='utf-8') as f_task:
                f_task.write(task_content.strip())
            print(f"[Watcher] Created task: {task_filepath}")

        # Process Goals
        goal_pattern = re.compile(r"###GOAL_START###(.*?)###GOAL_END###", re.DOTALL)
        goals = goal_pattern.findall(content)
        if goals:
            goals_added = True
        for i, goal_content in enumerate(goals):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            goal_filename = f"goal_{timestamp}_{i+1}.txt"
            goal_filepath = GOALS_DIR / goal_filename
            with open(goal_filepath, 'w', encoding='utf-8') as f_goal:
                f_goal.write(goal_content.strip())
            print(f"[Watcher] Created goal: {goal_filepath}")

        return tasks_added, goals_added

    except Exception as e:
        print(f"[Watcher] Failed to process {filepath.name}: {e}")
        return False, False

def main():
    """Main watch loop."""
    print("[Watcher] Starting Task/Goal Watcher...")

    os.chdir(Path(__file__).parent)

    ensure_dirs_exist()
    processed_files = get_processed_files()

    # Initial index generation on startup
    update_index_file(TASKS_DIR)
    update_index_file(GOALS_DIR)

    while True:
        try:
            all_files_in_dir = set(p.name for p in WATCH_DIR.glob("*.txt"))
            new_files_to_process = all_files_in_dir - processed_files

            if new_files_to_process:
                any_tasks_added = False
                any_goals_added = False
                sorted_new_files = sorted(list(new_files_to_process))

                for filename in sorted_new_files:
                    file_to_process = WATCH_DIR / filename
                    print(f"[Watcher] Processing new file: {filename}")
                    tasks_added, goals_added = process_chat_file(file_to_process)

                    if tasks_added or goals_added:
                        if tasks_added:
                            any_tasks_added = True
                        if goals_added:
                            any_goals_added = True
                        add_to_processed_log(filename)
                        processed_files.add(filename)

                if any_tasks_added:
                    update_index_file(TASKS_DIR)
                if any_goals_added:
                    update_index_file(GOALS_DIR)

            time.sleep(WATCH_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print("[Watcher] Shutting down.")
            break
        except Exception as e:
            print(f"[Watcher] An unexpected error occurred in main loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
