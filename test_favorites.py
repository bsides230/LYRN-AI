import asyncio
from pathlib import Path
from core.registry import settings_manager

import json
favorites_path = Path("model_favorites.json")
try:
    with open(favorites_path, "r", encoding="utf-8") as f:
        print("Loaded favorites: ", len(json.load(f)["favorites"]))
except Exception as e:
    print(f"Error: {e}")
