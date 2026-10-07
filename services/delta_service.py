import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

# Base directory for the project (LYRN REF)
SERVICE_DIR = Path(__file__).resolve().parent
BASE_DIR = SERVICE_DIR.parent
DELTAS_DIR = BASE_DIR / "deltas"
SOURCES_DIR = DELTAS_DIR / "sources"
CONFIG_PATH = DELTAS_DIR / "delta_config.json"
MANIFEST_PATH = DELTAS_DIR / "compiled_manifest.txt"

# Delimiters matching Snapshot formatting conventions
DELTAS_START_TAG = "###DELTAS_START###"
DELTAS_END_TAG = "###DELTAS_END###"
DELTA_RWI_START_TAG = "###DELTA_RWI_START###"
DELTA_RWI_END_TAG = "###DELTA_RWI_END###"

DEFAULT_MODULES = [
    {
        "id": "input_delta",
        "name": "Input Delta",
        "file": "input_delta.txt",
        "enabled": True,
        "order": 0,
        "begin_bracket": "###INPUT_DELTA_START###",
        "end_bracket": "###INPUT_DELTA_END###",
        "description": "Active incoming operational payload classified by input type."
    }
]

def ensure_directories():
    """Ensure deltas and sources directories exist."""
    DELTAS_DIR.mkdir(parents=True, exist_ok=True)
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)

def load_config() -> List[Dict[str, Any]]:
    """Loads the delta modules configuration from delta_config.json."""
    ensure_directories()
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_MODULES)
        return DEFAULT_MODULES

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "modules" in data:
                return data["modules"]
            return DEFAULT_MODULES
    except (json.JSONDecodeError, OSError) as e:
        print(f"[DeltaService] Error reading {CONFIG_PATH}: {e}")
        return DEFAULT_MODULES

def save_config(modules: List[Dict[str, Any]]) -> bool:
    """Saves the delta modules configuration to delta_config.json."""
    ensure_directories()
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(modules, f, indent=2)
        return True
    except OSError as e:
        print(f"[DeltaService] Error writing {CONFIG_PATH}: {e}")
        return False

def get_delta_blocks() -> List[Dict[str, Any]]:
    """
    Returns the list of delta module objects with their current disk contents,
    file presence, character counts, and line counts.
    """
    ensure_directories()
    modules = load_config()
    results = []

    for mod in modules:
        filename = mod.get("file", "")
        source_path = SOURCES_DIR / filename if filename else None
        exists = source_path.exists() if source_path else False
        content = ""
        char_count = 0
        line_count = 0

        if exists and source_path:
            try:
                content = source_path.read_text(encoding="utf-8")
                char_count = len(content)
                line_count = len(content.splitlines())
            except OSError as e:
                print(f"[DeltaService] Error reading {source_path}: {e}")

        item = dict(mod)
        item["exists"] = exists
        item["content"] = content
        item["char_count"] = char_count
        item["line_count"] = line_count
        results.append(item)

    results.sort(key=lambda x: x.get("order", 0))
    return results

def toggle_delta_module(module_id: str, enabled: bool) -> bool:
    """Toggles the 'enabled' state of a specific delta module."""
    modules = load_config()
    found = False
    for mod in modules:
        if mod.get("id") == module_id:
            mod["enabled"] = enabled
            found = True
            break
    if found:
        return save_config(modules)
    return False

