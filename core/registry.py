from settings_manager import SettingsManager
from chat_manager import ChatManager

settings_manager = SettingsManager()

# Initialize ChatManager (Needs settings to be loaded)
settings_manager.load_or_detect_first_boot()
role_mappings = {
    "assistant": "final_output",
    "model": "final_output",
    "thinking": "thinking_process",
    "analysis": "thinking_process"
}
chat_manager = ChatManager(
    settings_manager.settings.get("paths", {}).get("chat", "chat/"),
    settings_manager,
    role_mappings
)
