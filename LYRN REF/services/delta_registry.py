import os
import csv
import uuid
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

DELTAS_DIR = Path("runtime/deltas")
DELTAS_DIR.mkdir(parents=True, exist_ok=True)
CSV_FILE = DELTAS_DIR / "deltas.csv"

CSV_FIELDNAMES = [
    "delta_id",
    "name",
    "script_sequence",
    "trigger_level",
    "update_time",
    "notes",
    "enabled",
    "created_at",
    "updated_at"
]

def _ensure_csv():
    DELTAS_DIR.mkdir(parents=True, exist_ok=True)
    if not CSV_FILE.exists():
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
            writer.writeheader()

def get_deltas() -> List[Dict[str, Any]]:
    _ensure_csv()
    deltas = []
    with open(CSV_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["enabled"] = row["enabled"].lower() == "true"
            deltas.append(row)
    return deltas

def get_delta_by_name(name: str) -> Optional[Dict[str, Any]]:
    deltas = get_deltas()
    for delta in deltas:
        if delta["name"] == name:
            return delta
    return None

def get_delta_by_id(delta_id: str) -> Optional[Dict[str, Any]]:
    deltas = get_deltas()
    for delta in deltas:
        if delta["delta_id"] == delta_id:
            return delta
    return None

def save_delta(delta_data: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_csv()
    deltas = get_deltas()
    now = datetime.datetime.now().isoformat()

    existing_idx = -1
    if "delta_id" in delta_data and delta_data["delta_id"]:
        for i, d in enumerate(deltas):
            if d["delta_id"] == delta_data["delta_id"]:
                existing_idx = i
                break
    else:
        for i, d in enumerate(deltas):
            if d["name"] == delta_data.get("name"):
                existing_idx = i
                break

    if existing_idx >= 0:
        existing = deltas[existing_idx]
        existing["name"] = delta_data.get("name", existing["name"])
        existing["script_sequence"] = delta_data.get("script_sequence", existing["script_sequence"])
        existing["trigger_level"] = delta_data.get("trigger_level", existing["trigger_level"])
        existing["update_time"] = delta_data.get("update_time", existing["update_time"])
        existing["notes"] = delta_data.get("notes", existing["notes"])
        existing["enabled"] = str(delta_data.get("enabled", existing["enabled"])).lower() == "true"
        existing["updated_at"] = now
        deltas[existing_idx] = existing
        saved_delta = existing
    else:
        new_delta = {
            "delta_id": str(uuid.uuid4()),
            "name": delta_data.get("name", ""),
            "script_sequence": delta_data.get("script_sequence", ""),
            "trigger_level": delta_data.get("trigger_level", "Passive"),
            "update_time": delta_data.get("update_time", ""),
            "notes": delta_data.get("notes", ""),
            "enabled": str(delta_data.get("enabled", True)).lower() == "true",
            "created_at": now,
            "updated_at": now
        }
        deltas.append(new_delta)
        saved_delta = new_delta

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for d in deltas:
            row = dict(d)
            row["enabled"] = "true" if d["enabled"] else "false"
            writer.writerow(row)

    return saved_delta

def delete_delta(delta_id: str) -> bool:
    _ensure_csv()
    deltas = get_deltas()
    original_count = len(deltas)
    deltas = [d for d in deltas if d["delta_id"] != delta_id]

    if len(deltas) == original_count:
        return False

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for d in deltas:
            row = dict(d)
            row["enabled"] = "true" if d["enabled"] else "false"
            writer.writerow(row)

    return True
