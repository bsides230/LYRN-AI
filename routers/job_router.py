import os
import subprocess
import datetime
from pathlib import Path
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
    affordances: Optional[str] = ""
    scripts: Optional[str] = ""
    max_retries: Optional[int] = 1
    retry_error_message: Optional[str] = ""
    enabled: bool = True
    notes: Optional[str] = ""

class CategoryData(BaseModel):
    category: str

class RenameCategoryData(BaseModel):
    new_category: str

class InjectRequest(BaseModel):
    category: str
    job_name: str

class TriggerTextData(BaseModel):
    trigger_text: str

class CsvContentData(BaseModel):
    csv_content: str

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

@router.put("/categories/{category}", dependencies=[Depends(verify_token)])
async def rename_category(category: str, data: RenameCategoryData):
    success = job_registry.rename_category(category, data.new_category)
    if not success:
        raise HTTPException(status_code=400, detail="Category not found or new category already exists.")
    return {"success": True, "category": data.new_category}

@router.delete("/categories/{category}", dependencies=[Depends(verify_token)])
async def delete_category(category: str):
    success = job_registry.delete_category(category)
    if not success:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"success": True}

@router.get("/config/trigger", dependencies=[Depends(verify_token)])
async def get_trigger_text():
    trigger_file = os.path.join("runtime", "jobs", "trigger.txt")
    if os.path.exists(trigger_file):
        with open(trigger_file, "r", encoding="utf-8") as f:
            return {"trigger_text": f.read().strip()}
    return {"trigger_text": "##JOB_START##"}

@router.post("/config/trigger", dependencies=[Depends(verify_token)])
async def set_trigger_text(data: TriggerTextData):
    os.makedirs(os.path.join("runtime", "jobs"), exist_ok=True)
    trigger_file = os.path.join("runtime", "jobs", "trigger.txt")
    with open(trigger_file, "w", encoding="utf-8") as f:
        f.write(data.trigger_text)
    return {"success": True}

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

@router.delete("/{category}/{job_id}", dependencies=[Depends(verify_token)])
async def delete_job(category: str, job_id: str):
    success = job_registry.delete_job(category, job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"success": True}

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

@router.get("/categories/{category}/csv", dependencies=[Depends(verify_token)])
async def get_category_csv(category: str):
    cat_path = job_registry._get_category_path(category)
    if not cat_path.exists():
        raise HTTPException(status_code=404, detail="Category CSV not found")
    try:
        with open(cat_path, "r", encoding="utf-8") as f:
            return {"category": category, "csv_content": f.read()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/categories/{category}/csv", dependencies=[Depends(verify_token)])
async def save_category_csv(category: str, data: CsvContentData):
    cat_path = job_registry._get_category_path(category)
    cat_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(cat_path, "w", encoding="utf-8") as f:
            f.write(data.csv_content)
        jobs = job_registry.get_jobs(category)
        return {"success": True, "category": category, "count": len(jobs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/outputs/list", dependencies=[Depends(verify_token)])
async def list_job_outputs():
    out_dir = Path("job_output")
    if not out_dir.exists():
        return {"outputs": []}
    files = []
    for p in out_dir.glob("*.txt"):
        try:
            stat = p.stat()
            files.append({
                "filename": p.name,
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        except Exception:
            pass
    files.sort(key=lambda x: x["mtime"], reverse=True)
    return {"outputs": files[:50]}

@router.get("/outputs/file/{filename}", dependencies=[Depends(verify_token)])
async def get_job_output(filename: str):
    safe_name = os.path.basename(filename)
    file_path = Path("job_output") / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Output file not found")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return {"filename": safe_name, "content": f.read()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

