import subprocess
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

try:
    from crontab import CronTab
except ImportError:
    CronTab = None

from backend.auth import verify_token
from backend.automation_controller import automation_controller

router = APIRouter()

# --- Models ---
class JobDefinitionModel(BaseModel):
    name: str
    instructions: str
    trigger: str
    scripts: List[str] = []

class JobScheduleModel(BaseModel):
    id: Optional[str] = None
    job_name: str
    scheduled_datetime_iso: str
    priority: int = 100
    args: Optional[Dict[str, Any]] = None

class CycleModel(BaseModel):
    name: str
    triggers: List[Any]

class CronRequest(BaseModel):
    lines: str

# --- Routes ---

@router.get("/jobs")
async def get_jobs(token: str = Depends(verify_token)):
    return automation_controller.job_definitions

@router.post("/jobs")
async def save_job(job: JobDefinitionModel, token: str = Depends(verify_token)):
    automation_controller.save_job_definition(job.name, job.instructions, job.trigger, job.scripts)
    return {"success": True}

@router.delete("/jobs/{job_name}")
async def delete_job(job_name: str, token: str = Depends(verify_token)):
    automation_controller.delete_job_definition(job_name)
    return {"success": True}

@router.get("/scripts")
async def get_scripts(token: str = Depends(verify_token)):
    return automation_controller.get_available_scripts()

@router.get("/history")
async def get_job_history(token: str = Depends(verify_token)):
    return automation_controller.get_job_history()

@router.delete("/history")
async def clear_job_history(token: str = Depends(verify_token)):
    automation_controller.clear_job_history()
    return {"success": True}

@router.get("/schedule")
async def get_schedule(token: str = Depends(verify_token)):
    return automation_controller.get_queue()

@router.post("/schedule")
async def add_schedule(item: JobScheduleModel, token: str = Depends(verify_token)):
    automation_controller.add_job(
        name=item.job_name,
        priority=item.priority,
        when=item.scheduled_datetime_iso,
        args=item.args,
        job_id=item.id
    )
    return {"success": True}

@router.delete("/schedule/{job_id}")
async def delete_schedule(job_id: str, token: str = Depends(verify_token)):
    automation_controller.remove_job_from_queue(job_id)
    return {"success": True}

@router.get("/cycles")
async def get_cycles(token: str = Depends(verify_token)):
    return automation_controller.get_cycles()

@router.post("/cycles")
async def save_cycle(cycle: CycleModel, token: str = Depends(verify_token)):
    automation_controller.save_cycle(cycle.name, cycle.triggers)
    return {"success": True}

@router.delete("/cycles/{cycle_name}")
async def delete_cycle(cycle_name: str, token: str = Depends(verify_token)):
    automation_controller.delete_cycle(cycle_name)
    return {"success": True}

# --- Cron ---
@router.get("/cron")
async def get_cron(token: str = Depends(verify_token)):
    if not CronTab:
        raise HTTPException(status_code=501, detail="python-crontab not installed")
    try:
        cron = CronTab(user=True)
        return {"lines": cron.render()}
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

@router.post("/cron")
async def save_cron(req: CronRequest, token: str = Depends(verify_token)):
    try:
        proc = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate(input=req.lines.encode('utf-8'))
        if proc.returncode != 0: raise Exception(stderr.decode())
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
