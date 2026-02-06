import os
import sys
import asyncio
import argparse
from pathlib import Path
from typing import Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn

# Ensure backend can be imported if running from subdir
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.config import settings_manager
from backend.logger import logger
from backend.auth import verify_token, load_token

# Scheduler
from backend.automation_controller import automation_controller, Job

# Routers
from backend.system import router as system_router
from backend.logs import router as logs_router
from backend.files import router as files_router
from backend.git_mgr import router as git_router
from backend.vlc import router as vlc_router
from backend.shortcuts import router as shortcuts_router
from backend.automation import router as automation_router
from backend.chat import router as chat_router
from backend.models import router as models_router
from backend.snapshots import router as snapshots_router

# Global Loop
main_loop = None

async def scheduler_loop():
    print("[Scheduler] Starting scheduler loop...")
    while True:
        try:
            job = automation_controller.get_next_due_job()
            if job:
                print(f"[Scheduler] Executing job: {job.name}")
                result = await asyncio.get_running_loop().run_in_executor(None, automation_controller.execute_job_scripts, job)

                # If job has prompt and chat module is active (checked by existence of trigger_chat_generation logic,
                # but better to decouple).
                # The original scheduler called trigger_chat_generation.
                # We can import trigger_chat_generation from backend.chat if we are in LYRN context.
                # Or check if "chat" is in modules.
                if "chat" in settings_manager.settings.get("modules", []):
                    from backend.chat import trigger_chat_generation
                    if result["status"] == "success" and job.prompt:
                        try:
                            trigger_chat_generation(job.prompt, folder="jobs")
                            automation_controller.log_job_history(job.name, [{"message": "Prompt triggered."}], "success")
                        except Exception as e:
                            print(f"[Scheduler] Failed to trigger chat: {e}")

            await asyncio.sleep(5)
        except Exception as e:
            print(f"[Scheduler] Error: {e}")
            await asyncio.sleep(5)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global main_loop
    main_loop = asyncio.get_running_loop()

    # Load Token
    load_token()

    # Start Scheduler if automation module is active
    if "automation" in settings_manager.settings.get("modules", []):
        asyncio.create_task(scheduler_loop())

    await logger.emit("Info", "Server started.", "System")
    yield

app = FastAPI(title="Universal Server", lifespan=lifespan)

# CORS
allowed_origins = settings_manager.settings.get("allowed_origins", [])
current_port = 8000
if os.path.exists("port.txt"):
    try:
        with open("port.txt", "r") as f:
            val = f.read().strip()
            if val.isdigit(): current_port = int(val)
    except: pass

defaults = [f"http://localhost:{current_port}", f"http://127.0.0.1:{current_port}"]
for d in defaults:
    if d not in allowed_origins: allowed_origins.append(d)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["X-Token", "Content-Type", "Authorization"],
)

# Core Config Routes
@app.get("/api/config", dependencies=[Depends(verify_token)])
async def get_config():
    return {
        "settings": settings_manager.settings,
        "ui_settings": settings_manager.ui_settings,
        "port": current_port
    }

@app.post("/api/config", dependencies=[Depends(verify_token)])
async def save_config(data: Dict[str, Any]):
    if "settings" in data: settings_manager.settings = data["settings"]
    if "ui_settings" in data: settings_manager.ui_settings = data["ui_settings"]
    settings_manager.save_settings()
    return {"success": True}

# Config Presets (Common)
@app.get("/api/config/presets", dependencies=[Depends(verify_token)])
async def get_presets():
    return settings_manager.settings.get("model_presets", {})

@app.post("/api/config/presets", dependencies=[Depends(verify_token)])
async def save_preset(data: Dict[str, Any], token: str = Depends(verify_token)):
    if "model_presets" not in settings_manager.settings:
        settings_manager.settings["model_presets"] = {}
    preset_id = data.get("preset_id")
    config = data.get("config")
    if preset_id and config:
        settings_manager.settings["model_presets"][preset_id] = config
        settings_manager.save_settings()
        return {"success": True}
    return {"success": False}

@app.post("/api/config/active", dependencies=[Depends(verify_token)])
async def set_active_config(data: Dict[str, Any], token: str = Depends(verify_token)):
    config = data.get("config")
    if config:
        settings_manager.settings["active"] = config
        settings_manager.save_settings()
        return {"success": True}
    return {"success": False}

# Dynamic Router Mounting
modules = settings_manager.settings.get("modules", [])
print(f"[System] Active Modules: {modules}")

if "system" in modules: app.include_router(system_router) # /health, /sysinfo
if "logs" in modules: app.include_router(logs_router, prefix="/api/logs")
if "files" in modules: app.include_router(files_router, prefix="/api/files")
if "git" in modules: app.include_router(git_router, prefix="/api/git")
if "vlc" in modules: app.include_router(vlc_router, prefix="/api/vlc")
if "shortcuts" in modules: app.include_router(shortcuts_router, prefix="/api/shortcuts")
if "automation" in modules: app.include_router(automation_router, prefix="/api/automation")
if "chat" in modules: app.include_router(chat_router, prefix="/api/chat")
if "models" in modules: app.include_router(models_router, prefix="/api/models")
if "snapshots" in modules: app.include_router(snapshots_router, prefix="/api/snapshots") # /snapshot endpoints

# Worker Control (System module handles worker status endpoint, but chat module logic drives it)
if "chat" in modules:
    from backend.worker_controller import worker_controller
    @app.get("/api/system/worker_status", dependencies=[Depends(verify_token)])
    async def get_worker_status_proxy(): return worker_controller.get_status()

    @app.post("/api/system/start_worker", dependencies=[Depends(verify_token)])
    async def start_worker_proxy(): return worker_controller.start_worker()

    @app.post("/api/system/stop_worker", dependencies=[Depends(verify_token)])
    async def stop_worker_proxy(): return worker_controller.stop_worker()

# Static Files
# Detect where dashboard.html is
static_dir = "."
if os.path.exists("web/dashboard.html"):
    static_dir = "web"
elif os.path.exists("dashboard.html"):
    static_dir = "."

print(f"[System] Serving static files from: {os.path.abspath(static_dir)}")

@app.get("/")
async def read_root():
    return FileResponse(f'{static_dir}/dashboard.html')

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    print(f"Starting server on port {current_port}...")
    uvicorn.run(app, host="0.0.0.0", port=current_port)
