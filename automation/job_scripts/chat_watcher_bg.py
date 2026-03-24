"""
chat_watcher_bg.py - Background chat output watcher with affordance support.

Runs as a detached background process spawned by spawn_chat_watcher.py.
Responsibilities:
  1. Wait for the raw output file to appear (model started generating).
  2. Tail the file in real-time, scanning for affordance markers.
  3. When ##AFFORDANCE: FINAL_OUTPUT_START## is detected:
       - Set global_flags/final_output_mode.txt
       - Write subsequent tokens to global_flags/chat_stream_buffer.txt
         so the SSE endpoint can forward them live to the chat module.
  4. Once LLM status returns to idle/stopped/error:
       - Extract the final response (content after the affordance marker,
         or full output as fallback).
       - Save user/model pair to chat history using the user_message
         captured at spawn time (prevents race-condition with job_input.json).
       - Clean up all processing flags.

Affordance marker: ##AFFORDANCE: FINAL_OUTPUT_START##
"""

import sys
import os
import time
import re
import json
from pathlib import Path


AFFORDANCE_START = "##AF: FINAL_OUTPUT##"
POLL_INTERVAL_STREAM = 0.1   # seconds between read ticks while streaming
POLL_INTERVAL_WAIT   = 0.5   # seconds between ticks while waiting for file to appear
TIMEOUT_WAIT_FILE    = 300   # 5 min: max wait for raw output file to appear
TIMEOUT_GENERATION   = 1800  # 30 min: max total generation time


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_llm_status(llm_status_path: str) -> str:
    try:
        with open(llm_status_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return "idle"  # assume done if unreadable


def _append_stream_buffer(stream_buffer_file: str, content: str):
    """Append tokens to the live chat stream buffer."""
    try:
        os.makedirs(os.path.dirname(stream_buffer_file), exist_ok=True)
        with open(stream_buffer_file, "a", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        print(f"[Watcher] Error writing to stream buffer: {e}")


def _extract_final_response(raw_text: str) -> str | None:
    """
    Extract the user-visible response from raw model output.

    Priority:
      1. Content after ##AFFORDANCE: FINAL_OUTPUT_START## (new affordance protocol)
      2. Content between ##Response_START## / ##Response_END## (legacy markers)
      3. Full raw output as last-resort fallback
    """
    raw_text = raw_text.strip()
    if not raw_text:
        return None

    # 1. Affordance-based extraction
    if AFFORDANCE_START in raw_text:
        after = raw_text.split(AFFORDANCE_START, 1)[1].strip()
        if after:
            print("[Watcher] Extracted response using AFFORDANCE marker.")
            return after

    # 2. Legacy marker extraction
    start_m = "##Response_START##"
    end_m   = "##Response_END##"
    if start_m in raw_text and end_m in raw_text:
        match = re.search(f"{start_m}(.*?){end_m}", raw_text, re.DOTALL)
        if match:
            extracted = match.group(1).strip()
            if extracted:
                print("[Watcher] Extracted response using legacy markers.")
                return extracted

    # 3. Fallback: full raw output
    print("[Watcher] Using full raw output as response (no markers found).")
    return raw_text


def _save_chat_history(root_dir: str, user_input: str, model_response: str):
    """Write the user/model exchange to a timestamped chat history file."""
    try:
        chat_dir = os.path.join(root_dir, "chat")
        os.makedirs(chat_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S_") + str(int(time.time() * 1000) % 1000)
        filepath = os.path.join(chat_dir, f"chat_{timestamp}.txt")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"user\n{user_input}\n\nmodel\n{model_response}\n")
        print(f"[Watcher] Saved chat response to {filepath}")
    except Exception as e:
        print(f"[Watcher] Error saving chat history: {e}")


def _append_output_log(root_dir: str, user_message: str, raw_output: str,
                       final_output: str, marker_detected: bool):
    """Append one generation record to global_flags/output_log.jsonl."""
    MAX_ENTRIES = 100
    try:
        log_path = os.path.join(root_dir, "global_flags", "output_log.jsonl")
        entry = json.dumps({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "user_message": user_message,
            "raw_output": raw_output,
            "final_output": final_output or "",
            "marker_detected": marker_detected,
        })
        # Read existing lines, append, trim to MAX_ENTRIES
        lines = []
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                lines = [l for l in f.read().splitlines() if l.strip()]
        lines.append(entry)
        if len(lines) > MAX_ENTRIES:
            lines = lines[-MAX_ENTRIES:]
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception as e:
        print(f"[Watcher] Error writing output log: {e}")


def _get_user_message_from_json(root_dir: str) -> str | None:
    """Fallback: read user_message from job_input.json (may be stale)."""
    try:
        path = os.path.join(root_dir, "jobs", "job_input.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("user_message", "").strip() or None
    except Exception as e:
        print(f"[Watcher] Error reading job_input.json: {e}")
    return None


def _cleanup_flags(*flag_paths):
    for path in flag_paths:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception as e:
            print(f"[Watcher] Error clearing flag {path}: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("[Watcher] Missing root directory argument.")
        sys.exit(1)

    root_dir = sys.argv[1]

    # User message captured at spawn time to avoid the race condition where
    # job_input.json is overwritten before the watcher reads it.
    user_message_arg = sys.argv[2] if len(sys.argv) > 2 else None

    raw_output_file  = os.path.join(root_dir, "jobs", "job_raw_output.txt")
    lock_file        = os.path.join(root_dir, "global_flags", "chat_processing.txt")
    llm_status_path  = os.path.join(root_dir, "global_flags", "llm_status.txt")
    final_output_flag= os.path.join(root_dir, "global_flags", "final_output_mode.txt")
    stream_buffer    = os.path.join(root_dir, "global_flags", "chat_stream_buffer.txt")

    print(f"[Watcher] === chat_watcher_bg.py starting ===")
    print(f"[Watcher] PID: {os.getpid()}")
    print(f"[Watcher] root_dir:          {root_dir}")
    print(f"[Watcher] raw_output_file:   {raw_output_file}")
    print(f"[Watcher] lock_file:         {lock_file}")
    print(f"[Watcher] llm_status_path:   {llm_status_path}")
    print(f"[Watcher] final_output_flag: {final_output_flag}")
    print(f"[Watcher] stream_buffer:     {stream_buffer}")
    print(f"[Watcher] user_message_arg:  {repr(user_message_arg[:60]) if user_message_arg else None}")
    print(f"[Watcher] affordance_marker: {repr(AFFORDANCE_START)}")
    print(f"[Watcher] Watching {raw_output_file} for raw model output...")

    global_start = time.time()

    # -----------------------------------------------------------------------
    # Phase 1: Wait for the raw output file to appear
    # -----------------------------------------------------------------------
    print(f"[Watcher] Phase 1: Waiting for output file to appear (timeout={TIMEOUT_WAIT_FILE}s)...")
    wait_ticks = 0
    while not os.path.exists(raw_output_file):
        elapsed = time.time() - global_start
        if elapsed > TIMEOUT_WAIT_FILE:
            print(f"[Watcher] Phase 1: TIMED OUT after {elapsed:.1f}s waiting for output file.")
            _cleanup_flags(lock_file)
            sys.exit(1)
        wait_ticks += 1
        if wait_ticks % 10 == 0:  # log every ~5s
            print(f"[Watcher] Phase 1: Still waiting... {elapsed:.1f}s elapsed")
        time.sleep(POLL_INTERVAL_WAIT)

    print(f"[Watcher] Phase 1: Output file appeared after {time.time()-global_start:.2f}s")

    # Check if a previous generation already set the flag (recursion scenario).
    # If so, this generation is the "final output" generation — stream everything
    # from the start without waiting for the marker.
    flag_was_preset = os.path.exists(final_output_flag)
    print(f"[Watcher] Phase 1: final_output_mode.txt pre-set: {flag_was_preset}")

    # Clear stale stream buffer, but do NOT clear the flag if it was already set —
    # that means a previous job set it and we should honour it.
    _cleanup_flags(stream_buffer)
    if not flag_was_preset:
        _cleanup_flags(final_output_flag)

    if flag_was_preset:
        print("[Watcher] FINAL OUTPUT flag was pre-set — streaming everything from start.")
    else:
        print("[Watcher] Output file detected. Starting real-time affordance monitoring...")

    # -----------------------------------------------------------------------
    # Phase 2: Tail the file, detect affordance marker, stream to buffer
    # -----------------------------------------------------------------------
    print(f"[Watcher] Phase 2: Starting tail loop (poll={POLL_INTERVAL_STREAM}s, timeout={TIMEOUT_GENERATION}s)")
    char_pos       = 0               # character offset read so far
    in_final_output= flag_was_preset  # already live if flag was pre-set
    total_chars_read = 0
    total_buffer_chars = 0
    poll_count = 0

    while True:
        elapsed = time.time() - global_start
        if elapsed > TIMEOUT_GENERATION:
            print(f"[Watcher] Phase 2: TIMED OUT after {elapsed:.1f}s during generation monitoring.")
            break

        poll_count += 1

        # --- Read new content from file (by character position) ---
        new_content = ""
        try:
            with open(raw_output_file, "r", encoding="utf-8", errors="replace") as f:
                full = f.read()
            if len(full) > char_pos:
                new_content = full[char_pos:]
                char_pos = len(full)
                total_chars_read += len(new_content)
        except Exception as e:
            if poll_count == 1:
                print(f"[Watcher] Phase 2: Error reading output file: {e}")

        if new_content:
            print(f"[Watcher] Phase 2: +{len(new_content)} chars (total={total_chars_read}, "
                  f"in_final_output={in_final_output})")
            if not in_final_output:
                # Combine with already-read content to catch marker split across reads.
                # We only need the tail of what we've seen to check for the marker.
                # Build a look-back window: last (len(AFFORDANCE_START)-1) chars + new
                # The simplest approach: re-check full content for the marker once we
                # have the full text up to char_pos.
                current_full = full  # still in scope from the read above
                if AFFORDANCE_START in current_full:
                    marker_pos = current_full.index(AFFORDANCE_START)
                    print(f"[Watcher] Phase 2: ##AF: FINAL_OUTPUT## detected at char {marker_pos} "
                          f"— switching to final output mode.")
                    in_final_output = True

                    # Set the final output mode flag file
                    try:
                        os.makedirs(os.path.dirname(final_output_flag), exist_ok=True)
                        with open(final_output_flag, "w", encoding="utf-8") as f:
                            f.write("active")
                        print(f"[Watcher] Phase 2: final_output_mode.txt written")
                    except Exception as e:
                        print(f"[Watcher] Phase 2: ERROR setting final_output_mode flag: {e}")

                    # Write everything after the marker to the stream buffer
                    after_marker = current_full.split(AFFORDANCE_START, 1)[1]
                    if after_marker:
                        _append_stream_buffer(stream_buffer, after_marker)
                        total_buffer_chars += len(after_marker)
                        print(f"[Watcher] Phase 2: Wrote {len(after_marker)} post-marker chars to stream buffer")
                    else:
                        print(f"[Watcher] Phase 2: No post-marker content yet — waiting for more tokens")

            else:
                # Already past the marker — stream new content directly to buffer
                _append_stream_buffer(stream_buffer, new_content)
                total_buffer_chars += len(new_content)

        # --- Check if LLM has finished ---
        status = _read_llm_status(llm_status_path)
        if status in ("idle", "error", "stopped"):
            # Give a short grace period for any final token flushes
            print(f"[Watcher] Phase 2: LLM status='{status}' — generation complete. "
                  f"Total chars read={total_chars_read}, buffer chars={total_buffer_chars}")
            time.sleep(0.3)
            break

        time.sleep(POLL_INTERVAL_STREAM)

    # -----------------------------------------------------------------------
    # Phase 3: LLM done — extract final response and save chat history
    # -----------------------------------------------------------------------
    print(f"[Watcher] Phase 3: Reading final raw output from {raw_output_file}")
    try:
        with open(raw_output_file, "r", encoding="utf-8", errors="replace") as f:
            full_raw = f.read()
        print(f"[Watcher] Phase 3: Raw output length: {len(full_raw)} chars")
    except Exception as e:
        print(f"[Watcher] Phase 3: ERROR reading final output: {e}")
        full_raw = ""

    marker_in_raw = AFFORDANCE_START in full_raw
    print(f"[Watcher] Phase 3: Affordance marker in raw output: {marker_in_raw}")
    print(f"[Watcher] Phase 3: Extracting final response...")

    response_text = _extract_final_response(full_raw)
    print(f"[Watcher] Phase 3: Extracted response length: "
          f"{len(response_text) if response_text else 0} chars")
    if response_text:
        print(f"[Watcher] Phase 3: Response preview: {repr(response_text[:80])}")

    # Determine user_input: argv[2] (pre-captured) > job_input.json fallback > sentinel
    if user_message_arg:
        user_input = user_message_arg
        print(f"[Watcher] Phase 3: Using pre-captured user_message from argv ({len(user_input)} chars)")
    else:
        user_input = _get_user_message_from_json(root_dir) or "Unknown Input"
        print(f"[Watcher] Phase 3: Using user_message from job_input.json (argv not set): "
              f"{repr(user_input[:60])}")

    if response_text:
        _save_chat_history(root_dir, user_input, response_text)
    else:
        print("[Watcher] Phase 3: No response text extracted — skipping chat history save.")

    # Write to output log so the Output Viewer module can show the full picture
    log_path = os.path.join(root_dir, "global_flags", "output_log.jsonl")
    print(f"[Watcher] Phase 3: Appending to output log: {log_path}")
    _append_output_log(
        root_dir,
        user_message=user_input,
        raw_output=full_raw,
        final_output=response_text or "",
        marker_detected=marker_in_raw,
    )

    # Clean up all processing flags
    print(f"[Watcher] Phase 3: Cleaning up flags: {os.path.basename(lock_file)}, "
          f"{os.path.basename(final_output_flag)}")
    _cleanup_flags(lock_file, final_output_flag)

    elapsed_total = time.time() - global_start
    print(f"[Watcher] === Capture complete in {elapsed_total:.2f}s. Exiting. ===")
    sys.exit(0)


if __name__ == "__main__":
    main()
