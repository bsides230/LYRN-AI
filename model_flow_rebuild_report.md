# Model Flow Rebuild Report

## A. OLD FLOW SUMMARY

### What the old/current flow was doing

1. User sends chat message via POST `/api/chat`
2. `chat_endpoint()` saves user message to a **dynamic snapshot** (`automation/dynamic_snapshots/jobs/chat_input_context.txt`) and queues `chat_input_job`
3. Scheduler picks up `chat_input_job`, runs `route_chat.py` which queues `chat_response_job`
4. Scheduler picks up `chat_response_job`, runs `spawn_chat_watcher.py` (spawns background watcher)
5. Scheduler calls `trigger_chat_generation(job.prompt, folder="jobs")` — **job instructions** are written to `jobs/job_model_output.txt` in format `user\n{instructions}\n`
6. Model runner detects trigger, reads `jobs/job_model_output.txt`, builds context, generates response
7. Model runner **appends** raw output to the **same file** as the input
8. Background watcher reads `jobs/job_model_output.txt`, tries to extract response using `##Response_START##` / `##Response_END##` markers
9. Watcher writes extracted response to `chat/chat_*.txt`
10. Chat UI polls `/api/chat/status`, then fetches `/api/chat/history` which reads from `chat/` dir

### Where it was broken

1. **Model saw job instructions as user message, not actual user text.** `trigger_chat_generation(job.prompt)` wrote the chat_response_job instructions ("You are processing a user's chat input...") as the `user` turn. The real user text was buried in a dynamic snapshot system message. This meant the model's "user" turn was meta-instructions, not what the person actually typed.

2. **No input/output separation.** Raw model output was appended to the same file that held the input (`jobs/job_model_output.txt`). This co-mingled input and output in a single file, making extraction fragile.

3. **Marker-based extraction was unreliable.** The job instructions asked the model to wrap output in `##Response_START##`/`##Response_END##` markers. Small or non-instruction-following models often did not comply. The fallback (`content.strip()`) grabbed the **entire file** including the `user\n{instructions}` prefix, meaning the "response" shown to the user included the job instructions text.

4. **Double-hop indirection.** The user message traveled: dynamic snapshot → system message → model sees it as context → model must "read" it from context. This was an unnecessarily fragile indirection when the user message should have simply been the user turn.

---

## B. REFERENCE RUNNER ANALYSIS

### What the deprecated model runner did right
- Clean trigger-based execution loop (watch → read → process → write → idle)
- Proper context assembly: system prompt → history → deltas → user message
- Stderr capture for llama.cpp metrics
- Thread-safe model lock
- Settings reload on each trigger

### What was reused
- The overall trigger-based architecture (trigger file → model runner → status flags)
- Context assembly order (system prompt → dynamic snapshots → history → deltas → user message)
- Stderr capture and metrics parsing logic (unchanged)
- Model loading with `use_mlock=True`, `use_mmap=False` (unchanged)
- Rebuild trigger handling (unchanged)

### What was NOT reused
- The deprecated runner did not have DSManager support — the current runner's DSManager integration was kept
- The deprecated runner wrote output to the same input file — this behavior was **intentionally not restored** as it was the core architectural problem

---

## C. NEW FLOW DESIGN

### Exact new input/output flow

```
User types message
       │
       ▼
POST /api/chat
       │
       ├─ Writes jobs/job_input.json  ← { user_message, source: "chat", timestamp }
       ├─ Creates global_flags/chat_processing.txt lock
       └─ Queues chat_input_job
       │
       ▼
Scheduler picks up chat_input_job
       │
       └─ Runs route_chat.py → queues chat_response_job
       │
       ▼
Scheduler picks up chat_response_job
       │
       ├─ Runs spawn_chat_watcher.py → spawns chat_watcher_bg.py (background)
       │
       └─ Calls trigger_chat_generation(job.prompt, folder="jobs")
          │
          ├─ Reads existing jobs/job_input.json (has user_message from chat_endpoint)
          ├─ Merges job_instructions into payload
          ├─ Writes updated jobs/job_input.json
          ├─ Clears jobs/job_raw_output.txt (stale output)
          └─ Writes chat_trigger.txt → path to jobs/job_input.json
       │
       ▼
Model Runner detects chat_trigger.txt
       │
       ├─ Reads jobs/job_input.json → { user_message, job_instructions, source }
       ├─ Builds message context:
       │    [system] Master prompt
       │    [system] Dynamic snapshots
       │    [user/assistant...] Chat history
       │    [system] Deltas
       │    [system] Job instructions (for chat source only)
       │    [user] Actual user message  ← THE USER'S REAL TEXT
       │
       ├─ Generates response via LLM
       └─ Streams raw output to jobs/job_raw_output.txt  ← SEPARATE FROM INPUT
       │
       ▼
chat_watcher_bg.py (background, running in parallel)
       │
       ├─ Polls jobs/job_raw_output.txt
       ├─ Waits for llm_status == "idle"
       ├─ Reads raw output
       ├─ Extracts response (marker-based or full text)
       ├─ Reads user message from jobs/job_input.json
       ├─ Writes chat/chat_{timestamp}.txt ← user\n{input}\n\nmodel\n{response}
       ├─ Removes global_flags/chat_processing.txt lock
       └─ Exits
       │
       ▼
Chat UI polls /api/chat/status → processing: false
       │
       ├─ Fetches /api/chat/history → reads from chat/ directory
       └─ Displays captured response only
```

