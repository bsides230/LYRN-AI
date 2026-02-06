import os
import time
import tempfile
import hashlib
from pathlib import Path
from fastapi import HTTPException
from backend.config import settings_manager

# --- Shared Psutil / Mock ---
try:
    import psutil
except ImportError:
    class MockPsutil:
        class VirtualMemory:
            percent = 0; used = 0; total = 0
        class DiskUsage:
            percent = 0; used = 0; total = 0
        class Battery:
            percent = 0; power_plugged = False; secsleft = 0
        class CpuFreq:
            current = 0; max = 0
        class Process:
            def __init__(self, pid): pass
            def terminate(self): pass

        NoSuchProcess = Exception
        AccessDenied = Exception

        @staticmethod
        def cpu_percent(interval=None): return 0
        @staticmethod
        def virtual_memory(): return MockPsutil.VirtualMemory()
        @staticmethod
        def disk_usage(path): return MockPsutil.DiskUsage()
        @staticmethod
        def disk_partitions(): return []
        @staticmethod
        def cpu_count(logical=True): return 1
        @staticmethod
        def cpu_freq(): return MockPsutil.CpuFreq()
        @staticmethod
        def sensors_battery(): return None
        @staticmethod
        def net_io_counters():
            class NetIO:
                def _asdict(self): return {}
            return NetIO()
        @staticmethod
        def process_iter(attrs=None): return []
        @staticmethod
        def Process(pid): return MockPsutil.Process(pid)
        @staticmethod
        def pid_exists(pid): return False # Assume dead if no psutil

    psutil = MockPsutil()


def check_path_access(path: str) -> Path:
    """
    Validates if the requested path is allowed under the current filesystem mode.
    Returns the resolved Path object or raises HTTPException.
    """
    try:
        target = Path(path).expanduser().resolve()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")

    mode = settings_manager.settings.get("filesystem_mode", "open")

    if mode == "open":
        return target

    # Jailed Mode
    if mode == "jailed":
        root_str = settings_manager.settings.get("filesystem_root")
        extra_roots = settings_manager.settings.get("filesystem_extra_roots", [])

        allowed_roots = []
        if root_str:
            try:
                allowed_roots.append(Path(root_str).expanduser().resolve())
            except: pass

        for er in extra_roots:
            try:
                allowed_roots.append(Path(er).expanduser().resolve())
            except: pass

        if not allowed_roots:
            raise HTTPException(status_code=500, detail="Filesystem is jailed but no roots are configured.")

        is_allowed = False
        for root in allowed_roots:
            try:
                if os.path.commonpath([str(root), str(target)]) == str(root):
                    is_allowed = True
                    break
            except ValueError:
                continue

        if not is_allowed:
            raise HTTPException(status_code=403, detail="Access denied: Path is outside filesystem jail")

        return target

    return target

class SimpleFileLock:
    """
    A simple, portable file locking mechanism that is resistant to stale locks.
    """
    def __init__(self, lock_file_path, timeout=5):
        lock_file_hash = hashlib.md5(str(lock_file_path).encode()).hexdigest()
        self.lock_file_path = os.path.join(tempfile.gettempdir(), f"{lock_file_hash}.lock")
        self.timeout = timeout
        self._lock_file_handle = None

    def _is_pid_running(self, pid):
        return psutil.pid_exists(pid)

    def __enter__(self):
        start_time = time.time()
        while True:
            try:
                self._lock_file_handle = open(self.lock_file_path, 'x')
                self._lock_file_handle.write(str(os.getpid()))
                self._lock_file_handle.flush()
                return self
            except FileExistsError:
                if time.time() - start_time > self.timeout:
                    raise TimeoutError(f"Could not acquire lock on {self.lock_file_path} within {self.timeout}s.")

                try:
                    with open(self.lock_file_path, 'r') as f:
                        pid_str = f.read().strip()
                        if not pid_str:
                             os.remove(self.lock_file_path)
                             continue
                        owner_pid = int(pid_str)

                    if not self._is_pid_running(owner_pid):
                        os.remove(self.lock_file_path)
                        continue
                except (IOError, ValueError):
                    pass
                time.sleep(0.1)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._lock_file_handle:
            self._lock_file_handle.close()
            try:
                with open(self.lock_file_path, 'r') as f:
                    owner_pid = int(f.read().strip())
                if owner_pid == os.getpid():
                    os.remove(self.lock_file_path)
            except (IOError, ValueError, FileNotFoundError):
                pass
