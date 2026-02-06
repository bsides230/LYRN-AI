from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from backend.auth import verify_token
from backend.logger import logger

router = APIRouter()

@router.get("/")
async def stream_logs(request: Request, token: str = Depends(verify_token)):
    # Compatible with both SSE and simple stream
    return StreamingResponse(logger.subscribe(request), media_type="text/event-stream")

@router.get("/sessions")
async def list_log_sessions(token: str = Depends(verify_token)):
    return logger.list_sessions()

@router.get("/sessions/{session_id}/chunks")
async def list_log_chunks(session_id: str, token: str = Depends(verify_token)):
    return logger.list_chunks(session_id)

@router.get("/sessions/{session_id}/chunks/{chunk_id}")
async def get_log_chunk(session_id: str, chunk_id: str, token: str = Depends(verify_token)):
    return logger.get_chunk_content(session_id, chunk_id)
