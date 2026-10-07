from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from core.security import verify_token
from services.logger import logger

router = APIRouter(prefix="/api/logs", tags=["logs"])

@router.get("", dependencies=[Depends(verify_token)])
async def stream_logs(request: Request):
    return StreamingResponse(logger.subscribe(request), media_type="text/event-stream")

@router.get("/sessions", dependencies=[Depends(verify_token)])
async def list_log_sessions():
    return logger.list_sessions()

@router.get("/sessions/{session_id}/chunks", dependencies=[Depends(verify_token)])
async def list_log_chunks(session_id: str):
    return logger.list_chunks(session_id)

@router.get("/sessions/{session_id}/chunks/{chunk_id}", dependencies=[Depends(verify_token)])
async def get_log_chunk(session_id: str, chunk_id: str):
    return logger.get_chunk_content(session_id, chunk_id)
