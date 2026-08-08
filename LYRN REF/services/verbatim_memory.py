import os
import json
import csv
import shutil
from datetime import datetime, timezone

BASE_DIR = os.path.join("memory", "verbatim")

def _get_convo_dir(convo_id: str) -> str:
    return os.path.join(BASE_DIR, convo_id)

def _get_meta_path(convo_id: str) -> str:
    return os.path.join(_get_convo_dir(convo_id), "convo_meta.json")

def _get_block_path(convo_id: str, block_id: int) -> str:
    return os.path.join(_get_convo_dir(convo_id), f"Block_{block_id:04d}.csv")

def _now() -> str:
    # Use ISO-8601 UTC as required by parser contract
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def create_or_load_conversation(convo_id: str) -> dict:
    """Creates the folder if it does not exist and loads or initializes metadata."""
    os.makedirs(BASE_DIR, exist_ok=True)
    convo_dir = _get_convo_dir(convo_id)
    meta_path = _get_meta_path(convo_id)

    if not os.path.exists(convo_dir):
        os.makedirs(convo_dir, exist_ok=True)

    if not os.path.exists(meta_path):
        now = _now()
        meta = {
            "convo_id": convo_id,
            "created": now,
            "last_updated": now,
            "block_count": 0,
            "total_pairs": 0,
            "next_pair_id": 1
        }
        _save_meta(convo_id, meta)
        return meta

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
        if "next_pair_id" not in meta:
            meta["next_pair_id"] = meta["total_pairs"] + 1
        return meta

