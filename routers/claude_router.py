from pathlib import Path
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import FileResponse
from core.security import verify_token
from services.claude import claude_run_manager

router = APIRouter(prefix="/api/claude", tags=["claude"])

@router.get("/auth", dependencies=[Depends(verify_token)])
async def claude_auth():
    return claude_run_manager.auth_status()

@router.post("/validate_cwd", dependencies=[Depends(verify_token)])
async def claude_validate_cwd(req: Request):
    try:
        body = await req.json()
    except Exception:
        body = {}
    return claude_run_manager.resolve_cwd((body or {}).get("cwd"))

@router.post("/preview", dependencies=[Depends(verify_token)])
async def claude_preview(req: Request):
    try:
        body = await req.json()
    except Exception:
        body = {}
    return claude_run_manager.preview(body or {})

@router.get("/runs", dependencies=[Depends(verify_token)])
async def claude_list_runs():
    return {"runs": claude_run_manager.list_runs()}

@router.post("/runs", dependencies=[Depends(verify_token)])
async def claude_start_run(req: Request):
    try:
        body = await req.json()
    except Exception:
        body = {}
    return claude_run_manager.start_run(body or {})

@router.get("/runs/{run_id}", dependencies=[Depends(verify_token)])
async def claude_get_run(run_id: str):
    run = claude_run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return run

@router.get("/runs/{run_id}/transcript", dependencies=[Depends(verify_token)])
async def claude_get_transcript(run_id: str):
    run = claude_run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    text = claude_run_manager.get_transcript(run_id)
    return {"run_id": run_id, "transcript": text}

@router.get("/runs/{run_id}/transcript/download", dependencies=[Depends(verify_token)])
async def claude_download_transcript(run_id: str):
    run = claude_run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    path = run.get("transcript_path", "")
    if not path or not Path(path).exists():
        raise HTTPException(status_code=404, detail="transcript file missing")
    return FileResponse(path, filename=f"{run_id}.log", media_type="text/plain")

@router.get("/runs/{run_id}/diff", dependencies=[Depends(verify_token)])
async def claude_get_diff(run_id: str):
    run = claude_run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return claude_run_manager.get_diff(run_id)

@router.post("/runs/{run_id}/approve", dependencies=[Depends(verify_token)])
async def claude_approve(run_id: str):
    return claude_run_manager.approve(run_id)

@router.post("/runs/{run_id}/reject", dependencies=[Depends(verify_token)])
async def claude_reject(run_id: str):
    return claude_run_manager.reject(run_id)

@router.delete("/runs/{run_id}", dependencies=[Depends(verify_token)])
async def claude_delete_run(run_id: str):
    return claude_run_manager.delete_run(run_id)
