import os
import sys
import psutil
import asyncio
import json
import datetime
import threading
import subprocess
import collections
import time
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn

from settings_manager import SettingsManager

try:
    import pynvml
except ImportError:
    pynvml = None

# Global reference to the main event loop
main_loop: Optional[asyncio.AbstractEventLoop] = None

# --- JournalLogger ---
class JournalLogger:
    def __init__(self, max_history=1000):
        self.history = collections.deque(maxlen=max_history)
        self.subscribers = set()
        # Lock must be created in the loop, so we initialize it lazily or assume usage in loop
        self._lock = None

    @property
    def lock(self):
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def emit(self, level: str, msg: str, source: str = "System"):
        event = {
            "ts": datetime.datetime.now().isoformat(),
            "level": level,
            "msg": msg,
            "source": source
        }
        self.history.append(event)

        # Log to console as fallback/standard output
        print(f"[{level}] {source}: {msg}")

        # Notify subscribers
        async with self.lock:
            for q in self.subscribers:
                await q.put(event)

    async def subscribe(self, request: Request):
        q = asyncio.Queue()
        async with self.lock:
            self.subscribers.add(q)

        try:
            while True:
                if await request.is_disconnected():
                    break

                try:
                    # Wait for new event or timeout for heartbeat
                    event = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Heartbeat
                    yield f": heartbeat\n\n"
        finally:
            async with self.lock:
                if q in self.subscribers:
                    self.subscribers.remove(q)

# Global Logger
logger = JournalLogger()
settings_manager = SettingsManager()

# --- Worker Controller ---
class WorkerController:
    """Manages the headless worker process."""
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self.worker_script = "headless_lyrn_worker.py"

    def get_status(self):
        with self._lock:
            running = self.process is not None and self.process.poll() is None

            # Check LLM status flag if running
            llm_status = "unknown"
            if running:
                try:
                    flag_path = Path("global_flags/llm_status.txt")
                    if flag_path.exists():
                        llm_status = flag_path.read_text().strip()
                except Exception:
                    pass
            else:
                llm_status = "stopped"

            return {
                "running": running,
                "pid": self.process.pid if running else None,
                "llm_status": llm_status
            }

    def start_worker(self):
        with self._lock:
            if self.process is not None and self.process.poll() is None:
                return {"success": False, "message": "Worker already running."}

            try:
                # Start the worker process
                self.process = subprocess.Popen(
                    [sys.executable, self.worker_script],
                    cwd=os.getcwd(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                # Start threads to forward output to logger
                threading.Thread(target=self._monitor_output, args=(self.process.stdout, "WorkerOut"), daemon=True).start()
                threading.Thread(target=self._monitor_output, args=(self.process.stderr, "WorkerErr"), daemon=True).start()

                return {"success": True, "message": "Worker started."}
            except Exception as e:
                return {"success": False, "message": f"Failed to start worker: {e}"}

    def stop_worker(self):
        with self._lock:
            if self.process is None or self.process.poll() is not None:
                return {"success": False, "message": "Worker not running."}

            try:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()

                self.process = None
                return {"success": True, "message": "Worker stopped."}
            except Exception as e:
                return {"success": False, "message": f"Error stopping worker: {e}"}

    def _monitor_output(self, stream, source):
        """Reads output from the subprocess and logs it."""
        try:
            for line in iter(stream.readline, ''):
                if line:
                    clean_line = line.strip()
                    if main_loop and clean_line:
                        asyncio.run_coroutine_threadsafe(logger.emit("Info", clean_line, source), main_loop)
                    elif clean_line:
                        print(f"[{source}] {clean_line}")
        except Exception:
            pass
        finally:
            stream.close()

worker_controller = WorkerController()

# --- Pydantic Models ---
class PresetModel(BaseModel):
    preset_id: str
    config: Dict[str, Any]

class ActiveConfigModel(BaseModel):
    config: Dict[str, Any]

# --- App Setup ---
app = FastAPI(title="LYRN v5 Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    global main_loop
    main_loop = asyncio.get_running_loop()
    await logger.emit("Info", "Backend started.", "System")

# --- Routes ---

@app.get("/health")
async def health_check():
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('.')

    gpu_stats = {}
    if pynvml:
        try:
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            gpu_stats = {
                "vram_used_gb": mem_info.used / (1024**3),
                "vram_total_gb": mem_info.total / (1024**3),
                "vram_percent": (mem_info.used / mem_info.total) * 100
            }
        except Exception:
            pass

    worker_status = worker_controller.get_status()

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
        },
        "gpu": gpu_stats,
        "worker": worker_status
    }

# Logging Endpoint
@app.get("/api/logs")
async def stream_logs(request: Request):
    return StreamingResponse(logger.subscribe(request), media_type="text/event-stream")

# --- Model & Config Endpoints ---

@app.get("/api/models/list")
async def list_models():
    """Lists available models in the models/ directory."""
    models_dir = Path("models")
    if not models_dir.exists():
        return {"models": []}

    models = [f.name for f in models_dir.glob("*") if f.suffix in ['.gguf', '.bin']]
    return {"models": sorted(models)}

@app.get("/api/config/presets")
async def get_presets():
    """Gets all model presets."""
    if not settings_manager.settings:
        settings_manager.load_or_detect_first_boot()

    return settings_manager.settings.get("model_presets", {})

@app.post("/api/config/presets")
async def save_preset(preset: PresetModel):
    """Saves a model preset."""
    if not settings_manager.settings:
        settings_manager.load_or_detect_first_boot()

    if "model_presets" not in settings_manager.settings:
        settings_manager.settings["model_presets"] = {}

    settings_manager.settings["model_presets"][preset.preset_id] = preset.config
    settings_manager.save_settings()
    return {"success": True, "message": f"Preset {preset.preset_id} saved."}

@app.post("/api/config/active")
async def set_active_config(config: ActiveConfigModel):
    """Sets the active model configuration."""
    if not settings_manager.settings:
        settings_manager.load_or_detect_first_boot()

    settings_manager.settings["active"] = config.config
    settings_manager.save_settings()
    return {"success": True, "message": "Active configuration updated."}

@app.get("/api/config/active")
async def get_active_config():
    """Gets the active model configuration."""
    if not settings_manager.settings:
        settings_manager.load_or_detect_first_boot()

    return settings_manager.settings.get("active", {})

# --- Worker Control Endpoints ---

@app.get("/api/system/worker_status")
async def get_worker_status():
    return worker_controller.get_status()

@app.post("/api/system/start_worker")
async def start_worker():
    return worker_controller.start_worker()

@app.post("/api/system/stop_worker")
async def stop_worker():
    return worker_controller.stop_worker()


# Serve dashboard at root
@app.get("/")
async def read_root():
    return FileResponse('LYRN_v5/dashboard.html')

# Serve Static Files
app.mount("/", StaticFiles(directory="LYRN_v5", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
