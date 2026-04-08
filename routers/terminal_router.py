import json
import asyncio
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import core.state as state
from services.terminal import get_or_create_terminal_session, maybe_cleanup_terminal_session

router = APIRouter(tags=["terminal"])

@router.websocket("/api/terminal/{sid}")
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
