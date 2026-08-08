import os
import sys
import csv
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
ROUTES_FILE = os.path.join(SCRIPT_DIR, "handoff_routes.tsv")
HANDOFF_DIR = os.path.join(SCRIPT_DIR, "handoff")

class HandoffRouteWatcherHandler(FileSystemEventHandler):
    def __init__(self, routes):
        self.routes = routes

    def on_created(self, event):
        if event.is_directory:
            return
        self.process_file(event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        self.process_file(event.src_path)

    def process_file(self, filepath):
        filename = os.path.basename(filepath)

        # Check if the filename has a registered route
        if filename in self.routes:
            handler_script = self.routes[filename]
            handler_path = os.path.join(PROJECT_ROOT, handler_script)

            if os.path.exists(handler_path):
                print(f"[RouteWatcher] Match found for {filename}. Triggering {handler_script}...")

                # Execute the handler script and pass the file path as an argument
                subprocess.Popen([sys.executable, handler_path, filepath])

                # We could delete the handoff file here, but let the handler do it if needed,
                # or just leave it since the requirements don't explicitly say to delete it.
                # However, to prevent repeated triggers on the same file modification,
                # we might want to rename it or the handler should move it.
                # For now, we trust the handler will process it.
            else:
                print(f"[RouteWatcher] Error: Handler script {handler_script} not found at {handler_path}.")

def load_routes():
    routes = {}
    if not os.path.exists(ROUTES_FILE):
        print(f"Error: {ROUTES_FILE} not found.")
        sys.exit(1)

    with open(ROUTES_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            routes[row['output_file']] = row['handler_script']
    return routes

def main():
    print(f"[RouteWatcher] Starting handoff route watcher...")

    routes = load_routes()
    print(f"[RouteWatcher] Loaded routes: {routes}")

    os.makedirs(HANDOFF_DIR, exist_ok=True)

    event_handler = HandoffRouteWatcherHandler(routes)
    observer = Observer()
    observer.schedule(event_handler, HANDOFF_DIR, recursive=False)
    observer.start()

    print(f"[RouteWatcher] Watching directory: {HANDOFF_DIR}...")

    try:
        # Check for any existing files that might have been missed before startup
        for filename in os.listdir(HANDOFF_DIR):
            filepath = os.path.join(HANDOFF_DIR, filename)
            if os.path.isfile(filepath):
                event_handler.process_file(filepath)

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
