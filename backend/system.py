import os
import sys
import platform
import subprocess
import socket
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException

try:
    import psutil
except ImportError:
    psutil = None

try:
    import pynvml
except ImportError:
    pynvml = None

from backend.auth import verify_token

# --- Mock Psutil for Android/No-Dep ---
if psutil is None:
    class MockPsutil:
        class VirtualMemory:
            percent = 0
            used = 0
            total = 0
        class DiskUsage:
            percent = 0
            used = 0
            total = 0
        class Battery:
            percent = 0
            power_plugged = False
            secsleft = 0
        class CpuFreq:
            current = 0
            max = 0
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

    psutil = MockPsutil()

router = APIRouter()

# Extended LLM Stats (populated by worker/chat module if present)
extended_llm_stats = {}

def update_llm_stats(stats):
    extended_llm_stats.update(stats)

@router.get("/health")
async def health_check():
    # CPU
    try:
        cpu_percent = psutil.cpu_percent()
    except (PermissionError, Exception):
        cpu_percent = 0

    cpu_info = {
        "percent": cpu_percent,
        "count": psutil.cpu_count(logical=True) or 1
    }

    # RAM
    try:
        ram = psutil.virtual_memory()
    except (PermissionError, Exception):
        class MockRAM:
            percent = 0
            used = 0
            total = 0
        ram = MockRAM()

    # Disk
    try:
        disk = psutil.disk_usage('.')
    except (PermissionError, Exception):
        class MockDisk:
            percent = 0
            used = 0
            total = 0
        disk = MockDisk()

    # GPU
    gpu_stats = {}
    if pynvml:
        try:
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                name = pynvml.nvmlDeviceGetName(handle)
                try:
                    # pynvml returns bytes in older versions? nvidia-ml-py usually returns strings/ints correctly
                    if isinstance(name, bytes): name = name.decode()
                except: pass

                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                try:
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    gpu_util = util.gpu
                except:
                    gpu_util = 0

                gpu_stats[f"gpu_{i}"] = {
                    "name": name,
                    "vram_used_gb": mem_info.used / (1024**3),
                    "vram_total_gb": mem_info.total / (1024**3),
                    "vram_percent": (mem_info.used / mem_info.total) * 100,
                    "gpu_util_percent": gpu_util
                }
        except Exception as e:
            gpu_stats["error"] = str(e)

    # Battery
    battery_info = {}
    try:
        sb = psutil.sensors_battery()
        if sb:
            battery_info = {
                "percent": sb.percent,
                "power_plugged": sb.power_plugged
            }
    except: pass

    # OS Info
    os_info = {
        "system": platform.system(),
        "release": platform.release()
    }

    # Worker Status (Check for global flags file or similar if worker logic is separate)
    # The Chat module usually updates this, but System module provides the endpoint.
    # We might need to inject worker_controller status if available.
    # For now, we return a placeholder or check a file.
    worker_status = {"running": False, "llm_status": "unknown"}
    # If using backend/chat.py, it should write status to a file or share state?
    # Let's check "global_flags/llm_status.txt" directly here for stateless check
    if Path("global_flags/llm_status.txt").exists():
        worker_status["llm_status"] = Path("global_flags/llm_status.txt").read_text().strip()
        worker_status["running"] = True # Assumption if status file exists/updates

    return {
        "status": "ok",
        "cpu": cpu_info,
        "ram": {
            "percent": ram.percent,
            "used_gb": ram.used / (1024**3),
            "total_gb": ram.total / (1024**3)
        },
        "disk": {
            "percent": disk.percent,
            "used_gb": disk.used / (1024**3),
            "total_gb": disk.total / (1024**3)
        },
        "gpu": gpu_stats,
        "battery": battery_info,
        "os": os_info,
        "worker": worker_status,
        "llm_stats": extended_llm_stats
    }

@router.get("/api/sysinfo", dependencies=[Depends(verify_token)])
async def get_sysinfo():
    hostname = socket.gethostname()
    try:
        ip_address = socket.gethostbyname(hostname)
    except:
        ip_address = "Unknown"

    cpu_model = platform.processor()

    # Partitions
    partitions = []
    try:
        for part in psutil.disk_partitions():
            try:
                if "cdrom" in part.opts or part.fstype == "": continue
                usage = psutil.disk_usage(part.mountpoint)
                partitions.append({
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "total_gb": usage.total / (1024**3),
                    "percent": usage.percent
                })
            except: continue
    except: pass

    # Standard Paths (Android support)
    standard_paths = [{"name": "Home", "path": str(Path.home().resolve())}]
    if "ANDROID_ROOT" in os.environ or "com.termux" in os.environ.get("PREFIX", ""):
        if os.path.exists("/sdcard"):
             standard_paths.append({"name": "Internal Storage", "path": "/sdcard"})

    return {
        "hostname": hostname,
        "ip_address": ip_address,
        "os": f"{platform.system()} {platform.release()}",
        "cpu_model": cpu_model,
        "partitions": partitions,
        "standard_paths": standard_paths
    }

@router.post("/api/power/restart", dependencies=[Depends(verify_token)])
async def restart_server():
    try:
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/power/reboot", dependencies=[Depends(verify_token)])
async def reboot_system():
    try:
        if platform.system() == "Windows":
            subprocess.run(["shutdown", "/r", "/t", "0"])
        else:
            subprocess.run(["sudo", "reboot"])
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/power/shutdown", dependencies=[Depends(verify_token)])
async def shutdown_system():
    try:
        if platform.system() == "Windows":
            subprocess.run(["shutdown", "/s", "/t", "0"])
        else:
            subprocess.run(["sudo", "shutdown", "now"])
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
