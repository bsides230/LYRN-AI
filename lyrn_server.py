
import os
import sys
import json
import time
import queue
import threading
import io
import contextlib
import gc
import re
import shutil
import psutil
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from llama_cpp import Llama
except ImportError:
    print("Warning: llama-cpp-python not found. Model features will be disabled.")
    Llama = None

try:
    import pynvml
except ImportError:
    pynvml = None

# Import local modules
from delta_manager import DeltaManager
from automation_controller import AutomationController
from file_lock import SimpleFileLock
from oss_tool_manager import OSSToolManager
from cycle_manager import CycleManager
from episodic_memory_manager import EpisodicMemoryManager
from system_checker import SystemChecker
from chat_manager import ChatManager
# from help_manager import HelpManager # GUI based, skipping

# =========================================================================================
# UTILITY CLASSES (Ported from lyrn_sad_v4.2.11.py)
# =========================================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_PATH = os.path.join(SCRIPT_DIR, "settings.json")

class SettingsManager:
    """Enhanced settings manager with UI preferences"""

    def __init__(self):
        self.settings = None
        self.first_boot = False
        self.ui_settings = {
            "font_size": 12,
            "window_size": "1400x900",
            "confirmation_preferences": {},
            "save_chat_history": True,
            "chat_history_length": 10,
            "show_thinking_text": True,
            "chat_colors": {
                "user_text": "#00C0A0",
                "assistant_text": "#FFFFFF",
                "thinking_text": "#FFD700",
                "system_text": "#B0B0B0"
            }
        }
        self.load_or_detect_first_boot()

    def get_setting(self, key: str, default: any = None) -> any:
        """Gets a setting from the UI settings."""
        return self.ui_settings.get(key, default)

    def set_setting(self, key: str, value: any):
        """Sets a setting in the UI settings and saves it."""
        self.ui_settings[key] = value
        self.save_settings()

    def load_or_detect_first_boot(self):
        """Load settings or create a default one on first boot."""
        if os.path.exists(SETTINGS_PATH):
            try:
                with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.settings = data.get('settings', {})
                    self.ui_settings.update(data.get('ui_settings', {}))

                # Resolve relative paths for the current session
                if "paths" in self.settings:
                    for key, path in self.settings["paths"].items():
                        if path and not os.path.isabs(path):
                            self.settings["paths"][key] = os.path.join(SCRIPT_DIR, path)

                print("Settings loaded successfully")
                self.ensure_automation_flag()
                self.ensure_next_job_flag()
                self.ensure_llm_status_flag()
            except Exception as e:
                print(f"Error loading settings: {e}. Assuming first boot.")
                self.first_boot = True
        else:
            print("No settings.json found - First boot detected. Creating default settings.")
            self.first_boot = True

        if self.first_boot:
            # Create and save a default settings file
            self.settings = self.create_empty_settings_structure()
            default_paths = {
                "static_snapshots": "build_prompt/static_snapshots",
                "dynamic_snapshots": "build_prompt/dynamic_snapshots",
                "active_jobs": "build_prompt/active_jobs",
                "deltas": "deltas",
                "chat": "chat",
                "output": "output",
                "keywords": "active_keywords",
                "topics": "active_topics",
                "active_chunk": "active_chunk",
                "chunk_queue": "automation/chunk_queue.json",
                "job_list": "automation/job_list.txt",
                "job_log": "automation/job_log.json",
                "automation_flag_path": "global_flags/automation.txt",
                "chunk_queue_path": "automation/chunk_queue.json",
                "chat_dir": "chat",
                "chat_parsed_dir": "chat_parsed",
                "audit_dir": "automation/job_audit",
                "metrics_logs": "metrics_logs"
            }
            self.settings["paths"] = default_paths
            self.save_settings() # This saves the file with relative paths

            # Now resolve paths for the current session
            for key, path in self.settings["paths"].items():
                if path and not os.path.isabs(path):
                    self.settings["paths"][key] = os.path.join(SCRIPT_DIR, path)

            self.ensure_automation_flag()
            self.ensure_next_job_flag()
            self.ensure_llm_status_flag()

    def create_empty_settings_structure(self) -> dict:
        """Create empty settings structure for first boot"""
        return {
            "active": {
                "model_path": "",
                "n_ctx": 8192,
                "n_threads": 8,
                "n_gpu_layers": 0,
                "max_tokens": 2048,
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "stream": True
            },
            "paths": {
                "static_snapshots": "",
                "dynamic_snapshots": "",
                "active_jobs": "",
                "deltas": "",
                "chat": "",
                "output": "",
                "keywords": "",
                "topics": "",
                "active_chunk": "",
                "chunk_queue": "",
                "job_list": "",
                "job_log": "",
                "automation_flag_path": "",
                "chunk_queue_path": "",
                "chat_dir": "",
                "chat_parsed_dir": "",
                "audit_dir": "",
                "metrics_logs": ""
            }
        }

    def save_settings(self, settings: dict = None):
        """Save settings and UI preferences to JSON file"""
        try:
            if os.path.exists(SETTINGS_PATH):
                backup_path = SETTINGS_PATH + '.bk'
                shutil.copy2(SETTINGS_PATH, backup_path)

            data = {
                "settings": settings or self.settings,
                "ui_settings": self.ui_settings
            }

            with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            if settings:
                self.settings = settings
            self.first_boot = False
            print("Settings saved successfully")

        except Exception as e:
            print(f"Error saving settings: {e}")

    def ensure_automation_flag(self):
        """Ensure automation flag is set to 'off' on startup"""
        if not self.settings or "paths" not in self.settings:
            return

        flag_path = self.settings["paths"].get("automation_flag_path", "")
        if not flag_path:
            return

        os.makedirs(os.path.dirname(flag_path), exist_ok=True)
        try:
            with open(flag_path, 'w', encoding='utf-8') as f:
                f.write("off")
        except Exception as e:
            print(f"Warning: Could not set automation flag: {e}")

    def ensure_next_job_flag(self):
        """Ensure next job flag is initialized to 'false' on startup"""
        next_job_path = os.path.join(SCRIPT_DIR, "global_flags", "next_job.txt")
        os.makedirs(os.path.dirname(next_job_path), exist_ok=True)

        try:
            with open(next_job_path, 'w', encoding='utf-8') as f:
                f.write("false")
            print("Next job flag initialized to 'false'")
        except Exception as e:
            print(f"Warning: Could not initialize next job flag: {e}")

    def ensure_llm_status_flag(self):
        """Ensure LLM status flag is initialized to 'idle' on startup."""
        llm_status_path = os.path.join(SCRIPT_DIR, "global_flags", "llm_status.txt")
        os.makedirs(os.path.dirname(llm_status_path), exist_ok=True)
        try:
            with open(llm_status_path, 'w', encoding='utf-8') as f:
                f.write("idle")
            print("LLM status flag initialized to 'idle'")
        except Exception as e:
            print(f"Warning: Could not initialize LLM status flag: {e}")

