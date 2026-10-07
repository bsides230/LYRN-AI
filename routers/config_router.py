from typing import Dict, Any
from fastapi import APIRouter, Depends
from core.security import verify_token
from core.registry import settings_manager
from models.schemas import PresetModel, ActiveConfigModel

router = APIRouter(prefix="/api/config", tags=["config"])

@router.get("/presets", dependencies=[Depends(verify_token)])
async def get_presets():
    """Gets all model presets."""
    if not settings_manager.settings:
        settings_manager.load_or_detect_first_boot()

    return settings_manager.settings.get("model_presets", {})

@router.post("/presets", dependencies=[Depends(verify_token)])
async def save_preset(preset: PresetModel):
    """Saves a model preset."""
    if not settings_manager.settings:
        settings_manager.load_or_detect_first_boot()

    if "model_presets" not in settings_manager.settings:
        settings_manager.settings["model_presets"] = {}

    settings_manager.settings["model_presets"][preset.preset_id] = preset.config
    settings_manager.save_settings()
    return {"success": True, "message": f"Preset {preset.preset_id} saved."}

@router.post("/active", dependencies=[Depends(verify_token)])
async def set_active_config(config: ActiveConfigModel):
    """Sets the active model configuration."""
    if not settings_manager.settings:
        settings_manager.load_or_detect_first_boot()

    settings_manager.settings["active"] = config.config
    settings_manager.save_settings()
    return {"success": True, "message": "Active configuration updated."}

@router.get("/active", dependencies=[Depends(verify_token)])
async def get_active_config():
    """Gets the active model configuration."""
    if not settings_manager.settings:
        settings_manager.load_or_detect_first_boot()

    return settings_manager.settings.get("active", {})

@router.get("", dependencies=[Depends(verify_token)])
async def get_config():
    """Gets the full system configuration."""
    if not settings_manager.settings:
        settings_manager.load_or_detect_first_boot()
    return {
        "settings": settings_manager.settings,
        "ui_settings": settings_manager.ui_settings
    }

@router.post("", dependencies=[Depends(verify_token)])
async def save_config(data: Dict[str, Any]):
    """Saves the full system configuration."""
    if "settings" in data:
        settings_manager.settings = data["settings"]
    if "ui_settings" in data:
        settings_manager.ui_settings = data["ui_settings"]

    settings_manager.save_settings()
    return {"success": True, "message": "Settings saved."}
