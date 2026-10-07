import os
import time
import hashlib
import shutil
import asyncio
import datetime
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
import aiohttp
import aiofiles
import json
from core.security import verify_token
import core.state as state
from models.schemas import ModelFetchRequest, TestBenchmarkRequest
from services.logger import logger
from services.worker import worker_controller

router = APIRouter(prefix="/api/models", tags=["models"])

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

@router.post("/fetch", dependencies=[Depends(verify_token)])
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

@router.get("/downloads", dependencies=[Depends(verify_token)])
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

@router.get("/favorites", dependencies=[Depends(verify_token)])
async def get_favorites():
    """Gets the list of favorite models from model_favorites.json"""
    favorites_path = Path("model_favorites.json")
    if not favorites_path.exists():
        return {"favorites": []}

    import json
    try:
        with open(favorites_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"favorites": []}

@router.post("/favorites", dependencies=[Depends(verify_token)])
async def add_favorite(request: dict):
    """Adds a new favorite model from a HuggingFace URL"""
    url = request.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    # Try to parse HF URL
    # format: https://huggingface.co/{user}/{repo}/resolve/main/{filename}
    filename = request.get("filename")
    if not filename:
        filename = url.split("/")[-1]

    new_favorite = {
        "id": filename.split(".")[0],
        "family": "custom",
        "series": "custom",
        "model": filename.split(".")[0],
        "size": None,
        "variant": None,
        "quant": None,
        "format": filename.split(".")[-1] if "." in filename else "gguf",
        "filename": filename,
        "url": url
    }

    favorites_path = Path("model_favorites.json")
    favorites = {"favorites": []}
    import json

    if favorites_path.exists():
        try:
            with open(favorites_path, "r", encoding="utf-8") as f:
                favorites = json.load(f)
        except Exception:
            pass

    favorites["favorites"].append(new_favorite)

    with open(favorites_path, "w", encoding="utf-8") as f:
        json.dump(favorites, f, indent=2)

    return {"success": True, "favorite": new_favorite}


@router.get("/list", dependencies=[Depends(verify_token)])
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

@router.get("/inspect", dependencies=[Depends(verify_token)])
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

@router.delete("/delete", dependencies=[Depends(verify_token)])
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

@router.post("/test_benchmark", dependencies=[Depends(verify_token)])
async def trigger_benchmark(req: TestBenchmarkRequest):
    """Triggers an inference benchmark test through the model runner."""
    status = worker_controller.get_status()
    if not status.get("running"):
        raise HTTPException(status_code=400, detail="Model runner is not running. Click 'Start System' first.")

    llm_status_path = Path("global_flags/llm_status.txt")
    if llm_status_path.exists():
        cur_status = llm_status_path.read_text(encoding="utf-8").strip()
        if cur_status == "busy":
            raise HTTPException(status_code=400, detail="Model is currently busy executing another task.")

    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Test prompt cannot be empty.")

    # 1. Format job context for benchmark
    os.makedirs("global_flags", exist_ok=True)
    os.makedirs("job_output", exist_ok=True)

    job_context = (
        "##JI:START##\n"
        "[Manual Model Inference & Speed Benchmark]\n"
        f"{req.prompt.strip()}\n"
        "##JI:END##\n"
        "##AF:START##\n"
        "##AF:END##\n"
    )
    with open("global_flags/job_context.txt", "w", encoding="utf-8") as f:
        f.write(job_context)

    # 2. Generate unique test output filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    test_id = f"bench_{timestamp}.txt"
    target_output = Path("job_output") / test_id
    if target_output.exists():
        try:
            target_output.unlink()
        except OSError:
            pass

    # 3. Write trigger file with target output filename as content
    trigger_path = Path("global_flags") / f"{test_id}.trigger"
    with open(trigger_path, "w", encoding="utf-8") as f:
        f.write(test_id)

    return {"success": True, "test_id": test_id}

@router.get("/test_status/{test_id}", dependencies=[Depends(verify_token)])
async def get_benchmark_status(test_id: str):
    """Returns streaming output and metrics for the given benchmark run."""
    safe_name = os.path.basename(test_id)
    output_path = Path("job_output") / safe_name

    output_text = ""
    if output_path.exists():
        try:
            with open(output_path, "r", encoding="utf-8", errors="replace") as f:
                output_text = f.read()
        except Exception:
            pass

    llm_status = "idle"
    status_path = Path("global_flags/llm_status.txt")
    if status_path.exists():
        try:
            llm_status = status_path.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    # Determine execution state
    trigger_path = Path("global_flags") / f"{safe_name}.trigger"
    if trigger_path.exists():
        exec_state = "queued"
    elif llm_status == "busy":
        exec_state = "generating"
    elif output_path.exists() and llm_status == "idle":
        exec_state = "complete"
    elif llm_status == "error":
        exec_state = "error"
    else:
        exec_state = llm_status

    stats = {}
    stats_path = Path("global_flags/llm_stats.json")
    if stats_path.exists():
        try:
            with open(stats_path, "r", encoding="utf-8") as f:
                stats = json.load(f)
        except Exception:
            pass

    # Fetch real-time hardware telemetry
    try:
        from routers.system_router import health_check
        h_data = await health_check()
        stats["hw_telemetry"] = {
            "cpu": h_data.get("cpu"),
            "ram": h_data.get("ram"),
            "gpu": h_data.get("gpu")
        }
    except Exception:
        pass

    return {
        "test_id": safe_name,
        "state": exec_state,
        "output": output_text,
        "stats": stats
    }

@router.post("/test_stop", dependencies=[Depends(verify_token)])
async def stop_benchmark():
    """Stops the active benchmark generation."""
    try:
        with open("stop_trigger.txt", "w", encoding="utf-8") as f:
            f.write("stop")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
