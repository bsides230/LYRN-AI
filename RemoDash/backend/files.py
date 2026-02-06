import os
import shutil
import zipfile
import tempfile
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.auth import verify_token
from backend.utils import check_path_access

router = APIRouter()

class FileOpRequest(BaseModel):
    path: str
    content: Optional[str] = None
    new_path: Optional[str] = None

class FilesListRequest(BaseModel):
    paths: List[str]

@router.get("/list")
async def list_files(path: str, sort_by: str = "name", order: str = "asc", token: str = Depends(verify_token)):
    """Lists files in the given directory with sorting."""
    target_path = check_path_access(path)

    if not target_path.is_dir():
         raise HTTPException(status_code=400, detail="Path is not a directory")

    items = []
    try:
        with os.scandir(target_path) as it:
            for entry in it:
                try:
                    stat = entry.stat()
                    item_type = "dir" if entry.is_dir() else "file"
                    items.append({
                        "name": entry.name,
                        "path": entry.path,
                        "type": item_type,
                        "size": stat.st_size,
                        "mtime": stat.st_mtime
                    })
                except OSError:
                    continue
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission Denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Sort
    reverse = (order == "desc")

    # Sort helper
    def sort_key(x):
        is_file = 1 if x["type"] == "file" else 0
        val = x["name"].lower()
        if sort_by == "size": val = x["size"]
        elif sort_by == "date": val = x["mtime"]
        elif sort_by == "type": val = (x["type"], x["name"].lower())
        return (is_file, val)

    items.sort(key=sort_key, reverse=reverse)

    # Fix Dirs First if reversed
    if reverse:
        if sort_by == "name": items.sort(key=lambda x: x["name"].lower(), reverse=True)
        elif sort_by == "size": items.sort(key=lambda x: x["size"], reverse=True)
        elif sort_by == "date": items.sort(key=lambda x: x["mtime"], reverse=True)
        elif sort_by == "type": items.sort(key=lambda x: (x["type"], x["name"].lower()), reverse=True)
        # Stable sort type
        items.sort(key=lambda x: 0 if x["type"] == "dir" else 1)
    else:
        if sort_by == "name": items.sort(key=lambda x: x["name"].lower())
        elif sort_by == "size": items.sort(key=lambda x: x["size"])
        elif sort_by == "date": items.sort(key=lambda x: x["mtime"])
        elif sort_by == "type": items.sort(key=lambda x: (x["type"], x["name"].lower()))
        # Stable sort type
        items.sort(key=lambda x: 0 if x["type"] == "dir" else 1)

    return {"path": str(target_path), "items": items}

@router.get("/content")
async def get_file_content(path: str, token: str = Depends(verify_token)):
    p = check_path_access(path)
    if not p.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
             content = f.read()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/view")
async def view_file(path: str, token: str = Depends(verify_token)):
    p = check_path_access(path)
    if not p.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(p)

@router.post("/save")
async def save_file_content(data: FileOpRequest, token: str = Depends(verify_token)):
    p = check_path_access(data.path)
    try:
        with open(p, "w", encoding="utf-8") as f:
            f.write(data.content if data.content else "")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create_folder")
async def create_folder(data: FileOpRequest, token: str = Depends(verify_token)):
    p = check_path_access(data.path)
    try:
        p.mkdir(parents=True, exist_ok=True)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/delete")
async def delete_item(data: FileOpRequest, token: str = Depends(verify_token)):
    p = check_path_access(data.path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Path not found")
    try:
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rename")
async def rename_item(data: FileOpRequest, token: str = Depends(verify_token)):
    if not data.new_path:
        raise HTTPException(status_code=400, detail="new_path required")
    src = check_path_access(data.path)
    dst_input = data.new_path

    try:
        from pathlib import Path
        dst = Path(dst_input)
        if not dst.is_absolute() and len(dst.parts) == 1:
             dst = src.parent / dst_input

        check_path_access(str(dst)) # Validate dst
        src.rename(dst)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_files(path: str = Form(...), files: List[UploadFile] = File(...), token: str = Depends(verify_token)):
    target_dir = check_path_access(path)
    if not target_dir.is_dir():
         raise HTTPException(status_code=400, detail="Target path is not a directory")

    results = []
    try:
        for file in files:
            safe_name = os.path.basename(file.filename)
            file_path = target_dir / safe_name
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            results.append(file.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"success": True, "uploaded": results}

@router.post("/zip")
async def download_zip(req: FilesListRequest, background_tasks: BackgroundTasks, token: str = Depends(verify_token)):
    if not req.paths:
        raise HTTPException(status_code=400, detail="No paths provided")

    valid_paths = []
    for p in req.paths:
        try:
            valid_paths.append(check_path_access(p))
        except HTTPException:
            continue

    if not valid_paths:
        raise HTTPException(status_code=400, detail="No valid paths found")

    try:
        fd, temp_path = tempfile.mkstemp(suffix=".zip")
        os.close(fd)

        with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in valid_paths:
                if p.is_file():
                    zf.write(p, arcname=p.name)
                elif p.is_dir():
                    parent_len = len(str(p.parent))
                    for root, dirs, files in os.walk(p):
                        for file in files:
                            abs_path = os.path.join(root, file)
                            rel_path = abs_path[parent_len:].strip(os.sep)
                            zf.write(abs_path, arcname=rel_path)

        background_tasks.add_task(os.unlink, temp_path)
        return FileResponse(temp_path, filename="archive.zip", media_type="application/zip")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
