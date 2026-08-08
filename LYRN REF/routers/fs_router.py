import os
import json
import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from core.security import verify_token
from models.schemas import FileTreeSelectionModel, InjectArtifactModel, FileTreeProfileModel
from utils.helpers import _get_file_explanation

router = APIRouter(prefix="/api/fs", tags=["fs"])

@router.get("/list", dependencies=[Depends(verify_token)])
async def fs_list(path: str):
    """Returns directory contents for the given path."""
    try:
        req_path = Path(path).resolve()
        if not req_path.exists() or not req_path.is_dir():
            raise HTTPException(status_code=404, detail="Directory not found or is not a directory.")

        children = []

        # Default ignore list
        ignore_dirs = {'node_modules', '__pycache__', 'dist', 'build', 'target', 'venv', 'env', '.venv', '.git'}

        for entry in os.scandir(req_path):
            # Skip hidden files and some common huge directories
            if entry.name.startswith('.') or entry.name in ignore_dirs:
                continue

            is_dir = entry.is_dir()
            children.append({
                "name": entry.name,
                "path": entry.path,
                "is_dir": is_dir
            })

        return {
            "name": req_path.name,
            "path": str(req_path),
            "children": children
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/compile", dependencies=[Depends(verify_token)])
async def fs_compile(payload: FileTreeSelectionModel):
    """Compiles the selected tree into a repo-RWI artifact."""
    root_path = Path(payload.root_path)
    selections = payload.selections

    # Exclusions
    ignore_exts = {'.pyc', '.exe', '.dll', '.so', '.dylib', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.zip', '.tar', '.gz'}
    max_file_size = 500 * 1024  # 500 KB limit for expansion

    artifact_lines = []

    # 1. Header
    artifact_lines.append("==================================================================")
    artifact_lines.append(f"REPOSITORY CONTEXT: {payload.root_name}")
    artifact_lines.append(f"LOCAL PATH: {root_path}")
    artifact_lines.append(f"GENERATED: {datetime.datetime.now().isoformat()}")
    artifact_lines.append("==================================================================\n")

    # 2. Structured Tree Listing
    artifact_lines.append("### REPOSITORY STRUCTURE ###")
    artifact_lines.append("The following files and directories are present in the repository:")

    expanded_files = [] # Tuples of (relative_path, full_path, explanation)

    for rel_path_str, state in selections.items():
        if state.get("include"):
            is_dir = state.get("is_dir", False)
            icon = "📁" if is_dir else "📄"
            depth = len(rel_path_str.replace('\\', '/').split('/')) - 1
            indent = "  " * depth

            # Simple explanation
            full_path = root_path / rel_path_str
            explanation = _get_file_explanation(full_path) if not is_dir else "Folder"

            expand_mark = "[EXPANDED]" if state.get("expand") and not is_dir else ""
            artifact_lines.append(f"{indent}- {icon} {rel_path_str} : {explanation} {expand_mark}")

        if state.get("expand"):
            # If it's a directory, we could recursively expand, but for phase 1 we trust the user selected files directly
            # or we expand files inside. For now, let's just expand explicitly selected files.
            is_dir = state.get("is_dir", False)
            if not is_dir:
                full_path = root_path / rel_path_str
                expanded_files.append((rel_path_str, full_path, _get_file_explanation(full_path)))
            else:
                # Recursively add files in the expanded directory
                dir_path = root_path / rel_path_str
                if dir_path.exists() and dir_path.is_dir():
                    for root, _, files in os.walk(dir_path):
                        for file in files:
                            if file.startswith('.'): continue
                            fpath = Path(root) / file
                            rpath = str(fpath.relative_to(root_path)).replace('\\', '/')
                            expanded_files.append((rpath, fpath, _get_file_explanation(fpath)))


    # Deduplicate expanded files (in case a file AND its parent dir were marked 'expand')
    seen = set()
    unique_expanded = []
    for r, f, e in expanded_files:
        if r not in seen:
            seen.add(r)
            unique_expanded.append((r, f, e))

    # 3. Content Expansion
    artifact_lines.append("\n### FILE CONTENTS ###")
    artifact_lines.append("The following files have been expanded for detailed inspection:\n")

    for rel_path, full_path, explanation in unique_expanded:
        if not full_path.exists():
            continue

        if full_path.suffix.lower() in ignore_exts:
            continue

        try:
            stat = full_path.stat()
            if stat.st_size > max_file_size:
                artifact_lines.append(f"--- FILE: {rel_path} ---")
                artifact_lines.append(f"Explanation: {explanation}")
                artifact_lines.append(f"[CONTENT SKIPPED: File size ({stat.st_size} bytes) exceeds {max_file_size} bytes limit]\n")
                continue

            content = full_path.read_text(encoding='utf-8')

            artifact_lines.append(f"--- FILE: {rel_path} ---")
            artifact_lines.append(f"Explanation: {explanation}")
            artifact_lines.append("Content:")
            artifact_lines.append("```")
            artifact_lines.append(content)
            artifact_lines.append("```\n")

        except UnicodeDecodeError:
            artifact_lines.append(f"--- FILE: {rel_path} ---")
            artifact_lines.append(f"Explanation: {explanation}")
            artifact_lines.append("[CONTENT SKIPPED: Binary file detected]\n")
        except Exception as e:
            artifact_lines.append(f"--- FILE: {rel_path} ---")
            artifact_lines.append(f"[ERROR READING FILE: {e}]\n")

    return {"artifact": "\n".join(artifact_lines)}

@router.post("/inject", dependencies=[Depends(verify_token)])
async def fs_inject(payload: InjectArtifactModel):
    """Saves the artifact to be injected on the next run."""
    try:
        flags_dir = Path("global_flags")
        flags_dir.mkdir(exist_ok=True)
        with open(flags_dir / "repo_context.txt", "w", encoding="utf-8") as f:
            f.write(payload.artifact)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/inject", dependencies=[Depends(verify_token)])
async def fs_clear_inject():
    """Clears the injected repo context."""
    try:
        context_file = Path("global_flags/repo_context.txt")
        if context_file.exists():
            context_file.unlink()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profiles", dependencies=[Depends(verify_token)])
async def get_fs_profiles():
    try:
        profiles_dir = Path("repo_profiles")
        if not profiles_dir.exists(): return []
        return [f.stem for f in profiles_dir.glob("*.json")]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profiles/{name}", dependencies=[Depends(verify_token)])
async def load_fs_profile(name: str):
    try:
        file_path = Path("repo_profiles") / f"{name}.json"
        if not file_path.exists(): raise HTTPException(status_code=404, detail="Profile not found")
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/profiles", dependencies=[Depends(verify_token)])
async def save_fs_profile(payload: FileTreeProfileModel):
    try:
        profiles_dir = Path("repo_profiles")
        profiles_dir.mkdir(exist_ok=True)
        file_path = profiles_dir / f"{payload.name}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(payload.dict(), f, indent=2)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
