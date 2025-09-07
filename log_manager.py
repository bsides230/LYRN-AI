import os
from pathlib import Path
from datetime import datetime

class JournalLogger:
    """
    Handles the creation and appending of the permanent, auditable journal log.
    This log captures all actions for full auditability.
    """
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.log_dir / "journal.log"

    def log(self, role: str, content: str):
        """
        Appends a new entry to the journal log file.
        """
        timestamp = datetime.now().isoformat()
        role_upper = role.upper()

        start_tag = f"#{role_upper}_START# {timestamp}"
        end_tag = f"#{role_upper}_END#"

        formatted_content = f"{start_tag}\n{content}\n{end_tag}\n\n"

        try:
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(formatted_content)
        except Exception as e:
            print(f"Error appending to journal log file {self.log_path}: {e}")

class LiveDisplayLogger:
    """
    Manages a temporary, session-only log file used to populate the GUI display.
    This log contains only content intended for display.
    """
    def __init__(self, temp_dir: str = "temp"):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.temp_dir / "session_display.log"
        # Ensure the log is clear on startup
        self.clear()

    def log(self, role: str, content: str):
        """
        Appends a new entry to the temporary session log file.
        """
        role_upper = role.upper()
        start_tag = f"#{role_upper}_START#"
        end_tag = f"#{role_upper}_END#"

        formatted_content = f"{start_tag}\n{content}\n{end_tag}\n\n"

        try:
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(formatted_content)
        except Exception as e:
            print(f"Error appending to live display log file {self.log_path}: {e}")

    def read_all(self) -> str:
        """
        Reads and returns the entire content of the session log.
        """
        if not self.log_path.exists():
            return ""
        try:
            return self.log_path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"Error reading live display log file {self.log_path}: {e}")
            return ""

    def clear(self):
        """
        Clears the content of the temporary session log file.
        """
        try:
            with open(self.log_path, 'w', encoding='utf-8') as f:
                f.write("")
        except Exception as e:
            print(f"Error clearing live display log file {self.log_path}: {e}")
