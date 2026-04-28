from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any

from core.security import verify_token
from models.schemas import DeltaDataModel
from services import delta_registry

router = APIRouter(prefix="/api/deltas", tags=["deltas"])

@router.get("/", dependencies=[Depends(verify_token)])
@router.get("", dependencies=[Depends(verify_token)])
async def get_all_deltas():
    deltas = delta_registry.get_deltas()
    return {"deltas": deltas}

@router.get("/{delta_id}", dependencies=[Depends(verify_token)])
async def get_delta(delta_id: str):
    delta = delta_registry.get_delta_by_id(delta_id)
    if not delta:
        raise HTTPException(status_code=404, detail="Delta not found")
    return {"delta": delta}

@router.post("", dependencies=[Depends(verify_token)])
@router.post("/", dependencies=[Depends(verify_token)])
async def create_delta(data: DeltaDataModel):
    saved_delta = delta_registry.save_delta(data.model_dump())
    return {"success": True, "delta": saved_delta}

@router.put("/{delta_id}", dependencies=[Depends(verify_token)])
async def update_delta(delta_id: str, data: DeltaDataModel):
    delta_data = data.model_dump()
    delta_data["delta_id"] = delta_id
    saved_delta = delta_registry.save_delta(delta_data)
    return {"success": True, "delta": saved_delta}

@router.delete("/{delta_id}", dependencies=[Depends(verify_token)])
async def delete_delta(delta_id: str):
    success = delta_registry.delete_delta(delta_id)
    if not success:
        raise HTTPException(status_code=404, detail="Delta not found")
    return {"success": True}
