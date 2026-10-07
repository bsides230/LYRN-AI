import os
import json
import shutil
import subprocess
import psutil
from pathlib import Path
from fastapi import APIRouter, Depends
from core.security import verify_token
import core.state as state
from services.worker import worker_controller

try:
    import pynvml
except ImportError:
    pynvml = None

router = APIRouter(tags=["system"])

@router.get("/api/auth/status")
async def get_auth_status():
    if Path("global_flags/no_auth").exists():
        return {"required": False}
    return {"required": True}

@router.post("/api/verify_token", dependencies=[Depends(verify_token)])
async def verify_token_endpoint():
    return {"status": "valid"}

@router.get("/health")
async def health_check():
    try:
        cpu = psutil.cpu_percent()
    except (PermissionError, AttributeError, Exception):
        cpu = None

    ram = psutil.virtual_memory()

    try:
        disk = psutil.disk_usage('.')
    except (PermissionError, Exception):
        disk = None

    gpu_stats = {}
    if pynvml:
        try:
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                raw_name = pynvml.nvmlDeviceGetName(handle)
                name = raw_name.decode('utf-8') if isinstance(raw_name, bytes) else str(raw_name)
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                try:
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    gpu_util = util.gpu
                except Exception:
                    gpu_util = 0

                gpu_stats[f"gpu_{i}"] = {
                    "name": name,
                    "vram_used_gb": round(mem_info.used / (1024**3), 2),
                    "vram_total_gb": round(mem_info.total / (1024**3), 2),
                    "vram_percent": round((mem_info.used / mem_info.total) * 100, 1),
                    "gpu_util_percent": gpu_util
                }
        except Exception as e:
            gpu_stats["error"] = str(e)

    # Fallback to nvidia-smi if pynvml returned no devices or errored
    if (not any(k.startswith("gpu_") for k in gpu_stats)) and shutil.which("nvidia-smi"):
        try:
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=2
            )
            if res.returncode == 0 and res.stdout.strip():
                lines = [line.strip() for line in res.stdout.strip().splitlines() if line.strip()]
                for i, line in enumerate(lines):
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 4:
                        dev_name = parts[0]
                        g_util = float(parts[1])
                        used_gb = float(parts[2]) / 1024.0
                        tot_gb = float(parts[3]) / 1024.0
                        pct = (used_gb / tot_gb) * 100 if tot_gb > 0 else 0
                        gpu_stats[f"gpu_{i}"] = {
                            "name": dev_name,
                            "vram_used_gb": round(used_gb, 2),
                            "vram_total_gb": round(tot_gb, 2),
                            "vram_percent": round(pct, 1),
                            "gpu_util_percent": round(g_util, 1)
                        }
                if "error" in gpu_stats and any(k.startswith("gpu_") for k in gpu_stats):
                    gpu_stats.pop("error", None)
        except Exception:
            pass

    if "gpu_0" in gpu_stats:
        gpu_stats["primary"] = gpu_stats["gpu_0"]
        gpu_stats["available"] = True
    else:
        gpu_stats["available"] = False

    worker_status = worker_controller.get_status()

    llm_stats = {}
    try:
        stats_path = Path("global_flags/llm_stats.json")
        if stats_path.exists():
            with open(stats_path, 'r', encoding='utf-8') as f:
                llm_stats = json.load(f)
    except Exception:
        pass

    # Merge with extended stats from memory
    llm_stats.update(state.extended_llm_stats)

    from core.registry import settings_manager
    if not settings_manager.settings:
        settings_manager.load_or_detect_first_boot()
    active_config = settings_manager.settings.get("active", {})
    model_path = active_config.get("model_path", "")
    if model_path:
        llm_stats["model_name"] = os.path.basename(model_path)
    else:
        llm_stats["model_name"] = "None"

    return {
        "status": "ok",
        "cpu": cpu,
        "ram": {
            "percent": ram.percent,
            "used_gb": ram.used / (1024**3),
            "total_gb": ram.total / (1024**3)
        },
        "disk": {
            "percent": disk.percent,
            "used_gb": disk.used / (1024**3),
            "total_gb": disk.total / (1024**3)
        } if disk else None,
        "gpu": gpu_stats,
        "worker": worker_status,
        "llm_stats": llm_stats
    }

@router.get("/api/system/worker_status", dependencies=[Depends(verify_token)])
async def get_worker_status():
    return worker_controller.get_status()

@router.post("/api/system/start_worker", dependencies=[Depends(verify_token)])
async def start_worker():
    return worker_controller.start_worker()

@router.post("/api/system/stop_worker", dependencies=[Depends(verify_token)])
async def stop_worker():
    return worker_controller.stop_worker()

@router.post("/api/system/clear_stats", dependencies=[Depends(verify_token)])
async def clear_stats():
    # Reset memory stats
    for key in state.extended_llm_stats:
        if isinstance(state.extended_llm_stats[key], (int, float)):
            state.extended_llm_stats[key] = 0

    # Clear json file
    stats_path = Path("global_flags/llm_stats.json")
    if stats_path.exists():
        try:
            stats_path.unlink()
        except Exception:
            pass

    return {"success": True}
