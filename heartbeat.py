import json
from pathlib import Path

# The path to the new JSON configuration file
CONFIG_PATH = Path(__file__).parent / "build_prompt" / "heartbeat" / "heartbeat_config.json"

def get_heartbeat_string() -> str:
    """
    Reads the heartbeat configuration and returns the formatted heartbeat string
    to be injected into the system prompt.

    If the heartbeat is disabled or the config file is not found, it returns
    an empty string.
    """
    if not CONFIG_PATH.exists():
        return ""

    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)

        if not config.get("enabled", False):
            return ""

        begin_bracket = config.get("begin_bracket", "")
        body = config.get("body", "")
        end_bracket = config.get("end_bracket", "")

        # Construct the final string, ensuring there are newlines
        # for proper separation in the master prompt.
        if body:
            return f"\n{begin_bracket}\n{body}\n{end_bracket}\n"
        else:
            return ""

    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading heartbeat config: {e}")
        return ""
