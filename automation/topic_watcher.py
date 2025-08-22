import os
import re
import sys
import time
from pathlib import Path

# --- Add project root to sys.path ---
# This allows the script to import modules from the project root, like topic_manager.
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from topic_manager import TopicManager

# --- Configuration ---
WATCH_DIR = project_root / "chat"
NEW_TOPICS_FILE = project_root / "new_topics.txt"
SEARCHED_TOPICS_FILE = project_root / "searched_topics.txt"
PROCESSED_FILES_LOG = Path(__file__).parent / "topic_watcher_processed.log"
WATCH_INTERVAL_SECONDS = 3

def ensure_files_exist():
    """Ensure the necessary output and log files exist."""
    WATCH_DIR.mkdir(parents=True, exist_ok=True)
    NEW_TOPICS_FILE.touch(exist_ok=True)
    SEARCHED_TOPICS_FILE.touch(exist_ok=True)
    PROCESSED_FILES_LOG.touch(exist_ok=True)

def get_processed_files() -> set:
    """Reads the list of already processed chat files."""
    try:
        with open(PROCESSED_FILES_LOG, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    except IOError as e:
        print(f"[TopicWatcher] Error reading processed files log: {e}")
        return set()

def add_to_processed_log(filename: str):
    """Adds a filename to the log of processed files."""
    try:
        with open(PROCESSED_FILES_LOG, 'a', encoding='utf-8') as f:
            f.write(filename + "\n")
    except IOError as e:
        print(f"[TopicWatcher] Error writing to processed files log: {e}")

def process_chat_file(filepath: Path, tm: TopicManager, existing_search_data: dict):
    """
    Reads a chat file, parses for the TIS block, and processes the keywords.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        tis_pattern = re.compile(r"##TIS_START##(.*?)##TIS_END##", re.DOTALL)
        matches = tis_pattern.findall(content)

        if not matches:
            return # No topic block found in this file

        keywords_processed = 0
        new_topics_found = []

        for block in matches:
            keywords = [kw.strip() for kw in block.strip().split('\n') if kw.strip()]

            with open(SEARCHED_TOPICS_FILE, 'a', encoding='utf-8') as f_searched:
                for kw in keywords:
                    f_searched.write(kw + "\n")
                    keywords_processed += 1

                    # Check if topic exists
                    found = False
                    for topic_data in existing_search_data.values():
                        if kw.lower() == topic_data['display_name'].lower() or kw.lower() in [n.lower() for n in topic_data['alt_names']]:
                            found = True
                            break

                    if not found:
                        new_topics_found.append(kw)

        if new_topics_found:
            # Append unique new topics to the file
            unique_new_topics = sorted(list(set(new_topics_found)))
            with open(NEW_TOPICS_FILE, 'a', encoding='utf-8') as f_new:
                for topic in unique_new_topics:
                    f_new.write(topic + "\n")
            print(f"[TopicWatcher] Found {len(unique_new_topics)} new topics: {unique_new_topics}")

        if keywords_processed > 0:
            print(f"[TopicWatcher] Processed {keywords_processed} topic keywords from {filepath.name}.")

    except Exception as e:
        print(f"[TopicWatcher] Failed to process {filepath.name}: {e}")

def main():
    """Main watch loop."""
    print("[TopicWatcher] Starting...")

    # It's better to work with absolute paths, so no os.chdir is needed.
    ensure_files_exist()
    processed_files = get_processed_files()
    tm = TopicManager(base_dir=project_root)

    print(f"[TopicWatcher] Watching directory: {WATCH_DIR}")

    while True:
        try:
            # Refresh topic search data periodically
            existing_search_data = tm.get_topic_search_data()

            all_files_in_dir = set(p.name for p in WATCH_DIR.glob("*.txt"))
            new_files_to_process = all_files_in_dir - processed_files

            if new_files_to_process:
                sorted_new_files = sorted(list(new_files_to_process), key=lambda name: os.path.getmtime(WATCH_DIR / name))

                for filename in sorted_new_files:
                    file_to_process = WATCH_DIR / filename
                    print(f"[TopicWatcher] Processing new file: {filename}")
                    process_chat_file(file_to_process, tm, existing_search_data)
                    add_to_processed_log(filename)
                    processed_files.add(filename)

            time.sleep(WATCH_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print("[TopicWatcher] Shutting down.")
            break
        except Exception as e:
            print(f"[TopicWatcher] An unexpected error occurred in main loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