class JournalLogger:
    """Handles the creation and appending of structured journal logs for full auditability."""
    def __init__(self, chat_dir: str):
        self.chat_dir = Path(chat_dir)
        self.chat_dir.mkdir(parents=True, exist_ok=True)
        self.current_log_path = None

    def start_log(self) -> str:
        """Starts a new log file with a timestamp and returns the path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        timestamp_str = datetime.now().strftime("#%Y-%m-%d %H:%M:%S#")
        filename = f"chat_{timestamp}.txt"
        self.current_log_path = self.chat_dir / filename
        with open(self.current_log_path, 'w', encoding='utf-8') as f:
            f.write(f"{timestamp_str}\n\n")
        return str(self.current_log_path)

    def append_log(self, role: str, content: str):
        """Appends a new section to the current log file."""
        if not self.current_log_path:
            # Fallback if start_log wasn't called (e.g., job trigger)
            self.start_log()

        role_upper = role.upper()
        if role_upper == "RESPONSE":
            role_upper = "ASSISTANT"
        start_tag = f"#{role_upper}_START#"
        end_tag = f"#{role_upper}_END#"

        formatted_content = f"{start_tag}\n{content}\n{end_tag}\n\n"

        try:
            with open(self.current_log_path, 'a', encoding='utf-8') as f:
                f.write(formatted_content)
        except Exception as e:
            print(f"Error appending to log file {self.current_log_path}: {e}")

class SystemResourceMonitor:
    """Monitors system resources like CPU, RAM, and VRAM."""
    def __init__(self):
        self.nvml_initialized = False
        if pynvml:
            try:
                pynvml.nvmlInit()
                self.nvml_initialized = True
            except Exception as e:
                print(f"Warning: Could not initialize NVML for GPU monitoring: {e}")

    def get_stats(self) -> Dict[str, any]:
        """Fetches current system stats."""
        stats = {
            "ram_percent": 0, "ram_used_gb": 0, "ram_total_gb": 0,
            "cpu": 0, "cpu_temp": "N/A",
            "vram_percent": 0, "vram_used_gb": 0, "vram_total_gb": 0,
            "disk_percent": 0, "disk_used_gb": 0, "disk_total_gb": 0
        }

        try:
            ram_info = psutil.virtual_memory()
            stats["ram_percent"] = ram_info.percent
            stats["ram_used_gb"] = ram_info.used / (1024**3)
            stats["ram_total_gb"] = ram_info.total / (1024**3)
        except: pass

        try:
            disk_info = psutil.disk_usage(os.path.abspath(SCRIPT_DIR))
            stats["disk_percent"] = disk_info.percent
            stats["disk_used_gb"] = disk_info.used / (1024**3)
            stats["disk_total_gb"] = disk_info.total / (1024**3)
        except: pass

        try:
            stats["cpu"] = psutil.cpu_percent()
        except: pass

        # Get CPU temperature
        try:
            temps = psutil.sensors_temperatures()
            if 'coretemp' in temps:
                stats["cpu_temp"] = f"{temps['coretemp'][0].current:.1f}°C"
            elif 'k10temp' in temps:
                stats["cpu_temp"] = f"{temps['k10temp'][0].current:.1f}°C"
            elif temps:
                key = list(temps.keys())[0]
                stats["cpu_temp"] = f"{temps[key][0].current:.1f}°C"
        except: pass

        # Get VRAM usage
        if self.nvml_initialized:
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                stats["vram_percent"] = (info.used / info.total) * 100
                stats["vram_used_gb"] = info.used / (1024**3)
                stats["vram_total_gb"] = info.total / (1024**3)
            except: pass

        return stats

class SnapshotLoader:
    """Loads the static base prompt from the 'build_prompt' directory."""
    def __init__(self, settings_manager: SettingsManager, automation_controller: AutomationController):
        self.settings_manager = settings_manager
        self.automation_controller = automation_controller
        self.build_prompt_dir = os.path.join(SCRIPT_DIR, "build_prompt")
        self.master_prompt_path = os.path.join(self.build_prompt_dir, "master_prompt.txt")
        self.config_path = os.path.join(self.build_prompt_dir, "builder_config.json")

    def _load_json_file(self, path: str) -> Optional[dict]:
        if not os.path.exists(path): return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return None

    def _load_text_file(self, path: str) -> str:
        if not os.path.exists(path): return ""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except: return ""

    def build_master_prompt_from_components(self) -> str:
        """Simplified build process for backend context."""
        # For simplicity in this port, we will try to just read the master prompt if it exists,
        # otherwise we assume the existing logic generated it.
        # But to be robust, we'll implement a basic read.
        if os.path.exists(self.master_prompt_path):
             return self._load_text_file(self.master_prompt_path)
        return "You are LYRN."

    def load_base_prompt(self) -> str:
        return self.build_master_prompt_from_components()

class EnhancedPerformanceMetrics:
    """Enhanced performance metrics"""
    def __init__(self):
        self.reset_metrics()

    def reset_metrics(self):
        self.kv_cache_reused = 0
        self.prompt_tokens = 0
        self.prompt_speed = 0.0
        self.eval_tokens = 0
        self.eval_speed = 0.0
        self.total_tokens = 0
        self.generation_time_ms = 0.0
        self.tokenization_time_ms = 0.0

    def parse_llama_logs(self, log_output: str):
        try:
            kv_match = re.search(r'(\d+)\s+prefix-match hit', log_output)
            if kv_match: self.kv_cache_reused = int(kv_match.group(1))

            prompt_match = re.search(r'prompt eval time\s*=\s*([\d.]+)\s*ms\s*/\s*(\d+)\s*tokens.*?([\d.]+)\s*ms per token', log_output)
            if prompt_match:
                self.tokenization_time_ms = float(prompt_match.group(1))
                self.prompt_tokens = int(prompt_match.group(2))
                ms_per_token = float(prompt_match.group(3))
                self.prompt_speed = 1000.0 / ms_per_token if ms_per_token > 0 else 0.0

            eval_match = re.search(r'eval time\s*=\s*([\d.]+)\s*ms\s*/\s*(\d+)\s*runs.*?([\d.]+)\s*ms per token', log_output)
            if eval_match:
                self.generation_time_ms = float(eval_match.group(1))
                self.eval_tokens = int(eval_match.group(2))
                ms_per_token = float(eval_match.group(3))
                self.eval_speed = 1000.0 / ms_per_token if ms_per_token > 0 else 0.0

            self.total_tokens = self.prompt_tokens + self.eval_tokens + self.kv_cache_reused
        except Exception as e:
            print(f"Metrics parsing error: {e}")

# =========================================================================================
# APP & STATE
# =========================================================================================

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Manager Instance
class ServiceManager:
    def __init__(self):
        self.settings_manager = SettingsManager()
        self.system_checker = SystemChecker(self.settings_manager)
        self.system_checker.check_and_create_folders()

        self.automation = AutomationController()
        self.delta_manager = DeltaManager()
        self.oss_tool_manager = OSSToolManager()
        self.cycle_manager = CycleManager()
        self.episodic = EpisodicMemoryManager()

        # Chat Manager
        self.role_mappings = {
            "assistant": "final_output",
            "model": "final_output",
            "thinking": "thinking_process"
        }
        chat_path = self.settings_manager.settings["paths"].get("chat", "chat")
        self.chat_manager = ChatManager(chat_path, self.settings_manager, self.role_mappings)
        self.chat_logger = JournalLogger(chat_path)

        self.snapshot_loader = SnapshotLoader(self.settings_manager, self.automation)
        self.metrics = EnhancedPerformanceMetrics()
        self.monitor = SystemResourceMonitor()

        self.llm: Optional[Llama] = None
        self.log_queue = queue.Queue()
        self.stop_generation = False

services = ServiceManager()

# Log capturing setup
class QueueWriter:
    def __init__(self, q): self.q = q
    def write(self, s):
        if s.strip(): self.q.put(s)
    def flush(self): pass

# Redirect stdout/stderr to queue for log viewer (optional, might interfere with uvicorn logs)
# For the API, we will just capture specific logs or use a separate queue for the log viewer endpoint.
# We won't globally redirect stdout/stderr here to avoid breaking the server console.

# =========================================================================================
# API ENDPOINTS
# =========================================================================================

# --- System ---
@app.get("/api/system/status")
async def get_system_status():
    return services.monitor.get_stats()

@app.get("/api/logs")
async def stream_logs(request: Request):
    """Streams logs via SSE. For now, this is a mock or requires a real log sink."""
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            try:
                # In a real impl, we'd tap into python logging or the captured queue
                # For now, let's just send a heartbeat if empty
                if not services.log_queue.empty():
                    line = services.log_queue.get()
                    yield f"data: {json.dumps({'log': line})}\n\n"
                else:
                    await asyncio.sleep(0.5)
            except Exception:
                break
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# --- Model ---
class ModelLoadRequest(BaseModel):
    model_path: str
    n_ctx: int = 8192
    n_threads: int = 8
    n_gpu_layers: int = 0

@app.post("/api/model/load")
async def load_model(req: ModelLoadRequest):
    if services.llm:
        del services.llm
        gc.collect()

    try:
        services.llm = Llama(
            model_path=req.model_path,
            n_ctx=req.n_ctx,
            n_threads=req.n_threads,
            n_gpu_layers=req.n_gpu_layers,
            use_mlock=True,
            verbose=True
        )
        return {"status": "success", "message": "Model loaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/model/unload")
async def unload_model():
    if services.llm:
        del services.llm
        services.llm = None
        gc.collect()
    return {"status": "success", "message": "Model unloaded"}

@app.get("/api/model/status")
async def model_status():
    return {
        "loaded": services.llm is not None,
        "model_path": services.settings_manager.settings["active"].get("model_path")
    }

# --- Chat ---
class ChatRequest(BaseModel):
    message: str
    stream: bool = True

import asyncio

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    if not services.llm:
        raise HTTPException(status_code=503, detail="Model not loaded")

    # Prepare context
    full_prompt = services.snapshot_loader.load_base_prompt()
    history = services.chat_manager.get_chat_history_messages()

    messages = [{"role": "system", "content": full_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": req.message})

    # Log user input
    services.chat_logger.start_log()
    services.chat_logger.append_log("USER", req.message)

    # Streaming logic
    async def response_generator():
        response_content = ""
        # Redirect stderr to capture llama logs for metrics
        log_buffer = io.StringIO()

        try:
            with contextlib.redirect_stderr(log_buffer):
                stream = services.llm.create_chat_completion(
                    messages=messages,
                    max_tokens=services.settings_manager.settings["active"].get("max_tokens", 2048),
                    temperature=services.settings_manager.settings["active"].get("temperature", 0.7),
                    stream=True
                )

                for chunk in stream:
                    if services.stop_generation:
                        break

                    if 'choices' in chunk and len(chunk['choices']) > 0:
                        delta = chunk['choices'][0].get('delta', {})
                        content = delta.get('content', '')
                        if content:
                            response_content += content
                            # Check if content looks like thinking/thought tags
                            # For simplicity in this API port, we just send raw content
                            # The frontend can parse special tags if needed
                            yield json.dumps({"content": content}) + "\n"

            # Process metrics from log_buffer
            services.metrics.parse_llama_logs(log_buffer.getvalue())

            # Log final response
            services.chat_logger.append_log("ASSISTANT", response_content)

            # Save to episodic memory history if enabled
            if services.settings_manager.get_setting("save_chat_history", True):
                # We need to manually write to a file to persist context for next turn
                # The ChatManager reads from files, so we create a new one or append
                pass

        except Exception as e:
             yield json.dumps({"error": str(e)}) + "\n"

    return StreamingResponse(response_generator(), media_type="application/x-ndjson")

# --- Automation / Jobs ---
@app.get("/api/jobs")
async def get_jobs():
    return services.automation.job_definitions

@app.post("/api/jobs")
async def create_job(job_data: Dict[str, Any]):
    # This endpoint needs to parse the job_data properly based on AutomationController.save_job_definition
    name = job_data.get("name")
    instructions = job_data.get("instructions")
    trigger = job_data.get("trigger")
    if name and instructions:
        services.automation.save_job_definition(name, instructions, trigger)
        return {"status": "success", "message": f"Job {name} saved"}
    raise HTTPException(status_code=400, detail="Missing name or instructions")

@app.delete("/api/jobs/{name}")
async def delete_job(name: str):
    services.automation.delete_job_definition(name)
    return {"status": "success", "message": f"Job {name} deleted"}

# --- Cycles ---
@app.get("/api/cycles")
async def get_cycles():
    return services.cycle_manager.cycles

@app.post("/api/cycles")
async def save_cycle(cycle_data: Dict[str, Any]):
    name = cycle_data.get("name")
    triggers = cycle_data.get("triggers")
    if name and triggers is not None:
        services.cycle_manager.save_cycle(name, triggers)
        return {"status": "success"}
    raise HTTPException(status_code=400, detail="Missing data")

@app.delete("/api/cycles/{name}")
async def delete_cycle(name: str):
    services.cycle_manager.delete_cycle(name)
    return {"status": "success"}

# --- Files / Config ---
@app.get("/api/config")
async def get_full_config():
    """Returns the main settings.json content."""
    return services.settings_manager.settings

@app.post("/api/config")
async def update_config(config: Dict[str, Any]):
    """Updates settings.json."""
    services.settings_manager.save_settings(config)
    return {"status": "success"}

# =========================================================================================
# STATIC FILES
# =========================================================================================

# Mount the dashboard root
app.mount("/", StaticFiles(directory="LYRN_v5", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # In a real deployment we might want to bind 0.0.0.0, but per user request "localhost/LAN/Tailscale"
    # 0.0.0.0 covers all interfaces.
    print("Starting LYRN Server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
