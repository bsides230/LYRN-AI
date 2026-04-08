from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from core.security import verify_token
from core.registry import automation_controller
from models.schemas import JobDefinitionModel, JobScheduleModel, CycleModel

router = APIRouter(prefix="/api/automation", tags=["automation"])

@router.get("/jobs", dependencies=[Depends(verify_token)])
async def get_jobs():
    return automation_controller.job_definitions

@router.post("/jobs", dependencies=[Depends(verify_token)])
async def save_job(job: JobDefinitionModel):
    automation_controller.save_job_definition(job.name, job.instructions, job.trigger, job.scripts)
    return {"success": True}

@router.delete("/jobs/{job_name}", dependencies=[Depends(verify_token)])
async def delete_job(job_name: str):
    automation_controller.delete_job_definition(job_name)
    return {"success": True}

@router.get("/scripts", dependencies=[Depends(verify_token)])
async def get_scripts():
    return automation_controller.get_available_scripts()

@router.get("/history", dependencies=[Depends(verify_token)])
async def get_job_history():
    return automation_controller.get_job_history()

@router.get("/job_content", dependencies=[Depends(verify_token)])
async def get_job_content(path: str):
    """Reads the content of a job file."""
    try:
        # Security check: Ensure path is within jobs/ folder
        requested_path = Path(path).resolve()
        jobs_dir = Path("jobs").resolve()

        if not str(requested_path).startswith(str(jobs_dir)):
            raise HTTPException(status_code=403, detail="Access denied: Invalid file path.")

        if not requested_path.exists():
            raise HTTPException(status_code=404, detail="File not found.")

        return {"content": requested_path.read_text(encoding="utf-8")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/history", dependencies=[Depends(verify_token)])
async def clear_job_history():
    automation_controller.clear_job_history()
    return {"success": True}

@router.get("/schedule", dependencies=[Depends(verify_token)])
async def get_schedule():
    return automation_controller.get_queue()

@router.post("/schedule", dependencies=[Depends(verify_token)])
async def add_schedule(item: JobScheduleModel):
    automation_controller.add_job(
        name=item.job_name,
        priority=item.priority,
        when=item.scheduled_datetime_iso,
        args=item.args,
        job_id=item.id
    )
    return {"success": True}

@router.delete("/schedule/{job_id}", dependencies=[Depends(verify_token)])
async def delete_schedule(job_id: str):
    automation_controller.remove_job_from_queue(job_id)
    return {"success": True}

@router.get("/cycles", dependencies=[Depends(verify_token)])
async def get_cycles():
    return automation_controller.get_cycles()

@router.post("/cycles", dependencies=[Depends(verify_token)])
async def save_cycle(cycle: CycleModel):
    automation_controller.save_cycle(cycle.name, cycle.triggers)
    return {"success": True}

@router.delete("/cycles/{cycle_name}", dependencies=[Depends(verify_token)])
async def delete_cycle(cycle_name: str):
    automation_controller.delete_cycle(cycle_name)
    return {"success": True}
