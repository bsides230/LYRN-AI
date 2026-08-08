import os
import json
import csv
from datetime import datetime

INDEXES_DIR = "runtime/indexes"
STORAGE_DIR = os.path.join(INDEXES_DIR, "storage")
SETTINGS_FILE = os.path.join(INDEXES_DIR, "settings.json")
CATEGORIES_FILE = os.path.join(INDEXES_DIR, "categories.csv")

def _get_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {"default_recall_limit": 5}
    with open(SETTINGS_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"default_recall_limit": 5}

def store_index_string(category, pipe_string):
    """
    Parses a pipe-delimited string:
    Part 1 (Static Info) -> core.json
    Part 2 (Structured Logs) -> prepended to logs.csv
    Part 3 (Verbose Markdown) -> prepended to entries.md
    """
    os.makedirs(STORAGE_DIR, exist_ok=True)
    cat_dir = os.path.join(STORAGE_DIR, category)
    os.makedirs(cat_dir, exist_ok=True)

    parts = pipe_string.split('|')
    static_info = parts[0] if len(parts) > 0 else "{}"
    structured_log = parts[1] if len(parts) > 1 else ""
    verbose_markdown = parts[2] if len(parts) > 2 else ""

    # 1. Store Static Info (core.json) - overwrites
    core_file = os.path.join(cat_dir, "core.json")
    try:
        core_data = json.loads(static_info)
    except json.JSONDecodeError:
        core_data = {"raw_static": static_info}
    with open(core_file, "w") as f:
        json.dump(core_data, f, indent=4)

    # 2. Store Structured Logs (logs.csv) - prepends (reverse chron)
    logs_file = os.path.join(cat_dir, "logs.csv")
    existing_logs = []
    if os.path.exists(logs_file):
        with open(logs_file, "r", newline='') as f:
            reader = csv.reader(f)
            existing_logs = list(reader)

    timestamp = datetime.now().isoformat()
    new_log_row = [timestamp, structured_log]

    with open(logs_file, "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(new_log_row)
        writer.writerows(existing_logs)

    # 3. Store Verbose Markdown (entries.md) - prepends (reverse chron)
    md_file = os.path.join(cat_dir, "entries.md")
    existing_md = ""
    if os.path.exists(md_file):
        with open(md_file, "r") as f:
            existing_md = f.read()

    new_md_entry = f"## Entry {timestamp}\n{verbose_markdown}\n\n"
    with open(md_file, "w") as f:
        f.write(new_md_entry + existing_md)

    return True

def recall_index_string(category):
    """
    Recalls an index string from the file system.
    Returns: StaticInfo|RecentLogs|RecentMarkdown
    """
    cat_dir = os.path.join(STORAGE_DIR, category)
    if not os.path.exists(cat_dir):
        return ""

    settings = _get_settings()
    limit = settings.get("default_recall_limit", 5)

    # 1. Recall Static Info
    core_file = os.path.join(cat_dir, "core.json")
    static_info = "{}"
    if os.path.exists(core_file):
        with open(core_file, "r") as f:
            try:
                data = json.load(f)
                static_info = json.dumps(data)
            except json.JSONDecodeError:
                f.seek(0)
                static_info = f.read()

    # 2. Recall Structured Logs (Top N)
    logs_file = os.path.join(cat_dir, "logs.csv")
    recent_logs = []
    if os.path.exists(logs_file):
        with open(logs_file, "r", newline='') as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i >= limit:
                    break
                if len(row) > 1:
                    recent_logs.append(row[1])
                elif len(row) == 1:
                    recent_logs.append(row[0])
    logs_str = ",".join(recent_logs)

    # 3. Recall Verbose Markdown (Top N sections)
    md_file = os.path.join(cat_dir, "entries.md")
    recent_md_entries = []
    if os.path.exists(md_file):
        with open(md_file, "r") as f:
            content = f.read()
            sections = content.split("## Entry ")
            sections = [s for s in sections if s.strip()]
            for i, section in enumerate(sections):
                if i >= limit:
                    break
                lines = section.split('\n', 1)
                if len(lines) > 1:
                    recent_md_entries.append(lines[1].strip())

    md_str = "\n".join(recent_md_entries)

    return f"{static_info}|{logs_str}|{md_str}"
