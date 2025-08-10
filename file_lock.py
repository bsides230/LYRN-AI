import os
import time

class SimpleFileLock:
    """
    A simple, portable file locking mechanism using a .lock file.
    This is a context manager to ensure the lock is always released.

    Usage:
    with SimpleFileLock("my_resource.lock"):
        # do work on the resource
    """
    def __init__(self, lock_file_path, timeout=5):
        self.lock_file_path = lock_file_path
        self.timeout = timeout
        self._lock_file_handle = None

    def __enter__(self):
        start_time = time.time()
        while True:
            try:
                # 'x' mode creates a file and opens it for writing,
                # failing with FileExistsError if the file already exists.
                self._lock_file_handle = open(self.lock_file_path, 'x')
                # If we successfully created the file, we have acquired the lock.
                return self
            except FileExistsError:
                if time.time() - start_time > self.timeout:
                    # After the timeout, we could either raise an error
                    # or potentially delete a stale lock file. Raising an error is safer.
                    raise TimeoutError(f"Could not acquire lock on {self.lock_file_path} within {self.timeout}s.")
                time.sleep(0.1)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._lock_file_handle:
            self._lock_file_handle.close()
            try:
                # Remove the lock file to release the lock.
                os.remove(self.lock_file_path)
            except OSError:
                # This could happen if another process broke the lock, which is acceptable.
                pass
