import os
import subprocess
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from core.security import verify_token
from services import job_registry

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

class JobData(BaseModel):
    job_id: Optional[str] = None
    job_name: str
    trigger_name: str
    instruction_layer: str
    enabled: bool = True
    notes: Optional[str] = ""

class CategoryData(BaseModel):
    category: str

class InjectRequest(BaseModel):
    category: str
    job_name: str

@router.get("/categories", dependencies=[Depends(verify_token)])
async def get_categories():
    categories = job_registry.get_categories()
    return {"categories": categories}

@router.post("/categories", dependencies=[Depends(verify_token)])
async def create_category(data: CategoryData):
    success = job_registry.create_category(data.category)
    if not success:
        raise HTTPException(status_code=400, detail="Category already exists or invalid.")
    return {"success": True, "category": data.category}

@router.get("/{category}", dependencies=[Depends(verify_token)])
async def get_jobs(category: str):
    jobs = job_registry.get_jobs(category)
    return {"jobs": jobs}

@router.post("/{category}", dependencies=[Depends(verify_token)])
async def create_job(category: str, job: JobData):
    saved_job = job_registry.save_job(category, job.model_dump())
    return {"success": True, "job": saved_job}

@router.put("/{category}/{job_id}", dependencies=[Depends(verify_token)])
async def update_job(category: str, job_id: str, job: JobData):
    job_data = job.model_dump()
    job_data["job_id"] = job_id
    saved_job = job_registry.save_job(category, job_data)
    return {"success": True, "job": saved_job}

@router.post("/inject/run", dependencies=[Depends(verify_token)])
async def inject_job(req: InjectRequest):
    """Optional wrapper to run inject script from API."""
    script_path = os.path.join("scripts", "inject_job.py")
    if not os.path.exists(script_path):
        raise HTTPException(status_code=500, detail="Injection script not found.")

    try:
        result = subprocess.run(
            ["python", script_path, "--category", req.category, "--job-name", req.job_name],
            capture_output=True, text=True
        )
        if result.returncode != 0:
             raise HTTPException(status_code=500, detail=f"Injection failed: {result.stderr}")
        return {"success": True, "output": result.stdout}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
