import os
import shutil
import subprocess
import datetime
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote_plus
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

try:
    import git
except ImportError:
    git = None

from backend.auth import verify_token
from backend.utils import check_path_access
from backend.config import settings_manager

router = APIRouter()

class GitRepoRequest(BaseModel):
    path: str
    message: Optional[str] = None
    branch: Optional[str] = None
    files: Optional[List[str]] = None
    delete_files: Optional[bool] = False

class GitCloneRequest(BaseModel):
    url: str
    path: Optional[str] = None
    name: Optional[str] = None
    username: Optional[str] = None
    token: Optional[str] = None

@router.get("/repos")
async def list_git_repos(token: str = Depends(verify_token)):
    repos = settings_manager.settings.get("git_repos", [])
    result = []

    # Filter valid
    for path in repos:
        try:
            check_path_access(path) # Ensure access allowed
        except HTTPException:
            continue

        status = "Unknown"
        branch = "Unknown"
        changed = False
        try:
            if git:
                r = git.Repo(path)
                try: branch = r.active_branch.name
                except: branch = "Detached"
                changed = r.is_dirty() or (len(r.untracked_files) > 0)
                status = "Dirty" if changed else "Clean"
        except Exception as e:
            status = f"Error: {str(e)}"

        result.append({
            "path": path,
            "name": os.path.basename(path),
            "status": status,
            "branch": branch,
            "changed": changed
        })
    return result

@router.post("/repos")
async def add_git_repo(req: GitRepoRequest, token: str = Depends(verify_token)):
    p_obj = check_path_access(req.path)
    p = str(p_obj)

    if not p_obj.exists():
        raise HTTPException(status_code=404, detail="Path does not exist")

    current = settings_manager.settings.get("git_repos", [])
    if p not in current:
        current.append(p)
        settings_manager.settings["git_repos"] = current
        settings_manager.save_settings()
    return {"success": True}

@router.post("/repos/remove")
async def remove_git_repo(req: GitRepoRequest, token: str = Depends(verify_token)):
    p = req.path
    current = settings_manager.settings.get("git_repos", [])
    if p in current:
        current.remove(p)
        settings_manager.settings["git_repos"] = current
        settings_manager.save_settings()

    if req.delete_files:
        try:
            p_obj = check_path_access(p)
            if p_obj.exists() and p_obj.is_dir():
                shutil.rmtree(p_obj)
        except Exception as e:
            print(f"Failed to delete repo files: {e}")
            pass

    return {"success": True}

@router.post("/clone")
async def git_clone(req: GitCloneRequest, token: str = Depends(verify_token)):
    if not git: raise HTTPException(status_code=501, detail="GitPython not installed")

    mode = settings_manager.settings.get("git_root_mode", "manual")
    root_path = settings_manager.settings.get("git_root_path", "")
    target_path_str = ""

    if mode == "auto":
        if not root_path:
             raise HTTPException(status_code=400, detail="Git Root Path not configured in settings")
        name = req.name
        if not name:
             try:
                 name = req.url.split("/")[-1]
                 if name.endswith(".git"): name = name[:-4]
             except: pass
        if not name:
             raise HTTPException(status_code=400, detail="Could not determine repository name")
        target_path_str = str(Path(root_path).expanduser() / name)
    else:
        if not req.path:
             raise HTTPException(status_code=400, detail="Path is required in Manual mode")
        target_path_str = req.path

    p_obj = check_path_access(target_path_str)
    if p_obj.exists() and any(p_obj.iterdir()):
         raise HTTPException(status_code=400, detail="Destination path exists and is not empty")

    try:
        env = os.environ.copy()
        env["GIT_SSH_COMMAND"] = "ssh -o StrictHostKeyChecking=no"

        clone_url = req.url
        if req.username and req.token:
            safe_user = quote_plus(req.username)
            safe_token = quote_plus(req.token)
            if clone_url.startswith("https://"):
                clone_url = clone_url.replace("https://", f"https://{safe_user}:{safe_token}@", 1)
            elif clone_url.startswith("http://"):
                clone_url = clone_url.replace("http://", f"http://{safe_user}:{safe_token}@", 1)

        git.Repo.clone_from(clone_url, str(p_obj), env=env)

        current = settings_manager.settings.get("git_repos", [])
        if str(p_obj) not in current:
            current.append(str(p_obj))
            settings_manager.settings["git_repos"] = current
            settings_manager.save_settings()

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_git_status(path: str, token: str = Depends(verify_token)):
    check_path_access(path)
    if not git: raise HTTPException(status_code=501, detail="GitPython not installed")
    try:
        try:
            r = git.Repo(path)
        except git.exc.InvalidGitRepositoryError:
            return {"error": "Invalid Git Repository", "branch": "Invalid", "files": [], "history": []}

        diffs = []
        try:
            for item in r.index.diff(None):
                diffs.append({"file": item.a_path, "type": "modified", "staged": False})
        except: pass
        try:
            _ = r.head.commit
            for item in r.index.diff("HEAD"):
                diffs.append({"file": item.a_path, "type": "modified", "staged": True})
        except: pass
        try:
            for f in r.untracked_files:
                diffs.append({"file": f, "type": "untracked", "staged": False})
        except: pass

        history = []
        try:
            for c in list(r.iter_commits(max_count=10)):
                history.append({
                    "hexsha": c.hexsha[:7],
                    "message": c.message.strip(),
                    "author": str(c.author),
                    "time": c.committed_datetime.isoformat()
                })
        except: pass

        branch_name = "Unknown"
        try:
            branch_name = r.active_branch.name
        except:
            branch_name = "Detached"

        return {"branch": branch_name, "files": diffs, "history": history}
    except Exception as e:
        return {"error": str(e), "branch": "Error", "files": [], "history": []}

