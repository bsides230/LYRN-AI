import os
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI

import core.state as state
from services.logger import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    state.main_loop = asyncio.get_running_loop()

    # Load Admin Token
    token_file = Path("admin_token.txt")
    if token_file.exists():
        try:
            state.LYRN_TOKEN = token_file.read_text(encoding="utf-8").strip()
            print("[System] Loaded admin token from admin_token.txt")
        except Exception as e:
            print(f"[System] Failed to read admin_token.txt: {e}")

    # Fallback to env var
    if not state.LYRN_TOKEN:
        state.LYRN_TOKEN = os.environ.get("LYRN_MODEL_TOKEN")
        if state.LYRN_TOKEN:
            print("[System] Loaded admin token from Environment Variable")
        else:
            print("[System] Warning: No admin token found (admin_token.txt or LYRN_MODEL_TOKEN). Model management will be unavailable.")

    await logger.emit("Info", "Backend started.", "System")

    yield
