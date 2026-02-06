import os
import json
import re
import datetime
import asyncio
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.auth import verify_token
from backend.config import settings_manager
from backend.chat_manager import ChatManager
from backend.worker_controller import worker_controller

router = APIRouter()

# Initialize ChatManager
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

class ChatRequest(BaseModel):
    message: str

def trigger_chat_generation(message: str, folder: str = "chat"):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{folder}/{folder}_{timestamp}.txt"
    # Ensure dir exists (relative to CWD)
    Path(folder).mkdir(parents=True, exist_ok=True)

    filepath = os.path.abspath(filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"#USER_START#\n{message}\n#USER_END#")

    with open("chat_trigger.txt", "w", encoding="utf-8") as f:
        f.write(filepath)

    return filepath, os.path.basename(filepath)

@router.get("/history")
async def get_chat_history(token: str = Depends(verify_token)):
    return chat_manager.get_chat_history_messages()

@router.delete("/")
async def clear_chat_history(token: str = Depends(verify_token)):
    try:
        chat_dir = Path(settings_manager.settings.get("paths", {}).get("chat", "chat/"))
        if chat_dir.exists():
            for f in chat_dir.glob("*.txt"):
                try: f.unlink()
                except: pass
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{filename}")
async def delete_chat_file(filename: str, token: str = Depends(verify_token)):
    try:
        chat_dir = Path(settings_manager.settings.get("paths", {}).get("chat", "chat/"))
        file_path = chat_dir / os.path.basename(filename)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        file_path.unlink()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop")
async def stop_chat_generation(token: str = Depends(verify_token)):
    try:
        with open("stop_trigger.txt", "w", encoding="utf-8") as f:
            f.write("stop")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def chat_endpoint(request: ChatRequest, token: str = Depends(verify_token)):
    try:
        filepath, filename = trigger_chat_generation(request.message)
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Failed to trigger chat: {e}")

    async def event_generator():
        yield json.dumps({"filename": filename}) + "\n"
        last_pos = 0
        retries = 0
        started = False

        while True:
            await asyncio.sleep(0.1)
            try:
                if not os.path.exists(filepath): continue

                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                    if not started:
                        match = re.search(r'(?:^|\n)model\n', content)
                        if match:
                            last_pos = match.end()
                            started = True

                        if not started:
                            if "[Error:" in content:
                                yield json.dumps({"response": "Error in worker."}) + "\n"
                                return

                            retries += 1
                            # 30s timeout default if setting missing
                            timeout = settings_manager.settings.get("worker_timeout_seconds", 30)
                            if retries > timeout * 10:
                                yield json.dumps({"response": "Timeout waiting for worker."}) + "\n"
                                return
                            continue

                    if started:
                        if len(content) > last_pos:
                            new_text = content[last_pos:]
                            yield json.dumps({"response": new_text}) + "\n"
                            last_pos = len(content)

                        # Check completion
                        status = worker_controller.get_status()
                        if status.get("llm_status") in ["idle", "error", "stopped"]:
                            # One last read to be sure? We just read it.
                            return
            except Exception as e:
                yield json.dumps({"response": f"Error: {e}"}) + "\n"
                return

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")
