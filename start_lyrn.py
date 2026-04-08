import os
import sys
import re
import psutil
import asyncio
import json
import datetime
import threading
import subprocess
import collections
import time
import hashlib
import shutil
import aiohttp
import aiofiles
from typing import Optional, List, Dict, Any
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Header, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn

from utils.helpers import _get_file_explanation

from models.schemas import (
    FileTreeSelectionModel,
    FileTreeProfileModel,
    InjectArtifactModel,
    PresetModel,
    ActiveConfigModel,
    ChatRequest,
    JobDefinitionModel,
    JobScheduleModel,
    CycleModel,
    ModelFetchRequest,
    SnapshotSaveModel,
    SnapshotLoadModel,
)

import platform
import struct
if platform.system() != "Windows":
    import pty
    import termios
    import fcntl

from fastapi import WebSocket, WebSocketDisconnect


from settings_manager import SettingsManager
from automation_controller import AutomationController
from chat_manager import ChatManager

try:
    import pynvml
except ImportError:
    pynvml = None

import core.state as state
from services.logger import logger
from services.claude import proxy_controller, claude_run_manager
from services.worker import worker_controller
from services.terminal import get_or_create_terminal_session, terminal_sessions_lock, terminal_sessions, maybe_cleanup_terminal_session
settings_manager = SettingsManager()
automation_controller = AutomationController()

# Initialize ChatManager (Needs settings to be loaded)
settings_manager.load_or_detect_first_boot()
role_mappings = {
    "assistant": "final_output",
    "model": "final_output",
    "thinking": "thinking_process",
    "analysis": "thinking_process"
}
chat_manager = ChatManager(
    settings_manager.settings.get("paths", {}).get("chat", "chat/"),
    settings_manager,
    role_mappings
)

