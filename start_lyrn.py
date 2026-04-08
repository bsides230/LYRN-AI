import os
import asyncio
import datetime
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn

from core.registry import settings_manager, automation_controller, chat_manager
from utils.helpers import trigger_chat_generation

import core.state as state
from services.logger import logger

# --- Scheduler Loop ---
async def scheduler_loop():
    print("[Scheduler] Starting scheduler loop...")
    while True:
        try:
            # Check for due jobs
            job = automation_controller.get_next_due_job()
            if job:
                print(f"[Scheduler] Executing job: {job.name}")

                # 1. Execute Scripts if any
                scripts_ok = True
                if job.scripts:
                    print(f"[Scheduler] Running scripts for job: {job.name}")
                    # Run in executor to avoid blocking the event loop
                    result = await state.main_loop.run_in_executor(None, automation_controller.execute_job_scripts, job)
                    if result["status"] != "success":
                        print(f"[Scheduler] Scripts failed for job {job.name}. Aborting chat generation.")
                        scripts_ok = False

                # 2. Trigger Chat if scripts ok (or no scripts) AND prompt exists
                if scripts_ok:
                    if job.prompt:
                        # Use "jobs" folder for automated tasks
                        filepath, _ = trigger_chat_generation(job.prompt, folder="jobs")

                        # Log the prompt generation step
                        automation_controller.log_job_history(
                            job.name,
                            [{"message": "Prompt triggered successfully."}],
                            "success",
                            filepath=filepath
                        )
                    elif not job.scripts:
                        # Only log this if there were no scripts either
                        print(f"[Scheduler] Job {job.name} has no prompt/instructions and no scripts.")

            await asyncio.sleep(5) # Check every 5 seconds
        except Exception as e:
            print(f"[Scheduler] Error in loop: {e}")
            await asyncio.sleep(5)

# --- App Setup ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    state.main_loop = asyncio.get_running_loop()

    # Load Admin Token
    token_file = Path("admin_token.txt")
    if token_file.exists():
        try:
            state.LYRN_TOKEN = token_file.read_text(encoding="utf-8").strip()
            print("[System] Loaded admin token from admin_token.txt")
        except Exception as e:
            print(f"[System] Failed to read admin_token.txt: {e}")

    # Fallback to env var
    if not state.LYRN_TOKEN:
        state.LYRN_TOKEN = os.environ.get("LYRN_MODEL_TOKEN")
        if state.LYRN_TOKEN:
            print("[System] Loaded admin token from Environment Variable")
        else:
            print("[System] Warning: No admin token found (admin_token.txt or LYRN_MODEL_TOKEN). Model management will be unavailable.")

    await logger.emit("Info", "Backend started.", "System")

    # Start Scheduler
    asyncio.create_task(scheduler_loop())

    yield

app = FastAPI(title="LYRN v6 Backend", lifespan=lifespan)

# Determine allowed origins
allowed_origins = settings_manager.settings.get("allowed_origins", [])
current_port = 8000
try:
    if os.path.exists("port.txt"):
        with open("port.txt", "r") as f:
            val = f.read().strip()
            if val.isdigit():
                current_port = int(val)
except: pass

defaults = [
    f"http://localhost:{current_port}",
    f"http://127.0.0.1:{current_port}"
]
# Ensure defaults are present
for d in defaults:
    if d not in allowed_origins:
        allowed_origins.append(d)

print(f"[System] Allowed Origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["X-Token", "Content-Type", "Authorization"],
)

# --- Routes ---

from routers.logs_router import router as logs_router
from routers.chat_router import router as chat_router
from routers.models_router import router as models_router
from routers.config_router import router as config_router
from routers.system_router import router as system_router
from routers.claude_router import router as claude_router
from routers.automation_router import router as automation_router
from routers.fs_router import router as fs_router
from routers.snapshot_router import router as snapshot_router
from routers.terminal_router import router as terminal_router

app.include_router(logs_router)
app.include_router(chat_router)
app.include_router(models_router)
app.include_router(config_router)
app.include_router(system_router)
app.include_router(claude_router)
app.include_router(automation_router)
app.include_router(fs_router)
app.include_router(snapshot_router)
app.include_router(terminal_router)

# Serve dashboard at root

@app.get("/")
async def read_root():
    return FileResponse('LYRN_v6/dashboard.html')

# Serve Static Files
app.mount("/", StaticFiles(directory="LYRN_v6", html=True), name="static")

if __name__ == "__main__":
    port = 8000
    try:
        if os.path.exists("port.txt"):
            with open("port.txt", "r") as f:
                val = f.read().strip()
                if val.isdigit():
                    port = int(val)
    except Exception as e:
        print(f"Failed to load port.txt: {e}")

    print(f"Starting server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
