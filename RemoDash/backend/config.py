import os
import json
import shutil
from pathlib import Path

# Use Current Working Directory
SETTINGS_PATH = "settings.json"

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

                # Resolve relative paths for the current session (Using CWD)
                cwd = os.getcwd()
                if "paths" in self.settings:
                    for key, path in self.settings["paths"].items():
                        if path and not os.path.isabs(path):
                            self.settings["paths"][key] = os.path.join(cwd, path)

                print(f"Settings loaded successfully from {os.path.abspath(SETTINGS_PATH)}")
                self.ensure_automation_flag()
                self.ensure_next_job_flag()
                self.ensure_llm_status_flag()
            except Exception as e:
                print(f"Error loading settings: {e}. Assuming first boot.")
                self.first_boot = True
        else:
            print(f"No settings.json found in {os.getcwd()} - First boot detected.")
            self.first_boot = True

        if self.first_boot:
            # Create and save a default settings file
            self.settings = self.create_empty_settings_structure()
            # Default paths relative to CWD
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
            self.save_settings()

            # Resolve paths
            cwd = os.getcwd()
            for key, path in self.settings["paths"].items():
                if path and not os.path.isabs(path):
                    self.settings["paths"][key] = os.path.join(cwd, path)

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
            "allowed_origins": [],
            "modules": [], # Unified modules list
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
            # print("Settings saved successfully")

        except Exception as e:
            print(f"Error saving settings: {e}")

    def ensure_automation_flag(self):
        if not self.settings or "paths" not in self.settings:
            return
        flag_path = self.settings["paths"].get("automation_flag_path", "")
        if not flag_path: return
        os.makedirs(os.path.dirname(flag_path), exist_ok=True)
        try:
            with open(flag_path, 'w', encoding='utf-8') as f: f.write("off")
        except Exception: pass

    def ensure_next_job_flag(self):
        next_job_path = os.path.join("global_flags", "next_job.txt")
        os.makedirs(os.path.dirname(next_job_path), exist_ok=True)
        try:
            with open(next_job_path, 'w', encoding='utf-8') as f: f.write("false")
        except Exception: pass

    def ensure_llm_status_flag(self):
        llm_status_path = os.path.join("global_flags", "llm_status.txt")
        os.makedirs(os.path.dirname(llm_status_path), exist_ok=True)
        try:
            with open(llm_status_path, 'w', encoding='utf-8') as f: f.write("idle")
        except Exception: pass

# Global Instance
settings_manager = SettingsManager()
