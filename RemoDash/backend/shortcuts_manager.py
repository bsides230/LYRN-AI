import os
import sys
import json
import uuid
import shlex
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from backend.utils import check_path_access

class Shortcut(BaseModel):
    id: Optional[str] = None
    name: str
    path: str
    type: str = "auto"
    args: Optional[str] = ""
    cwd: Optional[str] = ""
    confirm: bool = False
    capture_output: bool = True
    run_mode: str = "output"

class ShortcutsManager:
    def __init__(self, data_file="data/shortcuts.json"):
        self.data_file = Path(data_file)
        self.shortcuts = []
        self._load()

    def _load(self):
        if not self.data_file.exists():
            try: self.data_file.parent.mkdir(parents=True, exist_ok=True)
            except: pass
            self.shortcuts = []
            self._save()
            return
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.shortcuts = [Shortcut(**s) for s in data.get("shortcuts", [])]
        except Exception as e:
            print(f"Failed to load shortcuts: {e}")
            self.shortcuts = []

    def _save(self):
        try:
            data = {"shortcuts": [s.dict() for s in self.shortcuts]}
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to save shortcuts: {e}")

    def list(self): return self.shortcuts

    def get(self, sid):
        for s in self.shortcuts:
            if s.id == sid: return s
        return None

    def add(self, s: Shortcut):
        if not s.id: s.id = str(uuid.uuid4())
        self.shortcuts.append(s)
        self._save()
        return s

    def update(self, sid, updates: Dict[str, Any]):
        for i, s in enumerate(self.shortcuts):
            if s.id == sid:
                updated = s.copy(update=updates)
                self.shortcuts[i] = updated
                self._save()
                return updated
        return None

    def delete(self, sid):
        self.shortcuts = [s for s in self.shortcuts if s.id != sid]
        self._save()

# Global Instance
shortcuts_manager = ShortcutsManager()

# Execution Helpers
def build_command(s: Shortcut) -> str:
    # Shell string for terminal
    base = s.path
    if " " in base: base = f'"{base}"'
    args = s.args
    ext = os.path.splitext(s.path)[1].lower()
    prefix = ""
    if s.type == "auto":
        if ext == ".py": prefix = "python "
        elif ext == ".js": prefix = "node "
        elif ext == ".sh": prefix = "bash "
        elif ext == ".ps1": prefix = "powershell -ExecutionPolicy Bypass -File "
    elif s.type == "python": prefix = "python "
    elif s.type == "node": prefix = "node "
    elif s.type == "bash": prefix = "bash "
    return f"{prefix}{base} {args}".strip()

def build_command_list(s: Shortcut) -> List[str]:
    # List for subprocess
    path = s.path
    try: args = shlex.split(s.args) if s.args else []
    except: args = s.args.split(" ") if s.args else []
    ext = os.path.splitext(path)[1].lower()
    cmd = [path] + args
    if s.type == "auto":
        if ext == ".py": cmd = [sys.executable, path] + args
        elif ext == ".js": cmd = ["node", path] + args
        elif ext == ".sh": cmd = ["bash", path] + args
        elif ext == ".ps1": cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", path] + args
        elif ext == ".bat": cmd = ["cmd.exe", "/c", path] + args
    elif s.type == "python": cmd = [sys.executable, path] + args
    elif s.type == "node": cmd = ["node", path] + args
    elif s.type == "bash": cmd = ["bash", path] + args
    return cmd
