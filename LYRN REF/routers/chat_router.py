import os
import re
import json
import asyncio
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from core.security import verify_token
from core.registry import chat_manager, settings_manager
from models.schemas import ChatRequest
from utils.helpers import trigger_chat_generation
from services.worker import worker_controller

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.get("/history", dependencies=[Depends(verify_token)])
async def get_chat_history():
    """Returns the current chat history as a list of messages."""
    return chat_manager.get_chat_history_messages()

@router.delete("", dependencies=[Depends(verify_token)])
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

@router.delete("/{filename}", dependencies=[Depends(verify_token)])
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

@router.post("/stop", dependencies=[Depends(verify_token)])
async def stop_chat_generation():
    """Triggers the worker to stop the current generation."""
    try:
        with open("stop_trigger.txt", "w", encoding="utf-8") as f:
            f.write("stop")
        print("[API] Wrote stop_trigger.txt")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop generation: {e}")

@router.post("", dependencies=[Depends(verify_token)])
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