def save_delta_order(order_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Updates the order and configuration of delta modules.
    order_data is expected to be a list of objects with at least:
    id, order, enabled, and optionally name, description, begin_bracket, end_bracket.
    """
    current_modules = {m["id"]: m for m in load_config()}
    updated_list = []

    for item in order_data:
        mod_id = item.get("id")
        if mod_id in current_modules:
            mod = current_modules[mod_id]
            mod["order"] = item.get("order", mod.get("order", 0))
            if "enabled" in item:
                mod["enabled"] = item["enabled"]
            if "name" in item and item["name"]:
                mod["name"] = item["name"]
            if "description" in item:
                mod["description"] = item["description"]
            if "begin_bracket" in item and item["begin_bracket"]:
                mod["begin_bracket"] = item["begin_bracket"]
            if "end_bracket" in item and item["end_bracket"]:
                mod["end_bracket"] = item["end_bracket"]
            updated_list.append(mod)

    # Any modules not in order_data are appended at the end
    accounted_ids = {m["id"] for m in updated_list}
    for mod_id, mod in current_modules.items():
        if mod_id not in accounted_ids:
            updated_list.append(mod)

    save_config(updated_list)
    return get_delta_blocks()

def compile_manifest() -> str:
    """
    Compiles active delta modules into deltas/compiled_manifest.txt following
    the Snapshot formatting grammar and RWI structure.
    """
    ensure_directories()
    modules = load_config()
    active_modules = [m for m in modules if m.get("enabled", True)]
    active_modules.sort(key=lambda x: x.get("order", 0))

    if not active_modules:
        try:
            MANIFEST_PATH.write_text("", encoding="utf-8")
        except OSError:
            pass
        return ""

    # Build Delta RWI block with dynamic instructional preamble
    rwi_preamble_path = SOURCES_DIR / "delta_rwi.txt"
    preamble = ""
    if rwi_preamble_path.exists():
        try:
            preamble = rwi_preamble_path.read_text(encoding="utf-8").strip()
        except OSError:
            preamble = ""

    if not preamble:
        preamble = (
            "Delta Relational Web Index (RWI): Dynamic operational state framework.\n\n"
            "Deltas represent transient, mutable working memory (Layer 2) that updates per turn "
            "without invalidating the immutable Layer 1 KV cache prefix."
        )

    rwi_entries = []
    for mod in active_modules:
        mod_id = mod.get("id", "")
        begin_tag = mod.get("begin_bracket", f"###{mod_id.upper()}_START###")
        end_tag = mod.get("end_bracket", f"###{mod_id.upper()}_END###")
        description = mod.get("description", "Working memory module.")
        rwi_entries.append(f"- {mod_id}: [{begin_tag}]...[{end_tag}] {description}")

    rwi_body = "\n\n".join(rwi_entries)
    full_rwi_content = f"{preamble}\n\nActive Delta Modules:\n{rwi_body}"

    rwi_block = (
        f"{DELTA_RWI_START_TAG}\n"
        f"{full_rwi_content}\n"
        f"{DELTA_RWI_END_TAG}"
    )

    manifest_parts = [rwi_block]

    # Build individual module blocks
    for mod in active_modules:
        filename = mod.get("file", "")
        source_path = SOURCES_DIR / filename if filename else None
        content = ""
        if source_path and source_path.exists():
            try:
                content = source_path.read_text(encoding="utf-8").strip()
            except OSError as e:
                print(f"[DeltaService] Error reading source {source_path}: {e}")

        mod_id = mod.get("id", "")
        begin_tag = mod.get("begin_bracket", f"###{mod_id.upper()}_START###")
        end_tag = mod.get("end_bracket", f"###{mod_id.upper()}_END###")

        if content:
            formatted_block = f"{begin_tag}\n{content}\n{end_tag}"
            manifest_parts.append(formatted_block)

    # Wrap the entire Layer 2 output in top-level delta boundary tags
    inner_manifest = "\n\n".join(manifest_parts)
    full_compiled_manifest = f"{DELTAS_START_TAG}\n{inner_manifest}\n{DELTAS_END_TAG}"

    try:
        MANIFEST_PATH.write_text(full_compiled_manifest, encoding="utf-8")
        print(f"[DeltaService] Compiled delta manifest ({len(full_compiled_manifest)} chars) to {MANIFEST_PATH}")
    except OSError as e:
        print(f"[DeltaService] Error writing compiled manifest: {e}")
        raise e

    return full_compiled_manifest

def update_delta_source(block_id_or_file: str, content: str, recompile: bool = True) -> Dict[str, Any]:
    """
    Programmatic update hook to write or overwrite raw text in a target delta
    source file (e.g. input_delta.txt), with optional recompilation.
    """
    ensure_directories()
    modules = load_config()

    target_mod = None
    target_filename = None

    for mod in modules:
        if mod.get("id") == block_id_or_file or mod.get("file") == block_id_or_file or mod.get("name") == block_id_or_file:
            target_mod = mod
            target_filename = mod.get("file")
            break

    if not target_filename:
        # If not matched to existing registered module, treat as filename directly
        target_filename = os.path.basename(block_id_or_file)
        if not target_filename.endswith(".txt"):
            target_filename += ".txt"

    target_path = SOURCES_DIR / target_filename
    target_path.write_text(content, encoding="utf-8")

    compiled_text = ""
    if recompile:
        compiled_text = compile_manifest()

    return {
        "success": True,
        "block_id": target_mod.get("id") if target_mod else None,
        "file": target_filename,
        "path": str(target_path),
        "bytes_written": len(content.encode("utf-8")),
        "recompiled": recompile,
        "manifest_size": len(compiled_text) if recompile else None
    }

def get_compiled_manifest() -> str:
    """Reads and returns the compiled manifest text from disk."""
    if MANIFEST_PATH.exists():
        try:
            return MANIFEST_PATH.read_text(encoding="utf-8")
        except OSError:
            return ""
    return ""
