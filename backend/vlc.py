import os
import subprocess
import socket
import tempfile
import psutil
import platform
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.auth import verify_token
from backend.utils import check_path_access
from backend.config import settings_manager

router = APIRouter()

class VLCLaunchRequest(BaseModel):
    path: str

class VLCCommandRequest(BaseModel):
    command: str

class VLCManager:
    def __init__(self, host="127.0.0.1", port=4212):
        self.host = host
        self.port = port
        self.process = None

    def _send_command(self, cmd: str) -> str:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                s.connect((self.host, self.port))
                try: s.recv(1024)
                except: pass
                s.sendall(f"{cmd}\n".encode())
                data = b""
                try:
                    while True:
                        chunk = s.recv(4096)
                        if not chunk: break
                        data += chunk
                        if len(chunk) < 4096: break
                except socket.timeout: pass
                return data.decode(errors="ignore").strip()
        except ConnectionRefusedError:
            return "Error: VLC not running or RC interface not active."
        except Exception as e:
            return f"Error: {str(e)}"

    def launch(self, path: str):
        self.kill()
        playlist_path = self._create_playlist(path)
        if not playlist_path: raise Exception("Could not create playlist")

        custom_vlc = settings_manager.settings.get("vlc_path")
        vlc_bin = custom_vlc if custom_vlc and custom_vlc.strip() else "vlc"

        cmd = [
            vlc_bin,
            "--extraintf", "rc",
            "--rc-host", f"{self.host}:{self.port}",
            "--fullscreen", "--loop", "--random",
            playlist_path
        ]

        try:
            if platform.system() == "Windows":
                 self.process = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                 env = os.environ.copy()
                 if "DISPLAY" not in env: env["DISPLAY"] = ":0"
                 self.process = subprocess.Popen(cmd, env=env, preexec_fn=os.setsid)
        except FileNotFoundError:
             if custom_vlc: raise Exception(f"VLC executable not found at: {custom_vlc}")
             raise Exception("VLC executable not found. Install VLC or configure path.")

    def kill(self):
        if self.process:
            try:
                self.process.terminate()
                self.process = None
            except: pass
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info and proc.info['name'] and "vlc" in proc.info['name'].lower():
                        proc.terminate()
                except: pass
        except: pass

    def _create_playlist(self, folder_path: str):
        p = Path(folder_path)
        if not p.exists(): return None
        media_exts = {'.mp4', '.mkv', '.avi', '.mov', '.mp3', '.flac', '.wav', '.webm', '.m4v'}
        files = []
        if p.is_file(): files.append(p)
        else:
            for entry in p.iterdir():
                if entry.is_file() and entry.suffix.lower() in media_exts:
                    files.append(entry)
        if not files: return None
        fd, temp_path = tempfile.mkstemp(suffix=".m3u", prefix="remodash_vlc_")
        os.close(fd)
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for item in files: f.write(f"{str(item)}\n")
        return temp_path

    def command(self, action: str):
        valid = {
            "play": "play", "pause": "pause", "stop": "stop",
            "next": "next", "prev": "prev",
            "vol_up": "volup 2", "vol_down": "voldown 2",
            "fullscreen": "f"
        }
        if action in valid: return self._send_command(valid[action])
        return "Invalid command"

    def get_status(self):
        state = self._send_command("status").replace(">", "").strip()
        title = self._send_command("get_title").replace(">", "").strip()
        return {"state": state, "title": title}

vlc_manager = VLCManager()

@router.post("/launch")
async def vlc_launch(req: VLCLaunchRequest, token: str = Depends(verify_token)):
    try:
        check_path_access(req.path)
        vlc_manager.launch(req.path)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/command")
async def vlc_command_endpoint(req: VLCCommandRequest, token: str = Depends(verify_token)):
    try:
        res = vlc_manager.command(req.command)
        return {"result": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def vlc_status(token: str = Depends(verify_token)):
    try:
        return vlc_manager.get_status()
    except Exception as e:
        return {"state": "error", "title": str(e)}

@router.post("/kill")
async def vlc_kill(token: str = Depends(verify_token)):
    vlc_manager.kill()
    return {"success": True}
