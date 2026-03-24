"""
chat_watcher_bg.py - Background chat output watcher with affordance support.

Runs as a detached background process spawned by spawn_chat_watcher.py.
Responsibilities:
  1. Wait for the raw output file to appear (model started generating).
  2. Tail the file in real-time, scanning for affordance markers.
     - Thinking blocks (<think>...</think>) are EXCLUDED from affordance detection.
       The wizard only triggers on regular (non-thinking) output.
  3. When ##AF: FINAL_OUTPUT## is detected in non-thinking text:
       - Set global_flags/final_output_mode.txt
       - Write subsequent tokens (post-marker, thinking stripped) to
         global_flags/chat_stream_buffer.txt so the SSE endpoint can forward
         them live to the chat module.
  4. Once LLM status returns to idle/stopped/error:
       - Extract the final response (post-marker content, thinking stripped).
       - Save user/model pair to chat history (for LLM context).
       - Save clean chat pair to output_history/ (audit log, never seen by LLM).
       - Clean up all processing flags.

Affordance marker: ##AF: FINAL_OUTPUT##
Thinking tags:     <think>...</think>  — excluded from wizard + final output
"""

import sys
import os
import time
import re
import json
from pathlib import Path


AFFORDANCE_START     = "##AF: FINAL_OUTPUT##"
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


