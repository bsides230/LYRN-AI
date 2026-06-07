from fastapi import APIRouter, Depends
from core.security import verify_token
import os
import json
from pydantic import BaseModel

router = APIRouter(prefix="/api/indexes", tags=["indexes"])

INDEXES_DIR = "runtime/indexes"
SETTINGS_FILE = os.path.join(INDEXES_DIR, "settings.json")

class IndexSettings(BaseModel):
    default_recall_limit: int

@router.get("/settings", dependencies=[Depends(verify_token)])
async def get_index_settings():
    """Gets the settings for the index system."""
    if not os.path.exists(SETTINGS_FILE):
        return {"default_recall_limit": 5}
    with open(SETTINGS_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"default_recall_limit": 5}

@router.put("/settings", dependencies=[Depends(verify_token)])
async def update_index_settings(settings: IndexSettings):
    """Updates the settings for the index system."""
    os.makedirs(INDEXES_DIR, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings.model_dump(), f, indent=4)
    return {"success": True, "message": "Index settings updated."}
