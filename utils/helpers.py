from pathlib import Path

import os
import datetime

def _get_file_explanation(filepath: Path) -> str:
    """Heuristic logic to generate a short file explanation."""
    name = filepath.name.lower()
    ext = filepath.suffix.lower()

    if ext == '.py':
        if 'test' in name: return "Python test script"
        if 'manager' in name or 'controller' in name: return "Python management/controller logic"
        return "Python source file"
    if ext == '.js': return "JavaScript file"
    if ext == '.html': return "HTML structure"
    if ext == '.css': return "CSS stylesheet"
    if ext == '.json': return "JSON configuration/data file"
    if ext == '.csv': return "CSV data file"
    if ext == '.md': return "Markdown documentation"
    if ext == '.txt': return "Text file"
    if ext in ['.png', '.jpg', '.jpeg', '.gif', '.ico']: return "Image file"

    return "Unknown file type"

def trigger_chat_generation(message: str, folder: str = "chat"):
    """Creates a chat file and triggers the worker."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{folder}/{folder}_{timestamp}.txt"
    filepath = os.path.abspath(filename)

    # Ensure directory
    os.makedirs(folder, exist_ok=True)

    # Write User Message
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"user\n{message}\n")
    print(f"[System] Created chat file: {filepath}")

    # Write Trigger
    with open("chat_trigger.txt", "w", encoding="utf-8") as f:
        f.write(filepath)
    print(f"[System] Wrote trigger file: chat_trigger.txt")

    return filepath, os.path.basename(filepath)
