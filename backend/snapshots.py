import os
import json
import datetime
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth import verify_token
from backend.config import settings_manager

router = APIRouter()

class SnapshotSaveModel(BaseModel):
    filename: str
    components: List[Dict[str, Any]]

class SnapshotLoadModel(BaseModel):
    filename: str

async def _save_components_to_build_prompt(components: List[Dict[str, Any]]):
    try:
        base_dir = Path("build_prompt")
        base_dir.mkdir(parents=True, exist_ok=True)

        clean_components = []
        for c in components:
            copy = c.copy()
            if "content" in copy: del copy["content"]
            clean_components.append(copy)

        with open(base_dir / "components.json", "w", encoding='utf-8') as f:
            json.dump(clean_components, f, indent=2)

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
                    with open(config_path, 'r', encoding='utf-8') as f: config = json.load(f)
                except: pass

            if "config" in c:
                fc = c["config"]
                if "begin_bracket" in fc: config["begin_bracket"] = fc["begin_bracket"]
                if "end_bracket" in fc: config["end_bracket"] = fc["end_bracket"]
                if "rwi_text" in fc: config["rwi_text"] = fc["rwi_text"]

            if "content_file" not in config: config["content_file"] = "content.txt"

            with open(config_path, "w", encoding='utf-8') as f: json.dump(config, f, indent=2)
            with open(comp_dir / config["content_file"], "w", encoding='utf-8') as f: f.write(content)
        return True
    except Exception as e:
        print(f"Error saving to build_prompt: {e}")
        raise e

@router.get("/list")
async def list_snapshots(token: str = Depends(verify_token)):
    snapshots_dir = Path("snapshots")
    if not snapshots_dir.exists(): return []
    snapshots = []
    for f in snapshots_dir.glob("*.sns"):
        snapshots.append({
            "name": f.name,
            "modified": datetime.datetime.fromtimestamp(f.stat().st_mtime).isoformat()
        })
    return sorted(snapshots, key=lambda x: x['name'])

@router.post("/save")
async def save_named_snapshot(data: SnapshotSaveModel, token: str = Depends(verify_token)):
    try:
        snapshots_dir = Path("snapshots")
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        filename = data.filename if data.filename.endswith(".sns") else f"{data.filename}.sns"

        with open(snapshots_dir / filename, "w", encoding="utf-8") as f:
            json.dump(data.components, f, indent=2)

        await _save_components_to_build_prompt(data.components)
        settings_manager.settings["active_snapshot"] = filename
        settings_manager.save_settings()
        return {"success": True, "saved_as": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/load")
async def load_named_snapshot(data: SnapshotLoadModel, token: str = Depends(verify_token)):
    try:
        file_path = Path("snapshots") / data.filename
        if not file_path.exists(): raise HTTPException(status_code=404, detail="Not found")
        with open(file_path, "r", encoding="utf-8") as f: components = json.load(f)
        await _save_components_to_build_prompt(components)
        settings_manager.settings["active_snapshot"] = data.filename
        settings_manager.save_settings()
        return components
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/current")
async def get_snapshot(token: str = Depends(verify_token)):
    try:
        base_dir = Path("build_prompt")
        comp_path = base_dir / "components.json"
        if not comp_path.exists(): return []
        with open(comp_path, 'r', encoding='utf-8') as f: components = json.load(f)

        for comp in components:
            name = comp.get("name")
            if name == "RWI": continue
            comp_dir = base_dir / name
            config_path = comp_dir / "config.json"
            content_file = "content.txt"
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        content_file = json.load(f).get("content_file", "content.txt")
                except: pass

            content_path = comp_dir / content_file
            if content_path.exists():
                try: comp["content"] = content_path.read_text(encoding='utf-8')
                except: comp["content"] = ""
            else: comp["content"] = ""
        return components
    except Exception as e:
        return []

@router.post("/current")
async def save_snapshot(components: List[Dict[str, Any]], token: str = Depends(verify_token)):
    try:
        await _save_components_to_build_prompt(components)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rebuild")
async def rebuild_snapshot(token: str = Depends(verify_token)):
    try:
        with open("rebuild_trigger.txt", "w", encoding='utf-8') as f: f.write("rebuild")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
