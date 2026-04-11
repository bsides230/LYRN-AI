import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn

from core.registry import settings_manager
from core.lifecycle import lifespan

# --- App Setup ---

app = FastAPI(title="LYRN v6 Backend", lifespan=lifespan)

# Determine allowed origins
allowed_origins = settings_manager.settings.get("allowed_origins", [])
current_port = 8000
try:
    if os.path.exists("port.txt"):
        with open("port.txt", "r") as f:
            val = f.read().strip()
            if val.isdigit():
                current_port = int(val)
except: pass

defaults = [
    f"http://localhost:{current_port}",
    f"http://127.0.0.1:{current_port}"
]
# Ensure defaults are present
for d in defaults:
    if d not in allowed_origins:
        allowed_origins.append(d)

print(f"[System] Allowed Origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["X-Token", "Content-Type", "Authorization"],
)

# --- Routes ---

from routers.logs_router import router as logs_router
from routers.chat_router import router as chat_router
from routers.models_router import router as models_router
from routers.config_router import router as config_router
from routers.system_router import router as system_router
from routers.claude_router import router as claude_router
from routers.fs_router import router as fs_router
from routers.snapshot_router import router as snapshot_router
from routers.terminal_router import router as terminal_router

app.include_router(logs_router)
app.include_router(chat_router)
app.include_router(models_router)
app.include_router(config_router)
app.include_router(system_router)
app.include_router(claude_router)
app.include_router(fs_router)
app.include_router(snapshot_router)
app.include_router(terminal_router)

# Serve dashboard at root

@app.get("/")
async def read_root():
    return FileResponse('LYRN_v6/dashboard.html')

# Serve Static Files
app.mount("/", StaticFiles(directory="LYRN_v6", html=True), name="static")

if __name__ == "__main__":
    port = 8000
    try:
        if os.path.exists("port.txt"):
            with open("port.txt", "r") as f:
                val = f.read().strip()
                if val.isdigit():
                    port = int(val)
    except Exception as e:
        print(f"Failed to load port.txt: {e}")

    print(f"Starting server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