@router.post("/commit")
async def git_commit(req: GitRepoRequest, token: str = Depends(verify_token)):
    check_path_access(req.path)
    if not git: raise HTTPException(status_code=501)
    try:
        r = git.Repo(req.path)
        if req.files and len(req.files) > 0:
            r.git.reset()
            for f in req.files: r.git.add(f)
        else:
            r.git.add(A=True)
        r.index.commit(req.message or "Update from RemoDash")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/diff")
async def get_git_diff(path: str, file: str, token: str = Depends(verify_token)):
    check_path_access(path)
    if not git: raise HTTPException(status_code=501)
    try:
        r = git.Repo(path)
        try: diff = r.git.diff('HEAD', file)
        except:
            try:
                diff = r.git.diff(file)
                if not diff and (file in r.untracked_files):
                    with open(os.path.join(path, file), 'r', encoding='utf-8', errors='replace') as f:
                        diff = f.read()
            except: diff = ""
        return {"diff": diff}
    except Exception as e:
        return {"diff": f"Error: {str(e)}"}

@router.post("/push")
async def git_push(req: GitRepoRequest, token: str = Depends(verify_token)):
    check_path_access(req.path)
    if not git: raise HTTPException(status_code=501)
    try:
        r = git.Repo(req.path)
        origin = r.remote(name='origin')
        with r.git.custom_environment(GIT_SSH_COMMAND='ssh -o StrictHostKeyChecking=no'):
            origin.push()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pull")
async def git_pull(req: GitRepoRequest, token: str = Depends(verify_token)):
    check_path_access(req.path)
    if not git: raise HTTPException(status_code=501)
    try:
        r = git.Repo(req.path)
        origin = r.remote(name='origin')
        with r.git.custom_environment(GIT_SSH_COMMAND='ssh -o StrictHostKeyChecking=no'):
            origin.pull()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stash")
async def git_stash(req: GitRepoRequest, token: str = Depends(verify_token)):
    check_path_access(req.path)
    if not git: raise HTTPException(status_code=501)
    try:
        r = git.Repo(req.path)
        r.git.stash('save', req.message or f"Stash {datetime.datetime.now()}")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stash/pop")
async def git_stash_pop(req: GitRepoRequest, token: str = Depends(verify_token)):
    check_path_access(req.path)
    if not git: raise HTTPException(status_code=501)
    try:
        r = git.Repo(req.path)
        r.git.stash('pop')
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/discard")
async def git_discard(req: GitRepoRequest, token: str = Depends(verify_token)):
    check_path_access(req.path)
    if not git: raise HTTPException(status_code=501)
    try:
        r = git.Repo(req.path)
        has_commits = True
        try: _ = r.head.commit
        except ValueError: has_commits = False

        if req.files and len(req.files) > 0:
            for f in req.files:
                if f in r.untracked_files:
                    fp = os.path.join(req.path, f)
                    if os.path.exists(fp):
                        if os.path.isdir(fp): shutil.rmtree(fp)
                        else: os.remove(fp)
                else:
                    if has_commits: r.git.checkout('HEAD', '--', f)
                    else:
                        r.git.rm('--cached', f)
                        fp = os.path.join(req.path, f)
                        if os.path.exists(fp): os.remove(fp)
        else:
            if has_commits: r.git.reset('--hard', 'HEAD')
            else: r.git.rm('-r', '--cached', '.', ignore_unmatch=True)
            r.git.clean('-fd')
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ssh_key")
async def get_ssh_key(token: str = Depends(verify_token)):
    ssh_dir = Path.home() / ".ssh"
    key_types = ["id_ed25519", "id_rsa"]
    found_key = None
    for k in key_types:
        if (ssh_dir / k).exists() and (ssh_dir / f"{k}.pub").exists():
            found_key = ssh_dir / k
            break
    if not found_key: return {"exists": False}
    try:
        pub_path = found_key.with_suffix(".pub")
        pub_content = pub_path.read_text(encoding="utf-8").strip()
        proc = subprocess.run(["ssh-keygen", "-lv", "-f", str(found_key)], capture_output=True, text=True)
        return {"exists": True, "type": found_key.name, "public_key": pub_content, "fingerprint": proc.stdout}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read key: {str(e)}")

@router.post("/ssh_key/generate")
async def generate_ssh_key(token: str = Depends(verify_token)):
    ssh_dir = Path.home() / ".ssh"
    ssh_dir.mkdir(parents=True, exist_ok=True)
    key_path = ssh_dir / "id_ed25519"
    if key_path.exists(): raise HTTPException(status_code=400, detail="Key exists")
    try:
        subprocess.run(["ssh-keygen", "-t", "ed25519", "-C", "remodash@local", "-f", str(key_path), "-N", ""], check=True)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