# --- Helper Functions ---
def trigger_chat_generation(message: str, folder: str = "chat"):
    """Creates a chat file and triggers the worker."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{folder}/{folder}_{timestamp}.txt"
    filepath = os.path.abspath(filename)

    # Ensure directory
    os.makedirs(folder, exist_ok=True)

    # Write User Message
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"user\n{message}\n")
    print(f"[System] Created chat file: {filepath}")

    # Write Trigger
    with open("chat_trigger.txt", "w", encoding="utf-8") as f:
        f.write(filepath)
    print(f"[System] Wrote trigger file: chat_trigger.txt")

    return filepath, os.path.basename(filepath)

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

async def verify_token(x_token: Optional[str] = Header(None, alias="X-Token"), token: Optional[str] = None):
    # Check for No Auth Flag
    if Path("global_flags/no_auth").exists():
        return "NO_AUTH"

    # Support both Header (preferred) and Query Param (SSE/EventSource)
    auth_token = x_token or token
    if not state.LYRN_TOKEN or not auth_token or auth_token != state.LYRN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return auth_token

@app.get("/api/auth/status")
async def get_auth_status():
    if Path("global_flags/no_auth").exists():
        return {"required": False}
    return {"required": True}

@app.post("/api/verify_token", dependencies=[Depends(verify_token)])
async def verify_token_endpoint():
    return {"status": "valid"}

@app.get("/health")
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

# Logging Endpoints
@app.get("/api/logs", dependencies=[Depends(verify_token)])
async def stream_logs(request: Request):
    return StreamingResponse(logger.subscribe(request), media_type="text/event-stream")

@app.get("/api/logs/sessions", dependencies=[Depends(verify_token)])
async def list_log_sessions():
    return logger.list_sessions()

@app.get("/api/logs/sessions/{session_id}/chunks", dependencies=[Depends(verify_token)])
async def list_log_chunks(session_id: str):
    return logger.list_chunks(session_id)

@app.get("/api/logs/sessions/{session_id}/chunks/{chunk_id}", dependencies=[Depends(verify_token)])
async def get_log_chunk(session_id: str, chunk_id: str):
    return logger.get_chunk_content(session_id, chunk_id)

# --- Snapshot Management Endpoints ---

@app.get("/api/snapshots", dependencies=[Depends(verify_token)])
async def list_snapshots():
    """Lists available .sns files in the snapshots/ directory."""
    snapshots_dir = Path("snapshots")
    if not snapshots_dir.exists():
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        return []

    snapshots = []
    for f in snapshots_dir.glob("*.sns"):
        stat = f.stat()
        snapshots.append({
            "name": f.name,
            "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
        })
    return sorted(snapshots, key=lambda x: x['name'])

async def _save_components_to_build_prompt(components: List[Dict[str, Any]]):
    """Helper to save components to build_prompt directory."""
    try:
        base_dir = Path("build_prompt")
        base_dir.mkdir(parents=True, exist_ok=True)

        # 1. Save components.json (without content field)
        clean_components = []
        for c in components:
            copy = c.copy()
            if "content" in copy:
                del copy["content"]
            clean_components.append(copy)

        with open(base_dir / "components.json", "w", encoding='utf-8') as f:
            json.dump(clean_components, f, indent=2)

        # 2. Save content files
        for c in components:
            name = c.get("name")
            if not name or name == "RWI": continue

            content = c.get("content", "")
            comp_dir = base_dir / name
            comp_dir.mkdir(exist_ok=True)

            config_path = comp_dir / "config.json"
            config = {}
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                except: pass

            if "config" in c:
                frontend_config = c["config"]
                if "begin_bracket" in frontend_config: config["begin_bracket"] = frontend_config["begin_bracket"]
                if "end_bracket" in frontend_config: config["end_bracket"] = frontend_config["end_bracket"]
                if "rwi_text" in frontend_config: config["rwi_text"] = frontend_config["rwi_text"]

            if "content_file" not in config:
                config["content_file"] = "content.txt"

            with open(config_path, "w", encoding='utf-8') as f:
                json.dump(config, f, indent=2)

            with open(comp_dir / config["content_file"], "w", encoding='utf-8') as f:
                f.write(content)
        return True
    except Exception as e:
        print(f"Error saving to build_prompt: {e}")
        raise e

@app.post("/api/snapshots/save", dependencies=[Depends(verify_token)])
async def save_named_snapshot(data: SnapshotSaveModel):
    """Saves to a file AND updates the build_prompt."""
    try:
        # 1. Save to .sns file
        snapshots_dir = Path("snapshots")
        snapshots_dir.mkdir(parents=True, exist_ok=True)

        filename = data.filename
        if not filename.endswith(".sns"):
            filename += ".sns"

        file_path = snapshots_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data.components, f, indent=2)

        # 2. Update build_prompt (Active State)
        await _save_components_to_build_prompt(data.components)

        # 3. Update Settings (Active Snapshot)
        if not settings_manager.settings:
            settings_manager.load_or_detect_first_boot()

        settings_manager.settings["active_snapshot"] = filename
        settings_manager.save_settings()

        return {"success": True, "saved_as": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/snapshots/load", dependencies=[Depends(verify_token)])
async def load_named_snapshot(data: SnapshotLoadModel):
    """Loads a specific .sns file into build_prompt and returns content."""
    try:
        snapshots_dir = Path("snapshots")
        filename = data.filename
        file_path = snapshots_dir / filename

        if not file_path.exists():
             raise HTTPException(status_code=404, detail="Snapshot file not found")

        with open(file_path, "r", encoding="utf-8") as f:
            components = json.load(f)

        # 1. Update build_prompt (Active State)
        await _save_components_to_build_prompt(components)

        # 2. Update Settings
        if not settings_manager.settings:
            settings_manager.load_or_detect_first_boot()

        settings_manager.settings["active_snapshot"] = filename
        settings_manager.save_settings()

        return components
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Chat Endpoint
@app.get("/api/chat/history", dependencies=[Depends(verify_token)])
async def get_chat_history():
    """Returns the current chat history as a list of messages."""
    return chat_manager.get_chat_history_messages()

@app.delete("/api/chat", dependencies=[Depends(verify_token)])
async def clear_chat_history():
    """Clears all chat history files."""
    try:
        chat_dir = Path(settings_manager.settings.get("paths", {}).get("chat", "chat/"))
        if chat_dir.exists():
            for f in chat_dir.glob("*.txt"):
                try:
                    f.unlink()
                except OSError as e:
                    print(f"Failed to delete {f}: {e}")
        return {"success": True, "message": "Chat history cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/chat/{filename}", dependencies=[Depends(verify_token)])
async def delete_chat_file(filename: str):
    """Deletes a specific chat history file."""
    try:
        # Sanitize filename to prevent directory traversal
        filename = os.path.basename(filename)
        chat_dir = Path(settings_manager.settings.get("paths", {}).get("chat", "chat/"))
        file_path = chat_dir / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        file_path.unlink()
        return {"success": True, "message": f"Deleted {filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/stop", dependencies=[Depends(verify_token)])
async def stop_chat_generation():
    """Triggers the worker to stop the current generation."""
    try:
        with open("stop_trigger.txt", "w", encoding="utf-8") as f:
            f.write("stop")
        print("[API] Wrote stop_trigger.txt")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop generation: {e}")

@app.post("/api/chat", dependencies=[Depends(verify_token)])
async def chat_endpoint(request: ChatRequest):
    print(f"[API] Received chat request: {request.message[:50]}...")

    try:
        filepath, filename = trigger_chat_generation(request.message)
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Failed to trigger chat: {e}")

    async def event_generator():
        # Yield the filename first for UI tracking
        yield json.dumps({"filename": filename}) + "\n"
        last_pos = 0
        retries = 0
        started = False

        while True:
            await asyncio.sleep(0.1)
            try:
                if not os.path.exists(filepath):
                    continue

                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                    if not started:
                        # Check for "model" marker. Worker writes "\n\nmodel\n"
                        # We look for "model" preceded by newlines or start of file
                        start_idx = -1
                        match = re.search(r'(?:^|\n)model\n', content)
                        if match:
                            start_idx = match.start()
                            # Start reading from end of match
                            last_pos = match.end()
                            started = True

                        if not started:
                            # Check for error
                            if "[Error:" in content:
                                print("[API] Detected error in chat file.")
                                yield json.dumps({"response": "Error in worker."}) + "\n"
                                return

                            retries += 1
                            # Load timeout from settings (default 1800s = 30 mins)
                            # Loop sleeps 0.1s, so 1800s = 18000 iterations
                            timeout_seconds = settings_manager.settings.get("worker_timeout_seconds", 1800)
                            max_retries = timeout_seconds * 10

                            if retries > max_retries:
                                print(f"[API] Timeout waiting for worker response ({timeout_seconds}s).")
                                yield json.dumps({"response": "Timeout waiting for worker."}) + "\n"
                                return
                            continue

                    if started:
                        # Read from last_pos
                        current_len = len(content)
                        if current_len > last_pos:
                            new_text = content[last_pos:]

                            # Stream what we have
                            yield json.dumps({"response": new_text}) + "\n"
                            last_pos = current_len

                        # Check if worker is done
                        status_info = worker_controller.get_status()
                        llm_status = status_info.get("llm_status", "unknown")

                        # If idle or error or stopped, and we have consumed everything (which we just did), we are done.
                        # Note: We rely on the fact that the worker writes content THEN sets status to idle.
                        if llm_status in ["idle", "error", "stopped"]:
                            return

            except Exception as e:
                print(f"Error in stream: {e}")
                yield json.dumps({"response": f"Error: {e}"}) + "\n"
                return

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

# --- Model & Config Endpoints ---

async def _download_model_task(url: str, filename: str, expected_sha256: Optional[str], max_bytes: int):
    models_dir = Path("models")
    staging_dir = models_dir / "_staging"
    models_dir.mkdir(exist_ok=True)
    staging_dir.mkdir(exist_ok=True)

    part_file = staging_dir / f"{filename}.part"
    final_staging = staging_dir / filename
    dest_file = models_dir / filename

    try:
        state.active_downloads[filename]["status"] = "downloading"

        max_retries = 5
        base_delay = 2

        for attempt in range(max_retries):
            try:
                existing_bytes = 0
                if part_file.exists():
                    existing_bytes = part_file.stat().st_size

                headers = {}
                if existing_bytes > 0:
                    headers['Range'] = f'bytes={existing_bytes}-'

                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as resp:
                        if resp.status not in (200, 206):
                            raise ValueError(f"HTTP {resp.status}")

                        is_partial = (resp.status == 206)
                        if not is_partial and existing_bytes > 0:
                            existing_bytes = 0 # Server didn't respect Range header
                            # In this case we have to truncate the part file
                            mode = "wb"
                        else:
                            mode = "ab" if is_partial else "wb"

                        content_len = resp.headers.get("Content-Length")
                        total_size = int(content_len) + existing_bytes if content_len else existing_bytes

                        if max_bytes > 0 and total_size > max_bytes:
                             raise ValueError("File too large")

                        downloaded = existing_bytes

                        # We need to compute hash of the whole file at the end
                        last_log_time = time.time()

                        # Update total
                        state.active_downloads[filename]["total"] = total_size

                        async with aiofiles.open(part_file, mode) as f:
                            async for chunk in resp.content.iter_chunked(1024 * 1024): # 1MB chunks
                                downloaded += len(chunk)
                                if max_bytes > 0 and downloaded > max_bytes:
                                     raise ValueError("File limit exceeded")

                                await f.write(chunk)

                                # Update status
                                state.active_downloads[filename]["bytes"] = downloaded
                                if total_size > 0:
                                    state.active_downloads[filename]["pct"] = int(downloaded / total_size * 100)

                                if time.time() - last_log_time > 2:
                                    pct = ""
                                    if total_size > 0:
                                        pct = f" ({int(downloaded/total_size*100)}%)"
                                    await logger.emit("Info", f"Downloading {filename}: {downloaded // (1024*1024)}MB{pct}", "ModelManager")
                                    last_log_time = time.time()

                # If successful, break the retry loop
                break
            except ValueError as e:
                # Fatal errors, no retry
                raise e
            except Exception as e:
                err_msg = str(e) or e.__class__.__name__
                if attempt < max_retries - 1:
                    await logger.emit("Warning", f"Download interrupted: {err_msg}. Retrying in {base_delay}s... (Attempt {attempt+1}/{max_retries})", "ModelManager")
                    await asyncio.sleep(base_delay)
                    base_delay *= 2
                else:
                    raise e

        # Hash Verification
        state.active_downloads[filename]["status"] = "verifying"

        # Compute hash from the full downloaded file
        sha256 = hashlib.sha256()
        async with aiofiles.open(part_file, "rb") as f:
            while chunk := await f.read(1024 * 1024):
                sha256.update(chunk)

        computed_hash = sha256.hexdigest()
        if expected_sha256 and computed_hash.lower() != expected_sha256.lower():
            if part_file.exists(): part_file.unlink()
            raise ValueError(f"Hash mismatch. Computed: {computed_hash}")

        # Atomic Move
        shutil.move(str(part_file), str(final_staging))
        shutil.move(str(final_staging), str(dest_file))

        await logger.emit("Success", f"Downloaded model: {filename} ({downloaded} bytes)", "ModelManager")

        # Mark done
        state.active_downloads[filename]["status"] = "completed"
        state.active_downloads[filename]["bytes"] = downloaded

    except Exception as e:
        err_msg = str(e) or e.__class__.__name__
        print(f"Download error: {err_msg}")
        await logger.emit("Error", f"Download failed: {err_msg}", "ModelManager")
        state.active_downloads[filename]["status"] = "error"
        state.active_downloads[filename]["error"] = err_msg

@app.post("/api/models/fetch", dependencies=[Depends(verify_token)])
async def fetch_model(request: ModelFetchRequest, background_tasks: BackgroundTasks):
    url = request.url

    # 1. Determine Filename
    filename = request.filename
    if not filename:
        path = url.split("?")[0]
        filename = path.split("/")[-1]

    # Sanitize
    filename = os.path.basename(filename)
    if not filename or filename in ['.', '..']:
        raise HTTPException(status_code=400, detail="Invalid filename")

    if filename in state.active_downloads and state.active_downloads[filename]["status"] in ["pending", "downloading", "verifying"]:
        raise HTTPException(status_code=400, detail="Download already in progress")

    # 2. Size Limit
    max_bytes = int(os.environ.get("LYRN_MAX_MODEL_BYTES", 0))

    # Initialize tracking
    state.active_downloads[filename] = {
        "status": "pending",
        "bytes": 0,
        "total": 0,
        "pct": 0,
        "error": None,
        "timestamp": time.time()
    }

    # Start Background Task
    background_tasks.add_task(_download_model_task, url, filename, request.expected_sha256, max_bytes)

    await logger.emit("Info", f"Started download for {filename}", "ModelManager")
    return {"ok": True, "message": "Download started", "filename": filename}

@app.get("/api/models/downloads", dependencies=[Depends(verify_token)])
async def get_active_downloads():
    current_time = time.time()
    to_remove = []
    for fname, data in state.active_downloads.items():
        if data["status"] in ["completed", "error"]:
            # Clean up old statuses after 10 minutes
            if current_time - data.get("timestamp", 0) > 600:
                to_remove.append(fname)

    for fname in to_remove:
        del state.active_downloads[fname]

    return state.active_downloads

@app.get("/api/models/list", dependencies=[Depends(verify_token)])
async def list_models():
    """Lists available models in the models/ directory."""
    models_dir = Path("models")
    if not models_dir.exists():
        return []

    models = []
    for f in models_dir.iterdir():
        if f.is_file() and f.name != "_staging" and not f.name.endswith(".part"):
             stat = f.stat()
             models.append({
                 "name": f.name,
                 "bytes": stat.st_size,
                 "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
             })

    return sorted(models, key=lambda x: x['name'])

@app.get("/api/models/inspect", dependencies=[Depends(verify_token)])
async def inspect_model(name: str):
    models_dir = Path("models")
    f = models_dir / os.path.basename(name)

    if not f.exists() or not f.is_file():
        raise HTTPException(status_code=404, detail="Model not found")

    # Compute Hash
    # Synchronous for now as permitted, but let's try to be nice
    # Streaming hash
    loop = asyncio.get_running_loop()
    def compute_hash():
        sha256 = hashlib.sha256()
        with open(f, "rb") as stream:
             while chunk := stream.read(1024*1024):
                  sha256.update(chunk)
        return sha256.hexdigest()

    computed_hash = await loop.run_in_executor(None, compute_hash)

    stat = f.stat()
    return {
        "name": f.name,
        "bytes": stat.st_size,
        "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "sha256": computed_hash
    }

@app.delete("/api/models/delete", dependencies=[Depends(verify_token)])
async def delete_model(name: str):
    models_dir = Path("models")
    filename = os.path.basename(name)

    if filename == "_staging":
         raise HTTPException(status_code=400, detail="Cannot delete staging dir")

    f = models_dir / filename
    if not f.exists():
        raise HTTPException(status_code=404, detail="Model not found")

    try:
        if f.is_dir():
             # Should not happen given list filter but safety first
             raise HTTPException(status_code=400, detail="Cannot delete directories")
        f.unlink()
        await logger.emit("Info", f"Deleted model: {filename}", "ModelManager")
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/config/presets", dependencies=[Depends(verify_token)])
async def get_presets():
    """Gets all model presets."""
    if not settings_manager.settings:
        settings_manager.load_or_detect_first_boot()

    return settings_manager.settings.get("model_presets", {})

@app.post("/api/config/presets", dependencies=[Depends(verify_token)])
async def save_preset(preset: PresetModel):
    """Saves a model preset."""
    if not settings_manager.settings:
        settings_manager.load_or_detect_first_boot()

    if "model_presets" not in settings_manager.settings:
        settings_manager.settings["model_presets"] = {}

    settings_manager.settings["model_presets"][preset.preset_id] = preset.config
    settings_manager.save_settings()
    return {"success": True, "message": f"Preset {preset.preset_id} saved."}

@app.post("/api/config/active", dependencies=[Depends(verify_token)])
async def set_active_config(config: ActiveConfigModel):
    """Sets the active model configuration."""
    if not settings_manager.settings:
        settings_manager.load_or_detect_first_boot()

    settings_manager.settings["active"] = config.config
    settings_manager.save_settings()
    return {"success": True, "message": "Active configuration updated."}

@app.get("/api/config/active", dependencies=[Depends(verify_token)])
async def get_active_config():
    """Gets the active model configuration."""
    if not settings_manager.settings:
        settings_manager.load_or_detect_first_boot()

    return settings_manager.settings.get("active", {})

@app.get("/api/config", dependencies=[Depends(verify_token)])
async def get_config():
    """Gets the full system configuration."""
    if not settings_manager.settings:
        settings_manager.load_or_detect_first_boot()
    return {
        "settings": settings_manager.settings,
        "ui_settings": settings_manager.ui_settings
    }

@app.post("/api/config", dependencies=[Depends(verify_token)])
async def save_config(data: Dict[str, Any]):
    """Saves the full system configuration."""
    if "settings" in data:
        settings_manager.settings = data["settings"]
    if "ui_settings" in data:
        settings_manager.ui_settings = data["ui_settings"]

    settings_manager.save_settings()
    return {"success": True, "message": "Settings saved."}

# --- Worker Control Endpoints ---

@app.get("/api/system/worker_status", dependencies=[Depends(verify_token)])
async def get_worker_status():
    return worker_controller.get_status()

@app.post("/api/system/start_worker", dependencies=[Depends(verify_token)])
async def start_worker():
    return worker_controller.start_worker()

@app.post("/api/system/stop_worker", dependencies=[Depends(verify_token)])
async def stop_worker():
    return worker_controller.stop_worker()

@app.post("/api/system/start_claude_proxy", dependencies=[Depends(verify_token)])
async def start_claude_proxy():
    return proxy_controller.start_proxy()

@app.post("/api/system/stop_claude_proxy", dependencies=[Depends(verify_token)])
async def stop_claude_proxy():
    return proxy_controller.stop_proxy()

@app.get("/api/system/proxy_status", dependencies=[Depends(verify_token)])
async def get_proxy_status():
    return proxy_controller.get_status()

# --- Claude Code Orchestrator Endpoints ---

@app.get("/api/claude/auth", dependencies=[Depends(verify_token)])
async def claude_auth():
    return claude_run_manager.auth_status()

@app.post("/api/claude/validate_cwd", dependencies=[Depends(verify_token)])
async def claude_validate_cwd(req: Request):
    try:
        body = await req.json()
    except Exception:
        body = {}
    return claude_run_manager.resolve_cwd((body or {}).get("cwd"))

@app.post("/api/claude/preview", dependencies=[Depends(verify_token)])
async def claude_preview(req: Request):
    try:
        body = await req.json()
    except Exception:
        body = {}
    return claude_run_manager.preview(body or {})

@app.get("/api/claude/runs", dependencies=[Depends(verify_token)])
async def claude_list_runs():
    return {"runs": claude_run_manager.list_runs()}

@app.post("/api/claude/runs", dependencies=[Depends(verify_token)])
async def claude_start_run(req: Request):
    try:
        body = await req.json()
    except Exception:
        body = {}
    return claude_run_manager.start_run(body or {})

@app.get("/api/claude/runs/{run_id}", dependencies=[Depends(verify_token)])
async def claude_get_run(run_id: str):
    run = claude_run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return run

@app.get("/api/claude/runs/{run_id}/transcript", dependencies=[Depends(verify_token)])
async def claude_get_transcript(run_id: str):
    run = claude_run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    text = claude_run_manager.get_transcript(run_id)
    return {"run_id": run_id, "transcript": text}

@app.get("/api/claude/runs/{run_id}/transcript/download", dependencies=[Depends(verify_token)])
async def claude_download_transcript(run_id: str):
    run = claude_run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    path = run.get("transcript_path", "")
    if not path or not Path(path).exists():
        raise HTTPException(status_code=404, detail="transcript file missing")
    return FileResponse(path, filename=f"{run_id}.log", media_type="text/plain")

@app.get("/api/claude/runs/{run_id}/diff", dependencies=[Depends(verify_token)])
async def claude_get_diff(run_id: str):
    run = claude_run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return claude_run_manager.get_diff(run_id)

@app.post("/api/claude/runs/{run_id}/approve", dependencies=[Depends(verify_token)])
async def claude_approve(run_id: str):
    return claude_run_manager.approve(run_id)

@app.post("/api/claude/runs/{run_id}/reject", dependencies=[Depends(verify_token)])
async def claude_reject(run_id: str):
    return claude_run_manager.reject(run_id)

@app.delete("/api/claude/runs/{run_id}", dependencies=[Depends(verify_token)])
async def claude_delete_run(run_id: str):
    return claude_run_manager.delete_run(run_id)

# --- Automation Endpoints ---

@app.get("/api/automation/jobs", dependencies=[Depends(verify_token)])
async def get_jobs():
    return automation_controller.job_definitions

@app.post("/api/automation/jobs", dependencies=[Depends(verify_token)])
async def save_job(job: JobDefinitionModel):
    automation_controller.save_job_definition(job.name, job.instructions, job.trigger, job.scripts)
    return {"success": True}

@app.delete("/api/automation/jobs/{job_name}", dependencies=[Depends(verify_token)])
async def delete_job(job_name: str):
    automation_controller.delete_job_definition(job_name)
    return {"success": True}

@app.get("/api/automation/scripts", dependencies=[Depends(verify_token)])
async def get_scripts():
    return automation_controller.get_available_scripts()

@app.get("/api/automation/history", dependencies=[Depends(verify_token)])
async def get_job_history():
    return automation_controller.get_job_history()

@app.get("/api/automation/job_content", dependencies=[Depends(verify_token)])
async def get_job_content(path: str):
    """Reads the content of a job file."""
    try:
        # Security check: Ensure path is within jobs/ folder
        requested_path = Path(path).resolve()
        jobs_dir = Path("jobs").resolve()

        if not str(requested_path).startswith(str(jobs_dir)):
            raise HTTPException(status_code=403, detail="Access denied: Invalid file path.")

        if not requested_path.exists():
            raise HTTPException(status_code=404, detail="File not found.")

        return {"content": requested_path.read_text(encoding="utf-8")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/automation/history", dependencies=[Depends(verify_token)])
async def clear_job_history():
    automation_controller.clear_job_history()
    return {"success": True}

@app.get("/api/automation/schedule", dependencies=[Depends(verify_token)])
async def get_schedule():
    return automation_controller.get_queue()

@app.post("/api/automation/schedule", dependencies=[Depends(verify_token)])
async def add_schedule(item: JobScheduleModel):
    automation_controller.add_job(
        name=item.job_name,
        priority=item.priority,
        when=item.scheduled_datetime_iso,
        args=item.args,
        job_id=item.id
    )
    return {"success": True}

@app.delete("/api/automation/schedule/{job_id}", dependencies=[Depends(verify_token)])
async def delete_schedule(job_id: str):
    automation_controller.remove_job_from_queue(job_id)
    return {"success": True}

@app.get("/api/automation/cycles", dependencies=[Depends(verify_token)])
async def get_cycles():
    return automation_controller.get_cycles()

@app.post("/api/automation/cycles", dependencies=[Depends(verify_token)])
async def save_cycle(cycle: CycleModel):
    automation_controller.save_cycle(cycle.name, cycle.triggers)
    return {"success": True}

@app.delete("/api/automation/cycles/{cycle_name}", dependencies=[Depends(verify_token)])
async def delete_cycle(cycle_name: str):
    automation_controller.delete_cycle(cycle_name)
    return {"success": True}

# --- File Tree Viewer Endpoints ---

@app.get("/api/fs/list", dependencies=[Depends(verify_token)])
async def fs_list(path: str):
    """Returns directory contents for the given path."""
    try:
        req_path = Path(path).resolve()
        if not req_path.exists() or not req_path.is_dir():
            raise HTTPException(status_code=404, detail="Directory not found or is not a directory.")

        children = []

        # Default ignore list
        ignore_dirs = {'node_modules', '__pycache__', 'dist', 'build', 'target', 'venv', 'env', '.venv', '.git'}

        for entry in os.scandir(req_path):
            # Skip hidden files and some common huge directories
            if entry.name.startswith('.') or entry.name in ignore_dirs:
                continue

            is_dir = entry.is_dir()
            children.append({
                "name": entry.name,
                "path": entry.path,
                "is_dir": is_dir
            })

        return {
            "name": req_path.name,
            "path": str(req_path),
            "children": children
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/fs/compile", dependencies=[Depends(verify_token)])
async def fs_compile(payload: FileTreeSelectionModel):
    """Compiles the selected tree into a repo-RWI artifact."""
    root_path = Path(payload.root_path)
    selections = payload.selections

    # Exclusions
    ignore_exts = {'.pyc', '.exe', '.dll', '.so', '.dylib', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.zip', '.tar', '.gz'}
    max_file_size = 500 * 1024  # 500 KB limit for expansion

    artifact_lines = []

    # 1. Header
    artifact_lines.append("==================================================================")
    artifact_lines.append(f"REPOSITORY CONTEXT: {payload.root_name}")
    artifact_lines.append(f"LOCAL PATH: {root_path}")
    artifact_lines.append(f"GENERATED: {datetime.datetime.now().isoformat()}")
    artifact_lines.append("==================================================================\n")

    # 2. Structured Tree Listing
    artifact_lines.append("### REPOSITORY STRUCTURE ###")
    artifact_lines.append("The following files and directories are present in the repository:")

    expanded_files = [] # Tuples of (relative_path, full_path, explanation)

    for rel_path_str, state in selections.items():
        if state.get("include"):
            is_dir = state.get("is_dir", False)
            icon = "📁" if is_dir else "📄"
            depth = len(rel_path_str.replace('\\', '/').split('/')) - 1
            indent = "  " * depth

            # Simple explanation
            full_path = root_path / rel_path_str
            explanation = _get_file_explanation(full_path) if not is_dir else "Folder"

            expand_mark = "[EXPANDED]" if state.get("expand") and not is_dir else ""
            artifact_lines.append(f"{indent}- {icon} {rel_path_str} : {explanation} {expand_mark}")

        if state.get("expand"):
            # If it's a directory, we could recursively expand, but for phase 1 we trust the user selected files directly
            # or we expand files inside. For now, let's just expand explicitly selected files.
            is_dir = state.get("is_dir", False)
            if not is_dir:
                full_path = root_path / rel_path_str
                expanded_files.append((rel_path_str, full_path, _get_file_explanation(full_path)))
            else:
                # Recursively add files in the expanded directory
                dir_path = root_path / rel_path_str
                if dir_path.exists() and dir_path.is_dir():
                    for root, _, files in os.walk(dir_path):
                        for file in files:
                            if file.startswith('.'): continue
                            fpath = Path(root) / file
                            rpath = str(fpath.relative_to(root_path)).replace('\\', '/')
                            expanded_files.append((rpath, fpath, _get_file_explanation(fpath)))


    # Deduplicate expanded files (in case a file AND its parent dir were marked 'expand')
    seen = set()
    unique_expanded = []
    for r, f, e in expanded_files:
        if r not in seen:
            seen.add(r)
            unique_expanded.append((r, f, e))

    # 3. Content Expansion
    artifact_lines.append("\n### FILE CONTENTS ###")
    artifact_lines.append("The following files have been expanded for detailed inspection:\n")

    for rel_path, full_path, explanation in unique_expanded:
        if not full_path.exists():
            continue

        if full_path.suffix.lower() in ignore_exts:
            continue

        try:
            stat = full_path.stat()
            if stat.st_size > max_file_size:
                artifact_lines.append(f"--- FILE: {rel_path} ---")
                artifact_lines.append(f"Explanation: {explanation}")
                artifact_lines.append(f"[CONTENT SKIPPED: File size ({stat.st_size} bytes) exceeds {max_file_size} bytes limit]\n")
                continue

            content = full_path.read_text(encoding='utf-8')

            artifact_lines.append(f"--- FILE: {rel_path} ---")
            artifact_lines.append(f"Explanation: {explanation}")
            artifact_lines.append("Content:")
            artifact_lines.append("```")
            artifact_lines.append(content)
            artifact_lines.append("```\n")

        except UnicodeDecodeError:
            artifact_lines.append(f"--- FILE: {rel_path} ---")
            artifact_lines.append(f"Explanation: {explanation}")
            artifact_lines.append("[CONTENT SKIPPED: Binary file detected]\n")
        except Exception as e:
            artifact_lines.append(f"--- FILE: {rel_path} ---")
            artifact_lines.append(f"[ERROR READING FILE: {e}]\n")

    return {"artifact": "\n".join(artifact_lines)}

@app.post("/api/fs/inject", dependencies=[Depends(verify_token)])
async def fs_inject(payload: InjectArtifactModel):
    """Saves the artifact to be injected on the next run."""
    try:
        flags_dir = Path("global_flags")
        flags_dir.mkdir(exist_ok=True)
        with open(flags_dir / "repo_context.txt", "w", encoding="utf-8") as f:
            f.write(payload.artifact)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/fs/inject", dependencies=[Depends(verify_token)])
async def fs_clear_inject():
    """Clears the injected repo context."""
    try:
        context_file = Path("global_flags/repo_context.txt")
        if context_file.exists():
            context_file.unlink()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/fs/profiles", dependencies=[Depends(verify_token)])
async def get_fs_profiles():
    try:
        profiles_dir = Path("repo_profiles")
        if not profiles_dir.exists(): return []
        return [f.stem for f in profiles_dir.glob("*.json")]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/fs/profiles/{name}", dependencies=[Depends(verify_token)])
async def load_fs_profile(name: str):
    try:
        file_path = Path("repo_profiles") / f"{name}.json"
        if not file_path.exists(): raise HTTPException(status_code=404, detail="Profile not found")
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/fs/profiles", dependencies=[Depends(verify_token)])
async def save_fs_profile(payload: FileTreeProfileModel):
    try:
        profiles_dir = Path("repo_profiles")
        profiles_dir.mkdir(exist_ok=True)
        file_path = profiles_dir / f"{payload.name}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(payload.dict(), f, indent=2)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Snapshot Builder Endpoints ---

@app.get("/api/snapshot", dependencies=[Depends(verify_token)])
async def get_snapshot():
    """Reads components and their content."""
    try:
        base_dir = Path("build_prompt")
        comp_path = base_dir / "components.json"

        if not comp_path.exists():
            return [] # Return empty list if no file

        with open(comp_path, 'r', encoding='utf-8') as f:
            components = json.load(f)

        # Enhance components with content
        for comp in components:
            name = comp.get("name")
            if name == "RWI":
                continue

            # Look for content in subdir
            comp_dir = base_dir / name
            config_path = comp_dir / "config.json"

            content_file = "content.txt"

            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        c = json.load(f)
                        content_file = c.get("content_file", "content.txt")
                except: pass

            content_path = comp_dir / content_file
            if content_path.exists():
                try:
                    comp["content"] = content_path.read_text(encoding='utf-8')
                except:
                    comp["content"] = ""
            else:
                 comp["content"] = ""

        return components
    except Exception as e:
        print(f"Error getting snapshot: {e}")
        return []

@app.post("/api/snapshot", dependencies=[Depends(verify_token)])
async def save_snapshot(components: List[Dict[str, Any]]):
    """Saves components list and updates content files. (Legacy/Quick Save)"""
    try:
        await _save_components_to_build_prompt(components)
        return {"success": True}
    except Exception as e:
        print(f"Error saving snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/snapshot/rebuild", dependencies=[Depends(verify_token)])
async def rebuild_snapshot():
    """Triggers a snapshot rebuild in the worker."""
    try:
        with open("rebuild_trigger.txt", "w", encoding='utf-8') as f:
            f.write("rebuild")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@app.websocket("/api/terminal/{sid}")
async def terminal_stream_ws(sid: str, websocket: WebSocket, token: Optional[str] = None, cwd: Optional[str] = None):
    try:
        # Auth check
        if not Path("global_flags/no_auth").exists():
            if not state.LYRN_TOKEN or not token or token != state.LYRN_TOKEN:
                print(f"[Terminal] Denied access. Expected: {state.LYRN_TOKEN} Got: {token}")
                await websocket.close(code=4003)
                return

        # Validate optional cwd
        safe_cwd: Optional[str] = None
        if cwd:
            try:
                p = Path(cwd).expanduser()
                if p.is_dir():
                    safe_cwd = str(p.resolve())
                else:
                    print(f"[Terminal] Ignoring invalid cwd: {cwd}")
            except Exception as e:
                print(f"[Terminal] cwd validation error: {e}")

        await websocket.accept()
        session = await get_or_create_terminal_session(sid, safe_cwd)

        session.subscribers.add(websocket)
        print(f"[Terminal] Connected {sid}")

        for chunk in session.history:
             await websocket.send_text(json.dumps({"type": "output", "data": chunk}))

        while True:
            msg_text = await websocket.receive_text()
            msg = json.loads(msg_text)

            if msg["type"] == "input":
                session.write_input(msg["data"])
            elif msg["type"] == "resize":
                session.resize(msg.get("cols", 80), msg.get("rows", 24))

    except WebSocketDisconnect:
        print(f"[Terminal] Disconnected {sid}")
    except Exception as e:
        print(f"[Terminal] Error: {e}")
    finally:
        if 'session' in locals():
            session.subscribers.discard(websocket)
            if not session.subscribers:
                asyncio.create_task(maybe_cleanup_terminal_session(sid))

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
