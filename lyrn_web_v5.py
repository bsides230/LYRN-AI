import os
import psutil
import asyncio
import json
import datetime
import threading
import gc
import collections
import time
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn

try:
    import pynvml
except ImportError:
    pynvml = None

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

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
            # Optionally send recent history upon connection
            # for event in self.history:
            #    await q.put(event)
            pass

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

# --- Model Controller ---
class ModelController:
    def __init__(self):
        self.llm: Optional[Any] = None
        self.status = "unloaded" # unloaded, loading, loaded, unloading, error
        self.model_path = ""
        self.model_params = {}
        self._lock = threading.Lock()

    def get_status(self):
        with self._lock:
            return {
                "state": self.status,
                "model_name": os.path.basename(self.model_path) if self.model_path else None,
                "n_ctx": self.model_params.get("n_ctx"),
                "n_gpu_layers": self.model_params.get("n_gpu_layers")
            }

    def load_model_thread(self, path: str, config: Dict[str, Any]):
        def log(level, msg):
            if main_loop:
                 asyncio.run_coroutine_threadsafe(logger.emit(level, msg, "ModelController"), main_loop)
            else:
                 print(f"[{level}] ModelController: {msg}")

        try:
            if not Llama:
                log("Error", "llama-cpp-python not installed.")
                with self._lock:
                    self.status = "error"
                return

            log("Info", f"Starting load of model: {path}")

            with self._lock:
                if self.status in ["loading", "unloading"]:
                     log("Warn", "Model operation already in progress.")
                     return
                self.status = "loading"
                self.model_path = path
                self.model_params = config

            # Check file existence
            if not os.path.exists(path):
                 raise FileNotFoundError(f"Model file not found: {path}")

            # Actual Loading (Blocking)
            # Using default params if not specified in config
            n_ctx = config.get("n_ctx", 2048)
            n_gpu_layers = config.get("n_gpu_layers", 0)

            self.llm = Llama(
                model_path=path,
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                verbose=False
            )

            with self._lock:
                self.status = "loaded"

            log("Info", "Model loaded successfully.")

        except Exception as e:
            with self._lock:
                self.status = "error"
                self.llm = None
            log("Error", f"Failed to load model: {str(e)}")

    def unload_model_thread(self):
        def log(level, msg):
            if main_loop:
                 asyncio.run_coroutine_threadsafe(logger.emit(level, msg, "ModelController"), main_loop)
            else:
                 print(f"[{level}] ModelController: {msg}")

        try:
            with self._lock:
                if self.status == "unloaded":
                    return
                self.status = "unloading"

            log("Info", "Unloading model...")

            if self.llm:
                del self.llm
                self.llm = None
                gc.collect()

            with self._lock:
                self.status = "unloaded"
                self.model_path = ""
                self.model_params = {}

            log("Info", "Model unloaded.")

        except Exception as e:
             with self._lock:
                self.status = "error"
             log("Error", f"Error unloading model: {str(e)}")

model_controller = ModelController()

# --- Pydantic Models ---
class LoadModelRequest(BaseModel):
    model_path: str
    config: Optional[Dict[str, Any]] = {}

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
        "gpu": gpu_stats
    }

# Logging Endpoint
@app.get("/api/logs")
async def stream_logs(request: Request):
    return StreamingResponse(logger.subscribe(request), media_type="text/event-stream")

# Model Endpoints
@app.get("/api/model/status")
async def get_model_status():
    return model_controller.get_status()

@app.post("/api/model/load")
async def load_model(req: LoadModelRequest, background_tasks: BackgroundTasks):
    if model_controller.status in ["loading", "loaded"]:
         return JSONResponse({"accepted": False, "message": "Model already loaded or loading."}, status_code=400)

    # Run in a separate thread to avoid blocking the event loop
    threading.Thread(target=model_controller.load_model_thread, args=(req.model_path, req.config)).start()
    return {"accepted": True, "message": "Model load started."}

@app.post("/api/model/unload")
async def unload_model():
    if model_controller.status == "unloaded":
         return JSONResponse({"accepted": False, "message": "No model to unload."}, status_code=400)

    threading.Thread(target=model_controller.unload_model_thread).start()
    return {"accepted": True, "message": "Model unload started."}


# Serve dashboard at root
@app.get("/")
async def read_root():
    return FileResponse('LYRN_v5/dashboard.html')

# Serve Static Files
app.mount("/", StaticFiles(directory="LYRN_v5", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