### Exact file responsibilities

| File | Responsibility |
|------|---------------|
| `start_lyrn.py` : `chat_endpoint()` | Writes structured input to `jobs/job_input.json`, creates lock, queues job |
| `start_lyrn.py` : `trigger_chat_generation()` | Merges job instructions into input payload, clears stale output, writes trigger |
| `start_lyrn.py` : `scheduler_loop()` | Orchestrates job execution (scripts → trigger), unchanged role |
| `model_runner.py` : `_read_input_payload()` | Reads structured JSON or legacy text input |
| `model_runner.py` : `process_request()` | Builds context, generates, writes raw output to `jobs/job_raw_output.txt` |
| `chat_watcher_bg.py` | Capture layer: waits for generation, extracts response, writes to `chat/` |
| `chat_manager.py` | Reads chat history from `chat/` dir for LLM context and UI display |
| Chat Interface HTML | Polls status, fetches history from `/api/chat/history`, displays only captured output |

---

## D. CHANGED FILES

### `model_runner.py`
- **Added** `_read_input_payload()` — reads structured JSON or legacy text input format
- **Added** `_resolve_raw_output_path()` — determines where to write raw output
- **Rewritten** `process_request()` — reads from structured input, writes raw output to separate intermediate file, correctly places user message as user turn (not job instructions)
- **Removed** behavior of appending to input file
- **Removed** dependency on `user\n{message}` format for jobs

### `start_lyrn.py`
- **Rewritten** `trigger_chat_generation()` — for jobs folder: reads/merges JSON input payload, clears stale output, triggers model runner
- **Rewritten** `chat_endpoint()` — writes structured `jobs/job_input.json` with user message instead of saving to dynamic snapshot
- **Rewritten** `_monitor_job_completion()` — monitors `jobs/job_raw_output.txt` instead of old `job_model_output.txt`
- **Removed** dynamic snapshot save/activate for chat input context

### `automation/job_scripts/chat_watcher_bg.py`
- **Full rewrite** — reads from `jobs/job_raw_output.txt` (separate intermediate file), reads user input from `jobs/job_input.json`, maintains marker extraction with clean fallback
- **Added** `get_input_from_json()` — reads user message from structured input
- **Added** `extract_response()` — clean extraction with marker support and full-text fallback
- **Removed** dependency on `##Response_START##`/`##Response_END##` markers for correct operation

### `automation/jobs/jobs.json`
- **Changed** `chat_response_job.instructions` — removed mandatory marker requirement, simplified to natural response guidance

---

## E. VALIDATION RESULTS

### Chat job flow still works
- YES: chat_endpoint → chat_input_job → route_chat.py → chat_response_job → spawn_chat_watcher.py → trigger → model_runner → watcher → chat history. Flow is preserved.

### Model runner input is corrected
- YES: Model runner now reads `jobs/job_input.json` which contains `user_message` (the actual user text) as a structured field. For chat source, the user message becomes the `user` turn in the LLM context. Job instructions are placed as a system message, not the user turn.

### Output capture works
- YES: Model runner writes raw output to `jobs/job_raw_output.txt` (separate from input). Watcher reads this file, extracts response, writes to `chat/chat_*.txt`. No input text is mixed into the response.

### Chat now displays only captured response
- YES: Chat UI reads from `/api/chat/history` which reads from `chat/` directory. Chat files are written exclusively by the capture layer (watcher). There is no direct-response display path bypassing the capture layer.

---

## F. REMAINING RISKS

1. **Marker extraction still optional.** If the model generates `##Response_START##`/`##Response_END##` markers (e.g., from prompt conditioning or habit), they are extracted cleanly. If not, the full raw output is used. This is now safe because raw output contains ONLY model text (no input mixed in).

2. **Legacy text-format trigger path.** The model runner still supports the old `user\n{message}` text format for backward compatibility with any non-job triggers. This path works but does not benefit from input/output separation for non-jobs folder files.

3. **Race condition window.** Between the watcher spawning and the model runner writing the raw output file, there is a brief window. The watcher handles this by polling with a 1-second interval and checking LLM status before reading.

4. **Single job concurrency.** The `chat_processing.txt` lock prevents concurrent chat jobs. This is unchanged and intentional.

5. **No streaming to UI.** The chat UI does not see tokens as they are generated — it waits for the full response via the capture layer. This is by design (decoupled architecture) but means no real-time streaming display.
