import os
import subprocess
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.auth import verify_token
from backend.utils import check_path_access
from backend.shortcuts_manager import shortcuts_manager, Shortcut, build_command, build_command_list

router = APIRouter()

class ShortcutRunRequest(BaseModel):
    run_mode: Optional[str] = None

@router.get("/")
async def list_shortcuts(token: str = Depends(verify_token)):
    return shortcuts_manager.list()

@router.post("/")
async def add_shortcut(s: Shortcut, token: str = Depends(verify_token)):
    try:
        check_path_access(s.path)
        if s.cwd: check_path_access(s.cwd)
    except Exception as e:
        raise HTTPException(status_code=403, detail=f"Access Denied: {str(e)}")
    return shortcuts_manager.add(s)

@router.put("/{sid}")
async def update_shortcut(sid: str, s: Shortcut, token: str = Depends(verify_token)):
    try:
        check_path_access(s.path)
        if s.cwd: check_path_access(s.cwd)
    except Exception as e:
        raise HTTPException(status_code=403, detail=f"Access Denied: {str(e)}")
    data = s.dict()
    data['id'] = sid
    updated = shortcuts_manager.update(sid, data)
    if not updated: raise HTTPException(status_code=404, detail="Shortcut not found")
    return updated

@router.delete("/{sid}")
async def delete_shortcut(sid: str, token: str = Depends(verify_token)):
    shortcuts_manager.delete(sid)
    return {"success": True}

@router.post("/{sid}/run")
async def run_shortcut_endpoint(sid: str, req: ShortcutRunRequest, token: str = Depends(verify_token)):
    s = shortcuts_manager.get(sid)
    if not s: raise HTTPException(status_code=404, detail="Shortcut not found")

    check_path_access(s.path)
    if s.cwd: check_path_access(s.cwd)

    run_mode = req.run_mode or s.run_mode

    if run_mode == "terminal":
        return {"action": "terminal", "cwd": s.cwd, "command": build_command(s)}

    # Output Mode
    cmd_list = build_command_list(s)
    cwd = s.cwd if s.cwd else os.path.dirname(s.path)
    if not cwd: cwd = None

    try:
        proc = subprocess.run(cmd_list, cwd=cwd, capture_output=True, text=True, timeout=30)
        stdout = proc.stdout[:200000]
        stderr = proc.stderr[:200000]
        return {"action": "output", "exit_code": proc.returncode, "stdout": stdout, "stderr": stderr}
    except subprocess.TimeoutExpired:
        return {"action": "output", "exit_code": -1, "stdout": "", "stderr": "Execution Timeout (30s)"}
    except Exception as e:
        return {"action": "output", "exit_code": -1, "stdout": "", "stderr": f"Error: {str(e)}"}
