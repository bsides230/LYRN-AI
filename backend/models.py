import os
import time
import json
import shutil
import hashlib
import asyncio
import aiohttp
import aiofiles
import datetime
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from backend.auth import verify_token
from backend.logger import logger

router = APIRouter()

# Global Active Downloads
active_downloads = {} # filename -> { status, bytes, total, pct, error, timestamp }

class ModelFetchRequest(BaseModel):
    url: str
    filename: Optional[str] = None
    expected_sha256: Optional[str] = None

async def _download_model_task(url: str, filename: str, expected_sha256: Optional[str], max_bytes: int):
    models_dir = Path("models")
    staging_dir = models_dir / "_staging"
    models_dir.mkdir(exist_ok=True)
    staging_dir.mkdir(exist_ok=True)

    part_file = staging_dir / f"{filename}.part"
    final_staging = staging_dir / filename
    dest_file = models_dir / filename

    try:
        active_downloads[filename]["status"] = "downloading"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200: raise Exception(f"HTTP {resp.status}")

                content_len = resp.headers.get("Content-Length")
                if max_bytes > 0 and content_len and int(content_len) > max_bytes:
                     raise Exception("File too large")

                downloaded = 0
                sha256 = hashlib.sha256()
                total_size = int(content_len) if content_len else 0
                last_log_time = time.time()
                active_downloads[filename]["total"] = total_size

                async with aiofiles.open(part_file, "wb") as f:
                    async for chunk in resp.content.iter_chunked(1024 * 1024):
                        downloaded += len(chunk)
                        if max_bytes > 0 and downloaded > max_bytes: raise Exception("File limit exceeded")
                        sha256.update(chunk)
                        await f.write(chunk)

                        active_downloads[filename]["bytes"] = downloaded
                        if total_size > 0:
                            active_downloads[filename]["pct"] = int(downloaded / total_size * 100)

                        if time.time() - last_log_time > 2:
                            pct = f" ({int(downloaded/total_size*100)}%)" if total_size > 0 else ""
                            await logger.emit("Info", f"Downloading {filename}: {downloaded // (1024*1024)}MB{pct}", "ModelManager")
                            last_log_time = time.time()

        active_downloads[filename]["status"] = "verifying"
        computed_hash = sha256.hexdigest()
        if expected_sha256 and computed_hash.lower() != expected_sha256.lower():
            if part_file.exists(): part_file.unlink()
            raise Exception(f"Hash mismatch. Computed: {computed_hash}")

        shutil.move(str(part_file), str(final_staging))
        shutil.move(str(final_staging), str(dest_file))

        await logger.emit("Success", f"Downloaded {filename}", "ModelManager")
        active_downloads[filename]["status"] = "completed"
        active_downloads[filename]["bytes"] = downloaded

    except Exception as e:
        if part_file.exists():
            try: part_file.unlink()
            except: pass
        await logger.emit("Error", f"Download failed: {str(e)}", "ModelManager")
        active_downloads[filename]["status"] = "error"
        active_downloads[filename]["error"] = str(e)

@router.post("/fetch")
async def fetch_model(request: ModelFetchRequest, background_tasks: BackgroundTasks, token: str = Depends(verify_token)):
    url = request.url
    filename = request.filename
    if not filename:
        path = url.split("?")[0]
        filename = path.split("/")[-1]

    filename = os.path.basename(filename)
    if not filename or filename in ['.', '..']: raise HTTPException(status_code=400, detail="Invalid filename")

    if filename in active_downloads and active_downloads[filename]["status"] in ["pending", "downloading", "verifying"]:
        raise HTTPException(status_code=400, detail="Download in progress")

    max_bytes = int(os.environ.get("LYRN_MAX_MODEL_BYTES", 0))
    active_downloads[filename] = {
        "status": "pending", "bytes": 0, "total": 0, "pct": 0, "error": None, "timestamp": time.time()
    }

    background_tasks.add_task(_download_model_task, url, filename, request.expected_sha256, max_bytes)
    await logger.emit("Info", f"Started download for {filename}", "ModelManager")
    return {"ok": True, "message": "Download started", "filename": filename}

@router.get("/downloads")
async def get_active_downloads(token: str = Depends(verify_token)):
    current = time.time()
    to_remove = [f for f, d in active_downloads.items() if d["status"] in ["completed", "error"] and current - d.get("timestamp", 0) > 600]
    for f in to_remove: del active_downloads[f]
    return active_downloads

@router.get("/list")
async def list_models(token: str = Depends(verify_token)):
    models_dir = Path("models")
    if not models_dir.exists(): return []
    models = []
    for f in models_dir.iterdir():
        if f.is_file() and f.name != "_staging" and not f.name.endswith(".part"):
             models.append({
                 "name": f.name,
                 "bytes": f.stat().st_size,
                 "modified": datetime.datetime.fromtimestamp(f.stat().st_mtime).isoformat()
             })
    return sorted(models, key=lambda x: x['name'])

@router.get("/inspect")
async def inspect_model(name: str, token: str = Depends(verify_token)):
    models_dir = Path("models")
    f = models_dir / os.path.basename(name)
    if not f.exists(): raise HTTPException(status_code=404, detail="Model not found")

    loop = asyncio.get_running_loop()
    def compute_hash():
        h = hashlib.sha256()
        with open(f, "rb") as s:
             while c := s.read(1024*1024): h.update(c)
        return h.hexdigest()

    computed_hash = await loop.run_in_executor(None, compute_hash)
    return {
        "name": f.name, "bytes": f.stat().st_size,
        "modified": datetime.datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        "sha256": computed_hash
    }

@router.delete("/delete")
async def delete_model(name: str, token: str = Depends(verify_token)):
    f = Path("models") / os.path.basename(name)
    if not f.exists(): raise HTTPException(status_code=404, detail="Not found")
    try:
        f.unlink()
        await logger.emit("Info", f"Deleted model: {name}", "ModelManager")
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
