from typing import List, Dict, Any, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Body

from core.security import verify_token
from services import delta_service
from models.schemas import DeltaUpdateRequest

router = APIRouter(prefix="/api/deltas", tags=["deltas"])

@router.get("/blocks", dependencies=[Depends(verify_token)])
async def get_delta_blocks():
    """
    Returns registered delta blocks sorted by order, including enabled status,
    delimiter brackets, description, and live content.
    """
    try:
        blocks = delta_service.get_delta_blocks()
        return blocks
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch delta blocks: {str(e)}")

@router.post("/order", dependencies=[Depends(verify_token)])
async def save_delta_order(payload: Union[List[Dict[str, Any]], Dict[str, Any]] = Body(...)):
    """
    Saves reordered blocks and enabled/disabled states to delta_config.json.
    Accepts either an array of block objects or an object containing a 'blocks' array.
    """
    try:
        if isinstance(payload, dict):
            order_data = payload.get("blocks", [])
        else:
            order_data = payload

        if not isinstance(order_data, list):
            raise HTTPException(status_code=400, detail="Invalid order payload format. Expected list of blocks.")

        updated_blocks = delta_service.save_delta_order(order_data)
        return {"success": True, "blocks": updated_blocks}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save delta order: {str(e)}")

@router.post("/compile", dependencies=[Depends(verify_token)])
async def compile_manifest():
    """
    Triggers compilation of deltas/compiled_manifest.txt based on active blocks.
    """
    try:
        manifest_text = delta_service.compile_manifest()
        return {
            "success": True,
            "manifest_size": len(manifest_text),
            "manifest_path": "deltas/compiled_manifest.txt",
            "content": manifest_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compile delta manifest: {str(e)}")

@router.post("/update", dependencies=[Depends(verify_token)])
async def update_delta_content(req: DeltaUpdateRequest):
    """
    Generic hook endpoint for external jobs to programmatically update a delta
    source file and optionally trigger manifest recompilation.
    """
    target = req.block_id or req.file
    if not target:
        raise HTTPException(status_code=400, detail="Must provide either 'block_id' or 'file'.")

    try:
        result = delta_service.update_delta_source(
            block_id_or_file=target,
            content=req.content,
            recompile=req.recompile if req.recompile is not None else True
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update delta source: {str(e)}")

@router.get("/manifest", dependencies=[Depends(verify_token)])
async def get_compiled_manifest():
    """
    Returns the current compiled delta manifest text directly.
    """
    try:
        content = delta_service.get_compiled_manifest()
        return {
            "exists": bool(content),
            "size": len(content),
            "content": content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load compiled manifest: {str(e)}")