def _strip_thinking(text: str) -> str:
    """Remove all <think>...</think> blocks from text (case-insensitive tags)."""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)


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
      1. Content after ##AF: FINAL_OUTPUT## (thinking stripped from both sides)
      2. Content between ##Response_START## / ##Response_END## (legacy markers)
      3. Full raw output, thinking stripped, as last-resort fallback

    Thinking blocks (<think>...</think>) are always removed from the result
    before it is saved to chat history or shown to the user.
    """
    raw_text = raw_text.strip()
    if not raw_text:
        return None

    # 1. Affordance-based extraction
    if AFFORDANCE_START in raw_text:
        after = raw_text.split(AFFORDANCE_START, 1)[1]
        # Strip thinking from final output — model may still think after the marker
        after = _strip_thinking(after).strip()
        if after:
            print("[Watcher] Extracted response using AFFORDANCE marker (thinking stripped).")
            return after

    # 2. Legacy marker extraction
    start_m = "##Response_START##"
    end_m   = "##Response_END##"
    if start_m in raw_text and end_m in raw_text:
        match = re.search(f"{start_m}(.*?){end_m}", raw_text, re.DOTALL)
        if match:
            extracted = _strip_thinking(match.group(1)).strip()
            if extracted:
                print("[Watcher] Extracted response using legacy markers (thinking stripped).")
                return extracted

    # 3. Fallback: full raw output with thinking stripped
    clean = _strip_thinking(raw_text).strip()
    if clean:
        print("[Watcher] Using thinking-stripped raw output as response (no markers found).")
        return clean

    # 4. Absolute fallback: raw output as-is
    print("[Watcher] Using full raw output as response (thinking strip yielded nothing).")
    return raw_text.strip()


def _save_chat_history(root_dir: str, user_input: str, model_response: str):
    """
    Write the user/model exchange to a timestamped file in chat/.
    This file IS read by the LLM as conversation context on future turns.
    """
    try:
        chat_dir = os.path.join(root_dir, "chat")
        os.makedirs(chat_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S_") + str(int(time.time() * 1000) % 1000)
        filepath = os.path.join(chat_dir, f"chat_{timestamp}.txt")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"user\n{user_input}\n\nmodel\n{model_response}\n")
        print(f"[Watcher] Saved chat history to {filepath}")
    except Exception as e:
        print(f"[Watcher] Error saving chat history: {e}")


def _save_output_history(root_dir: str, user_message: str, response: str):
    """
    Write a clean chat pair to output_history/ as a user-visible audit log.
    This folder is NEVER read by the LLM and NEVER cleared by chat history operations.
    Each file contains one complete exchange: the user's message + the clean final response.
    """
    try:
        hist_dir = os.path.join(root_dir, "output_history")
        os.makedirs(hist_dir, exist_ok=True)
        timestamp = time.strftime("%Y-%m-%dT%H-%M-%S") + f"_{int(time.time() * 1000) % 1000:03d}"
        filepath = os.path.join(hist_dir, f"{timestamp}.json")
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "user_message": user_message,
            "response": response,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(entry, f, indent=2, ensure_ascii=False)
        print(f"[Watcher] Saved output history to {filepath}")
    except Exception as e:
        print(f"[Watcher] Error saving output history: {e}")


def _append_output_log(root_dir: str, user_message: str, raw_output: str,
                       final_output: str, marker_detected: bool):
    """Append one generation record to global_flags/output_log.jsonl (legacy log)."""
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

    # spawn_chat_watcher.py now clears any stale final_output_mode.txt before
    # spawning us, so flag_was_preset should always be False for normal chat flow.
    # We keep the check for safety (e.g. direct invocations or edge cases).
    flag_was_preset = os.path.exists(final_output_flag)
    print(f"[Watcher] Phase 1: final_output_mode.txt pre-set: {flag_was_preset}")

    # Clear stale stream buffer; always clear the flag too (spawn clears it, but be safe).
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
    char_pos        = 0               # character offset read so far
    in_final_output = flag_was_preset  # already live if flag was pre-set

    # Two-phase mode: runner sets final_output_flag BEFORE creating raw_output_file,
    # so re-check here — the flag may have been set after our Phase 1 startup check.
    if not in_final_output and os.path.exists(final_output_flag):
        in_final_output = True
        print("[Watcher] Phase 2 start: Final output flag set by runner — entering streaming mode.")
    total_chars_read    = 0
    total_buffer_chars  = 0
    poll_count = 0

    while True:
        elapsed = time.time() - global_start
        if elapsed > TIMEOUT_GENERATION:
            print(f"[Watcher] Phase 2: TIMED OUT after {elapsed:.1f}s during generation monitoring.")
            break

        poll_count += 1

        # --- Read new content from file (by character position) ---
        new_content = ""
        full = ""
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

        # Defensive mid-loop check: catch external flag set by runner (two-phase mode)
        if not in_final_output and os.path.exists(final_output_flag):
            in_final_output = True
            print("[Watcher] Phase 2: External final output flag detected mid-loop — switching to streaming mode.")
            # Stream all content read so far to the buffer (it's all final output in two-phase)
            if full:
                clean_full = _strip_thinking(full)
                if clean_full:
                    _append_stream_buffer(stream_buffer, clean_full)
                    total_buffer_chars += len(clean_full)
                    print(f"[Watcher] Phase 2: Streamed {len(clean_full)} existing chars to buffer.")

        if new_content:
            print(f"[Watcher] Phase 2: +{len(new_content)} chars (total={total_chars_read}, "
                  f"in_final_output={in_final_output})")
            if not in_final_output:
                # Strip thinking blocks BEFORE checking for the affordance marker.
                # The wizard should not trigger on markers embedded in thinking text.
                text_for_detection = _strip_thinking(full)

                if AFFORDANCE_START in text_for_detection:
                    # Find marker position in the stripped text to locate context
                    marker_pos = text_for_detection.index(AFFORDANCE_START)
                    print(f"[Watcher] Phase 2: ##AF: FINAL_OUTPUT## detected (non-thinking) at "
                          f"stripped-char {marker_pos} — switching to final output mode.")
                    in_final_output = True

                    # Set the final output mode flag file
                    try:
                        os.makedirs(os.path.dirname(final_output_flag), exist_ok=True)
                        with open(final_output_flag, "w", encoding="utf-8") as f:
                            f.write("active")
                        print(f"[Watcher] Phase 2: final_output_mode.txt written")
                    except Exception as e:
                        print(f"[Watcher] Phase 2: ERROR setting final_output_mode flag: {e}")

                    # Write content after the marker to the stream buffer.
                    # Strip thinking from streamed content too (post-marker thinking
                    # should not be visible live in the chat module).
                    after_marker = text_for_detection.split(AFFORDANCE_START, 1)[1]
                    after_clean  = _strip_thinking(after_marker)
                    if after_clean:
                        _append_stream_buffer(stream_buffer, after_clean)
                        total_buffer_chars += len(after_clean)
                        print(f"[Watcher] Phase 2: Wrote {len(after_clean)} post-marker chars to stream buffer")
                    else:
                        print(f"[Watcher] Phase 2: No post-marker content yet — waiting for more tokens")

            else:
                # Already past the marker — stream new content (thinking stripped) to buffer
                clean_new = _strip_thinking(new_content)
                if clean_new:
                    _append_stream_buffer(stream_buffer, clean_new)
                    total_buffer_chars += len(clean_new)

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
    # Phase 3: LLM done — extract final response and save history
    # -----------------------------------------------------------------------
    print(f"[Watcher] Phase 3: Reading final raw output from {raw_output_file}")
    try:
        with open(raw_output_file, "r", encoding="utf-8", errors="replace") as f:
            full_raw = f.read()
        print(f"[Watcher] Phase 3: Raw output length: {len(full_raw)} chars")
    except Exception as e:
        print(f"[Watcher] Phase 3: ERROR reading final output: {e}")
        full_raw = ""

    # ── Two-phase: read phase 1 thinking content saved by the runner ──────────
    last_thinking_file = os.path.join(root_dir, "global_flags", "last_thinking.txt")
    phase1_content = ""
    if os.path.exists(last_thinking_file):
        try:
            with open(last_thinking_file, "r", encoding="utf-8") as f:
                phase1_content = f.read()
            os.remove(last_thinking_file)
            print(f"[Watcher] Phase 3: Read {len(phase1_content)} chars of phase 1 from last_thinking.txt")
        except Exception as e:
            print(f"[Watcher] Phase 3: Error reading last_thinking.txt: {e}")
    else:
        print(f"[Watcher] Phase 3: last_thinking.txt not found (single-phase or fallback mode)")

    # In two-phase mode full_raw = phase 2 response only (no marker).
    # Strip any <think> tags from phase 2 (in case model thinks again) for chat history.
    response_text = _strip_thinking(full_raw).strip()
    if not response_text:
        # Fallback: try legacy marker extraction
        response_text = _extract_final_response(full_raw)

    marker_in_log = bool(phase1_content)  # marker is in phase 1 content when two-phase
    if not marker_in_log:
        # Fallback: check phase 2 raw (single-phase compatibility)
        marker_in_log = AFFORDANCE_START in full_raw

    print(f"[Watcher] Phase 3: Response length: {len(response_text) if response_text else 0} chars")
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
        # Save to LLM chat history (chat/ folder — read by model on future turns).
        # Only save the clean response; thinking stays out of LLM context.
        _save_chat_history(root_dir, user_input, response_text)

        # Save to user-visible output history (audit log, never read by LLM)
        _save_output_history(root_dir, user_input, response_text)
    else:
        print("[Watcher] Phase 3: No response text extracted — skipping history saves.")

    # Build combined raw for Output Viewer history tab:
    # phase 1 thinking + marker + phase 2 response (shows full picture with thinking)
    if phase1_content:
        combined_raw = phase1_content.rstrip() + "\n\n" + AFFORDANCE_START + "\n\n" + (response_text or full_raw)
    else:
        combined_raw = full_raw  # single-phase fallback

    # Write to output log (used by Output Viewer history tab)
    log_path = os.path.join(root_dir, "global_flags", "output_log.jsonl")
    print(f"[Watcher] Phase 3: Appending to output log: {log_path}")
    _append_output_log(
        root_dir,
        user_message=user_input,
        raw_output=combined_raw,
        final_output=response_text or "",
        marker_detected=marker_in_log,
    )

    # Clean up ALL processing flags — always delete final_output_mode.txt regardless
    # of flag_was_preset so the next generation always starts clean.
    print(f"[Watcher] Phase 3: Cleaning up flags: chat_processing.txt, final_output_mode.txt")
    _cleanup_flags(lock_file, final_output_flag)

    elapsed_total = time.time() - global_start
    print(f"[Watcher] === Capture complete in {elapsed_total:.2f}s. Exiting. ===")
    sys.exit(0)


if __name__ == "__main__":
    main()
