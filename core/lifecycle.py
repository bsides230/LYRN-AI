import os
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI

from core.registry import automation_controller
from utils.helpers import trigger_chat_generation

import core.state as state
from services.logger import logger

# --- Scheduler Loop ---
async def scheduler_loop():
    print("[Scheduler] Starting scheduler loop...")
    while True:
        try:
            # Check for due jobs
            job = automation_controller.get_next_due_job()
            if job:
                print(f"[Scheduler] Executing job: {job.name}")

                # 1. Execute Scripts if any
                scripts_ok = True
                if job.scripts:
                    print(f"[Scheduler] Running scripts for job: {job.name}")
                    # Run in executor to avoid blocking the event loop
                    result = await state.main_loop.run_in_executor(None, automation_controller.execute_job_scripts, job)
                    if result["status"] != "success":
                        print(f"[Scheduler] Scripts failed for job {job.name}. Aborting chat generation.")
                        scripts_ok = False

                # 2. Trigger Chat if scripts ok (or no scripts) AND prompt exists
                if scripts_ok:
                    if job.prompt:
                        # Use "jobs" folder for automated tasks
                        filepath, _ = trigger_chat_generation(job.prompt, folder="jobs")

                        # Log the prompt generation step
                        automation_controller.log_job_history(
                            job.name,
                            [{"message": "Prompt triggered successfully."}],
                            "success",
                            filepath=filepath
                        )
                    elif not job.scripts:
                        # Only log this if there were no scripts either
                        print(f"[Scheduler] Job {job.name} has no prompt/instructions and no scripts.")

            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"[Scheduler] Error in loop: {e}")
            await asyncio.sleep(0.5)

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

    # Start Scheduler
    asyncio.create_task(scheduler_loop())

    yield
