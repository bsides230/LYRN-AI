import json
import datetime
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from core.security import verify_token
from core.registry import settings_manager
from models.schemas import SnapshotSaveModel, SnapshotLoadModel

router = APIRouter(prefix="/api", tags=["snapshots"])

@router.get("/snapshots", dependencies=[Depends(verify_token)])
async def list_snapshots():
    """Lists available .sns files in the snapshots/ directory."""
    snapshots_dir = Path("snapshots")
    if not snapshots_dir.exists():
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        return []

    snapshots = []
    for f in snapshots_dir.glob("*.sns"):
        stat = f.stat()
        snapshots.append({
            "name": f.name,
            "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
        })
    return sorted(snapshots, key=lambda x: x['name'])

async def _save_components_to_build_prompt(components: List[Dict[str, Any]]):
    """Helper to save components to build_prompt directory."""
    try:
        base_dir = Path("build_prompt")
        base_dir.mkdir(parents=True, exist_ok=True)

        # 1. Save components.json (without content field)
        clean_components = []
        for c in components:
            copy = c.copy()
            if "content" in copy:
                del copy["content"]
            clean_components.append(copy)

        with open(base_dir / "components.json", "w", encoding='utf-8') as f:
            json.dump(clean_components, f, indent=2)

        # 2. Save content files
        for c in components:
            name = c.get("name")
            if not name or name == "RWI": continue

            content = c.get("content", "")
            comp_dir = base_dir / name
            comp_dir.mkdir(exist_ok=True)

            config_path = comp_dir / "config.json"
            config = {}
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                except: pass

            if "config" in c:
                frontend_config = c["config"]
                if "begin_bracket" in frontend_config: config["begin_bracket"] = frontend_config["begin_bracket"]
                if "end_bracket" in frontend_config: config["end_bracket"] = frontend_config["end_bracket"]
                if "rwi_text" in frontend_config: config["rwi_text"] = frontend_config["rwi_text"]

            if "content_file" not in config:
                config["content_file"] = "content.txt"

            with open(config_path, "w", encoding='utf-8') as f:
                json.dump(config, f, indent=2)

            with open(comp_dir / config["content_file"], "w", encoding='utf-8') as f:
                f.write(content)
        return True
    except Exception as e:
        print(f"Error saving to build_prompt: {e}")
        raise e

@router.post("/snapshots/save", dependencies=[Depends(verify_token)])
async def save_named_snapshot(data: SnapshotSaveModel):
    """Saves to a file AND updates the build_prompt."""
    try:
        # 1. Save to .sns file
        snapshots_dir = Path("snapshots")
        snapshots_dir.mkdir(parents=True, exist_ok=True)

        filename = data.filename
        if not filename.endswith(".sns"):
            filename += ".sns"

        file_path = snapshots_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data.components, f, indent=2)

        # 2. Update build_prompt (Active State)
        await _save_components_to_build_prompt(data.components)

        # 3. Update Settings (Active Snapshot)
        if not settings_manager.settings:
            settings_manager.load_or_detect_first_boot()

        settings_manager.settings["active_snapshot"] = filename
        settings_manager.save_settings()

        return {"success": True, "saved_as": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/snapshots/load", dependencies=[Depends(verify_token)])
async def load_named_snapshot(data: SnapshotLoadModel):
    """Loads a specific .sns file into build_prompt and returns content."""
    try:
        snapshots_dir = Path("snapshots")
        filename = data.filename
        file_path = snapshots_dir / filename

        if not file_path.exists():
             raise HTTPException(status_code=404, detail="Snapshot file not found")

        with open(file_path, "r", encoding="utf-8") as f:
            components = json.load(f)

        # 1. Update build_prompt (Active State)
        await _save_components_to_build_prompt(components)

        # 2. Update Settings
        if not settings_manager.settings:
            settings_manager.load_or_detect_first_boot()

        settings_manager.settings["active_snapshot"] = filename
        settings_manager.save_settings()

        return components
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/snapshot", dependencies=[Depends(verify_token)])
async def get_snapshot():
    """Reads components and their content."""
    try:
        base_dir = Path("build_prompt")
        comp_path = base_dir / "components.json"

        if not comp_path.exists():
            return [] # Return empty list if no file

        with open(comp_path, 'r', encoding='utf-8') as f:
            components = json.load(f)

        # Enhance components with content
        for comp in components:
            name = comp.get("name")
            if name == "RWI":
                continue

            # Look for content in subdir
            comp_dir = base_dir / name
            config_path = comp_dir / "config.json"

            content_file = "content.txt"

            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        c = json.load(f)
                        content_file = c.get("content_file", "content.txt")
                except: pass

            content_path = comp_dir / content_file
            if content_path.exists():
                try:
                    comp["content"] = content_path.read_text(encoding='utf-8')
                except:
                    comp["content"] = ""
            else:
                 comp["content"] = ""

        return components
    except Exception as e:
        print(f"Error getting snapshot: {e}")
        return []

@router.post("/snapshot", dependencies=[Depends(verify_token)])
async def save_snapshot(components: List[Dict[str, Any]]):
    """Saves components list and updates content files. (Legacy/Quick Save)"""
    try:
        await _save_components_to_build_prompt(components)
        return {"success": True}
    except Exception as e:
        print(f"Error saving snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/snapshot/rebuild", dependencies=[Depends(verify_token)])
async def rebuild_snapshot():
    """Triggers a snapshot rebuild in the worker."""
    try:
        with open("rebuild_trigger.txt", "w", encoding='utf-8') as f:
            f.write("rebuild")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