def _save_meta(convo_id: str, meta: dict):
    """Saves metadata for the conversation."""
    with open(_get_meta_path(convo_id), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

def _init_block(convo_id: str, block_id: int):
    """Initializes a new block CSV with headers."""
    block_path = _get_block_path(convo_id, block_id)
    if not os.path.exists(block_path):
        with open(block_path, "w", encoding="utf-8", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Timestamp_Start", "Timestamp_End", "Input", "Output", "Summary"])

def _recalculate_meta(convo_id: str):
    """Recalculates block_count and total_pairs based on actual files."""
    meta_path = _get_meta_path(convo_id)
    if not os.path.exists(meta_path):
        return

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    convo_dir = _get_convo_dir(convo_id)
    total_pairs = 0
    highest_block = 0

    for filename in os.listdir(convo_dir):
        if filename.startswith("Block_") and filename.endswith(".csv"):
            try:
                b_id = int(filename.split("_")[1].split(".")[0])
                highest_block = max(highest_block, b_id)
                block_path = os.path.join(convo_dir, filename)
                with open(block_path, "r", encoding="utf-8", newline='') as f:
                    reader = csv.reader(f)
                    total_pairs += max(0, sum(1 for _ in reader) - 1) # exclude header
            except Exception:
                pass

    meta["total_pairs"] = total_pairs
    meta["block_count"] = max(meta.get("block_count", 0), highest_block)
    _save_meta(convo_id, meta)

def save_chat_pair(convo_id: str, input_text: str, output_text: str) -> int:
    """Appends a new chat pair, managing block boundaries."""
    meta = create_or_load_conversation(convo_id)

    if meta["block_count"] == 0:
        current_block = 1
        meta["block_count"] = 1
        _init_block(convo_id, current_block)
    else:
        current_block = meta["block_count"]

    block_path = _get_block_path(convo_id, current_block)

    # Check if we need a new block (max 50)
    row_count = 0
    if os.path.exists(block_path):
        with open(block_path, "r", encoding="utf-8", newline='') as f:
            row_count = sum(1 for _ in csv.reader(f)) - 1

    if row_count >= 50:
        current_block += 1
        meta["block_count"] = current_block
        _init_block(convo_id, current_block)
        block_path = _get_block_path(convo_id, current_block)
    elif not os.path.exists(block_path):
        _init_block(convo_id, current_block)

    now = _now()
    pair_id = meta.get("next_pair_id", meta["total_pairs"] + 1)

    # Write pair
    with open(block_path, "a", encoding="utf-8", newline='') as f:
        writer = csv.writer(f)
        writer.writerow([pair_id, now, now, input_text, output_text, ""])

    # Update meta
    meta["total_pairs"] += 1
    meta["next_pair_id"] = pair_id + 1
    meta["last_updated"] = now
    _save_meta(convo_id, meta)

    return pair_id

def update_summary(convo_id: str, block_id: int, row_id: int, summary_text: str) -> bool:
    """Updates the summary column for a specific chat pair."""
    block_path = _get_block_path(convo_id, block_id)
    if not os.path.exists(block_path):
        return False

    rows = []
    updated = False
    with open(block_path, "r", encoding="utf-8", newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if int(row["ID"]) == row_id:
                row["Summary"] = summary_text
                updated = True
            rows.append(row)

    if updated:
        with open(block_path, "w", encoding="utf-8", newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        meta = create_or_load_conversation(convo_id)
        meta["last_updated"] = _now()
        _save_meta(convo_id, meta)

    return updated

def update_chat_pair(convo_id: str, block_id: int, row_id: int, input_text: str, output_text: str) -> bool:
    """Updates the input and output columns for a specific chat pair."""
    block_path = _get_block_path(convo_id, block_id)
    if not os.path.exists(block_path):
        return False

    rows = []
    updated = False
    with open(block_path, "r", encoding="utf-8", newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if int(row["ID"]) == row_id:
                row["Input"] = input_text
                row["Output"] = output_text
                updated = True
            rows.append(row)

    if updated:
        with open(block_path, "w", encoding="utf-8", newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        meta = create_or_load_conversation(convo_id)
        meta["last_updated"] = _now()
        _save_meta(convo_id, meta)

    return updated

def delete_chat_pair(convo_id: str, block_id: int, row_id: int) -> bool:
    """Deletes a specific chat pair from a block."""
    block_path = _get_block_path(convo_id, block_id)
    if not os.path.exists(block_path):
        return False

    rows = []
    deleted = False
    with open(block_path, "r", encoding="utf-8", newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if int(row["ID"]) == row_id:
                deleted = True
            else:
                rows.append(row)

    if deleted:
        with open(block_path, "w", encoding="utf-8", newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        _recalculate_meta(convo_id)

    return deleted

def delete_block(convo_id: str, block_id: int) -> bool:
    """Deletes an entire block file."""
    block_path = _get_block_path(convo_id, block_id)
    if os.path.exists(block_path):
        os.remove(block_path)
        _recalculate_meta(convo_id)
        return True
    return False

def delete_conversation(convo_id: str) -> bool:
    """Hard deletes the entire conversation directory."""
    convo_dir = _get_convo_dir(convo_id)
    if os.path.exists(convo_dir):
        shutil.rmtree(convo_dir)
        return True
    return False

def clear_conversation(convo_id: str) -> bool:
    """Deletes all blocks in a conversation but keeps metadata."""
    convo_dir = _get_convo_dir(convo_id)
    if not os.path.exists(convo_dir):
        return False

    for filename in os.listdir(convo_dir):
        if filename.startswith("Block_") and filename.endswith(".csv"):
            os.remove(os.path.join(convo_dir, filename))

    meta = create_or_load_conversation(convo_id)
    meta["block_count"] = 0
    meta["total_pairs"] = 0
    meta["next_pair_id"] = 1
    meta["last_updated"] = _now()
    _save_meta(convo_id, meta)
    return True

def get_convo_list() -> list:
    """Returns a list of all conversations."""
    if not os.path.exists(BASE_DIR):
        return []

    convos = []
    for entry in os.listdir(BASE_DIR):
        convo_dir = os.path.join(BASE_DIR, entry)
        if os.path.isdir(convo_dir):
            meta_path = os.path.join(convo_dir, "convo_meta.json")
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        convos.append(meta)
                except Exception:
                    pass

    convos.sort(key=lambda x: x.get("last_updated", ""), reverse=True)
    return convos

def get_blocks(convo_id: str) -> list:
    """Returns a list of blocks and their metadata for a conversation."""
    meta = create_or_load_conversation(convo_id)
    blocks = []
    # Use max possible block_count just in case, but actual files are checked
    highest_b = meta.get("block_count", 0)
    for b in range(1, highest_b + 1):
        block_path = _get_block_path(convo_id, b)
        if not os.path.exists(block_path):
            continue

        with open(block_path, "r", encoding="utf-8", newline='') as f:
            reader = list(csv.DictReader(f))
            if reader:
                start_ts = reader[0].get("Timestamp_Start", "")
                end_ts = reader[-1].get("Timestamp_End", "")

                # Derive an aggregate summary or just keep it simple
                summaries = [r.get("Summary", "") for r in reader if r.get("Summary", "").strip()]
                block_summary = summaries[0] if summaries else ""

                blocks.append({
                    "block_id": b,
                    "timestamp_range": f"{start_ts} to {end_ts}",
                    "summary": block_summary,
                    "pair_count": len(reader)
                })
            else:
                blocks.append({
                    "block_id": b,
                    "timestamp_range": "Empty",
                    "summary": "",
                    "pair_count": 0
                })
    return blocks

def get_block(convo_id: str, block_id: int) -> list:
    """Returns all chat pairs in a block."""
    block_path = _get_block_path(convo_id, block_id)
    if not os.path.exists(block_path):
        return []

    rows = []
    with open(block_path, "r", encoding="utf-8", newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows

def get_chat_pair(convo_id: str, block_id: int, row_id: int) -> dict:
    """Returns a specific chat pair."""
    rows = get_block(convo_id, block_id)
    for row in rows:
        if int(row["ID"]) == row_id:
            return row
    return None
