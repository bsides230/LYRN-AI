import sys
import subprocess
import os

def main():
    print("--- spawn_chat_watcher.py executed ---")

    # Launch chat_watcher_bg.py in the background
    script_dir = os.path.dirname(os.path.abspath(__file__))
    watcher_script = os.path.join(script_dir, "chat_watcher_bg.py")

    # We must start the background process and exit immediately so the scheduler can trigger the model.
    # We use subprocess.Popen and don't wait for it.

    # We pass the root dir so the watcher knows where to look for files
    root_dir = os.path.abspath(os.path.join(script_dir, '../..'))

    if os.name == 'nt':
        # On Windows we can use creationflags to detach
        subprocess.Popen(
            [sys.executable, watcher_script, root_dir],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000008,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    else:
        subprocess.Popen(
            [sys.executable, watcher_script, root_dir],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    print("Spawned background watcher.")
    sys.exit(0)

if __name__ == "__main__":
    main()
