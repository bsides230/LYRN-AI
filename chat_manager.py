import os
from pathlib import Path
from datetime import datetime

class ChatManager:
    """
    Manages the chat history files in the `chat/` directory.
    This includes enforcing a maximum number of files and preparing
    chat history for injection into the prompt.
    """
    def __init__(self, chat_dir: str, settings_manager):
        self.chat_dir = Path(chat_dir)
        self.settings_manager = settings_manager
        self.chat_dir.mkdir(parents=True, exist_ok=True)

    def manage_chat_history_files(self):
        """
        Ensures the number of chat files in the chat directory does not
        exceed the user-defined limit. Deletes the oldest files if necessary.
        """
        history_limit = self.settings_manager.get_setting("chat_history_length", 10)
        if history_limit <= 0:
            # If limit is zero or less, we can just clear the directory.
            for f in self.chat_dir.glob("*.txt"):
                f.unlink()
            return

        try:
            files = sorted(self.chat_dir.glob("*.txt"), key=os.path.getmtime)
            if len(files) > history_limit:
                num_to_delete = len(files) - history_limit
                for i in range(num_to_delete):
                    files[i].unlink()
                    print(f"Deleted old chat file: {files[i].name}")
        except Exception as e:
            print(f"Error managing chat history files: {e}")

    def get_live_chat_history_content(self) -> str:
        """
        Reads all chat files, concatenates them, and returns them as a
        single string block for prompt injection.
        """
        if not self.settings_manager.get_setting("enable_chat_history", True):
            return ""

        self.manage_chat_history_files()

        try:
            files = sorted(self.chat_dir.glob("*.txt"), key=os.path.getmtime)
            if not files:
                return ""

            # The user wants the combined history injected as 'live_chats.txt'
            # Let's build that content.
            full_history = []
            for file_path in files:
                # This assumes the file format is simple user/assistant turns.
                # The StructuredChatLogger saves in a #USER_START# format. We need to parse that.
                # For now, let's just get the raw content. A future refinement could parse it.
                full_history.append(file_path.read_text(encoding='utf-8'))

            # Create a single block as requested
            live_chats_content = "\n\n".join(full_history)

            # Wrap in a clear block for the LLM
            return f"###LIVE_CHAT_HISTORY_START###\n{live_chats_content}\n###LIVE_CHAT_HISTORY_END###"

        except Exception as e:
            print(f"Error getting live chat history: {e}")
            return ""
