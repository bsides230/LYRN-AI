import os
import json
import psutil
from pathlib import Path
from fastapi import APIRouter, Depends
from core.security import verify_token
import core.state as state
from services.worker import worker_controller
from services.claude import proxy_controller

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
                name = pynvml.nvmlDeviceGetName(handle)
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                try:
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    gpu_util = util.gpu
                except Exception:
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
        "proxy": proxy_controller.get_status(),
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

@router.post("/api/system/start_claude_proxy", dependencies=[Depends(verify_token)])
async def start_claude_proxy():
    return proxy_controller.start_proxy()

@router.post("/api/system/stop_claude_proxy", dependencies=[Depends(verify_token)])
async def stop_claude_proxy():
    return proxy_controller.stop_proxy()

@router.get("/api/system/proxy_status", dependencies=[Depends(verify_token)])
async def get_proxy_status():
    return proxy_controller.get_status()
