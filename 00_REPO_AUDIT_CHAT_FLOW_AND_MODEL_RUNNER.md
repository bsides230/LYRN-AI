# REPO AUDIT: CHAT FLOW AND MODEL RUNNER

## 1. Executive Summary

This audit assesses the responsibilities and coupling between the frontend chat UI, backend chat router, and the `model_runner.py` inference script to identify hooks for future modular loops (e.g., memory, reflection, affordances).

**Key Findings:**
*   `model_runner.py` is **NOT** pure inference. It is heavily mixed with chat and history logic. It is responsible for assembling prompts (system + context + history + new input), reading chat files, executing model inference, and directly appending the model's output to the chat log file.
*   Chat-pair saving is handled **internally** by the chat framework (`chat_manager.py`) in combination with `model_runner.py` updating the file.
*   Basic I/O mode can currently be approximated by disabling `enable_chat_history` via settings.
*   A clean context injection seam already exists: `global_flags/repo_context.txt` is loaded into the prompt stack before chat history.

## 2. Flow Diagram

```text
Frontend Chat UI (LYRN_v6/modules/Chat Interface.html)
  |
  | (POST /api/chat)
  v
Backend API (routers/chat_router.py -> trigger_chat_generation)
  | (Creates 'chat/chat_*.txt' file with "user\n{msg}\n")
  | (Writes 'chat_trigger.txt' containing the filepath)
  v
Background Worker (model_runner.py loop)
  | (Detects 'chat_trigger.txt', reads user msg)
  |
  v
Prompt/Context Assembly (model_runner.py -> process_request)
  | (Loads Snapshot/System Prompt via snapshot_loader.py)
  | (Injects 'global_flags/repo_context.txt' if exists)
  | (Loads history via chat_manager.py)
  | (Injects deltas via delta_manager.py)
  |
  v
Model Inference (model_runner.py calls llama_cpp.Llama)
  |
  v
Response Handling / Chat Save (model_runner.py)
  | (Appends "\n\nmodel\n{text}" to 'chat/chat_*.txt' during stream)
  |
  v
Frontend Response (routers/chat_router.py)
  | (Tails the 'chat/chat_*.txt' file and streams via SSE/NDJSON back to UI)
```

## 3. Detailed Findings

### 1. Chat input flow
*   **Where does user chat input enter the system?** `LYRN_v6/modules/Chat Interface.html` text area.
*   **Which frontend component sends it?** Javascript fetch call in `Chat Interface.html` (line 345+).
*   **Which backend API route receives it?** `POST /api/chat` in `routers/chat_router.py`.
*   **What payload structure is used?** `ChatRequest` containing a `message` string (`models/schemas.py`).
*   **Where is the input validated or transformed?** Minimal transformation; written directly to a new timestamped file by `trigger_chat_generation` in `utils/helpers.py`.

### 2. Model invocation flow
*   **Where is the final model input assembled?** Inside `model_runner.py` (`process_request` function).
*   **What script/function calls the model?** `model_runner.py` directly invokes `llama_cpp.Llama.create_chat_completion`.
*   **How is `model_runner.py` invoked?** It is a long-running background daemon process, likely started by a wrapper or worker service.
*   **Is `model_runner.py` called directly, imported as a module, launched as a subprocess, or used another way?** It runs as an independent script in a `while True` loop waiting for trigger files.
*   **What arguments or payload does it receive?** None via command line. It communicates via the `chat_trigger.txt` file (IPC).
*   **What exact output does it return?** It appends generation text directly into the target `.txt` file and logs metrics to stderr.

### 3. `model_runner.py` responsibilities
*   **Does it only run inference?** No, it manages context, prompt assembly, and file I/O.
*   **Does it assemble chat prompts?** Yes.
*   **Does it manage chat history?** Yes, by calling `chat_manager.get_chat_history_messages`.
*   **Does it save chat pairs?** Yes, by streaming output directly into the triggered chat text file.
*   **Does it truncate chat history?** Delegated to `chat_manager.py`.
*   **Does it inject system/context files?** Yes (e.g. `repo_context.txt`).
*   **Does it manage context window/token limits?** Partly (passes config params to Llama-cpp), but no explicit token-based truncation logic exists before inference.
*   **Does it handle response parsing?** No, dumps raw text.
*   **Does it write logs?** Yes (metrics).
*   **Does it handle model load/unload?** Yes.
*   **Does it expose any reusable functions or is it script-style only?** Mostly script-style/daemon execution (`main` loop and `process_request`).

### 4. Chat-pair saving
*   **Where are chat pairs saved?** In the `chat/` directory (or directory defined in settings).
*   **What file format is used?** Plain text files (`.txt`), one file per request pair usually. Format is `user\n{msg}\n\nmodel\n{resp}`.
*   **What fields are stored?** Raw text content and implicit roles based on separators.
*   **Is there one global chat history or per-session/per-agent history?** Global single directory (`chat/`).
*   **When is a user/assistant pair written?** User is written before trigger; model is appended during inference stream.
*   **Is the pair written before or after model response validation?** During generation. No validation occurs.
*   **What code reads saved chat pairs back into future prompts?** `chat_manager.py` (`get_chat_history_messages()`).

### 5. Chat-pair count / history length management
*   **Is there existing code for limiting how many chat pairs are saved or loaded?** Yes, in `chat_manager.py` (`manage_chat_history_files`).
*   **Is this controlled by config, UI, API, hardcoded constants, or manual file editing?** Configuration value (`chat_history_length` in settings). Available in UI via `Chat Interface.html`.
*   **Where is the limit enforced?** Enforced before loading history.
*   **Is the limit based on pair count, token count, file size, or something else?** Based on file count (number of `.txt` files in `chat/`).
*   **Is old history deleted, ignored, summarized, archived, or truncated?** Old files are explicitly unlinked (deleted).

### 6. Ability to disable chat-pair saving
*   **Is there an existing toggle to turn off saving chat pairs?** No direct "don't save file" toggle (every run saves a file by design to stream to UI). However, `enable_chat_history` prevents loading them.
*   **Is there an API endpoint for this?** Managed via standard config endpoint `/api/config`.
*   **Is there a dashboard control for this?** Yes ("Enable Context/History" checkbox in `Chat Interface.html`).
*   **Is there a config file or environment flag for this?** Yes, `enable_chat_history` in settings.
*   **If no toggle exists, identify the smallest safe place one could be added later.** Modifying `utils/helpers.py` (`trigger_chat_generation`) to support an ephemeral `folder` or modifying `chat_manager.py` to auto-delete after extraction if an `ephemeral` flag is set.
*   **Determine whether LYRN can already operate as basic stateless I/O:** Yes. Disabling `enable_chat_history` creates a stateless input -> output pipeline, although it still accumulates files on disk.

### 7. Context injection flow
*   **Where are system prompts, RWI, snapshots, dynamic snapshots, file-tree injector output, or other context layers assembled?** Inside `model_runner.py`'s `process_request` function.
*   **Is context injected before chat history, after chat history, or inside `model_runner.py`?** Inside `model_runner.py`. Order: Snapshot (System) -> Repo Context -> History -> Deltas -> New Input.
*   **How does the existing file-tree injector connect to the final model input?** The file tree UI compiles to an artifact via `/api/fs/compile`, posts to `/api/fs/inject` which writes `global_flags/repo_context.txt`. `model_runner.py` dynamically loads this file.
*   **What format does injected context use?** Plaintext with basic section headers (`--- FILE: path ---`).
*   **Is there an existing general-purpose injection seam future systems can reuse?** Yes, the `global_flags/repo_context.txt` mechanism is generic and acts as a direct injection vector right after the system prompt.

### 8. Response handling
*   **Where does the model response go after inference?** Written incrementally to the generated text file.
*   **Is it parsed, filtered, validated, streamed, saved, or transformed?** Streamed raw into the file.
*   **What code sends the response back to the dashboard/chat UI?** `routers/chat_router.py` tails the file and streams JSON via a `StreamingResponse`.
*   **Is there any structured-output handling already available?** No native structural enforcement.

### 9. API and dashboard controls
*   **API endpoints:**
    *   sending chat: `POST /api/chat`
    *   loading chat history: `GET /api/chat/history`
    *   clearing chat history: `DELETE /api/chat`
    *   saving chat pairs: Implicit in generation.
    *   configuring chat history length: `POST /api/config`
    *   enabling/disabling context injection: `POST /api/fs/inject`, `DELETE /api/fs/inject`
    *   model runner status: `GET /api/system/status` (via `system_router.py` or worker endpoint)
*   **Frontend/dashboard controls:**
    *   chat history: Chat window in `Chat Interface.html`.
    *   saved pairs: History toggle and limit inputs in Chat Interface.
    *   context injection: `FileTreeViewer.html` module.
    *   model selection: `ModelController.html`.
    *   runner status: `ServerStatus.html` / Dashboard icons.

### 10. Hook-point analysis

#### Hook 1: Injecting world state/memory before model call
*   **File path:** `model_runner.py` / `global_flags/repo_context.txt`
*   **Function/route name:** `process_request`
*   **Why it is a good hook:** Already positioned in the perfect sequence (between system prompt and history).
*   **Risk level:** Low.
*   **What would break:** Excessive tokens will overflow context window if not managed externally.

#### Hook 2: Disabling chat history for basic I/O mode
*   **File path:** `chat_manager.py`
*   **Function/route name:** `get_chat_history_messages`
*   **Why it is a good hook:** Centralized method. Already honors `enable_chat_history`.
*   **Risk level:** Low.
*   **What would break:** UI relying on contextual follow-ups.

#### Hook 3: Capturing model output before it is saved
*   **File path:** `model_runner.py`
*   **Function/route name:** `process_request` (inside the `for token_data in stream:` loop)
*   **Why it is a good hook:** The only place where raw tokens emerge.
*   **Risk level:** High.
*   **What would break:** Breaking the loop or raising errors here interrupts standard UI streaming.

## 4. Responsibility Table

| Responsibility | Current owner | File/path | Notes |
| :--- | :--- | :--- | :--- |
| Chat input | Frontend UI | `LYRN_v6/modules/Chat Interface.html` | Client-side handling |
| Chat Triggering | Chat Router | `routers/chat_router.py` | Creates file, triggers runner |
| Prompt assembly | Model Runner | `model_runner.py` | Heavy responsibility |
| Context injection | Model Runner | `model_runner.py` | Reads from `global_flags/repo_context.txt` |
| Chat history load | Chat Manager | `chat_manager.py` | Called by runner |
| Chat history save | Model Runner | `model_runner.py` | Directly appends to file |
| History length limit | Chat Manager | `chat_manager.py` | Enforced file deletions |
| Model invocation | Model Runner | `model_runner.py` | Uses llama_cpp directly |
| Response parsing | None | None | Raw output stream |
| Response display | Chat UI / Router | `routers/chat_router.py` | Tails file, SSE |
| Logging (metrics) | Model Runner | `model_runner.py` | Parsed from stderr |

## 5. Current limitations / risks
*   **Tight Coupling in `model_runner.py`**: The runner manages file I/O, UI streaming requirements, and prompt building. Calling it for purely background/silent memory loops will pollute the user's UI chat log and generate unneeded chat files.
*   **Implicit UI Streaming**: Because the API router streams back to the UI by tailing the file `model_runner.py` is currently writing to, interrupting this flow for structured parsing or background loops is difficult without breaking the UI.
*   **No Central Token Management**: No system limits the size of injected context (`repo_context.txt`) + history before inference, risking context window exhaustion.

## 6. Recommended next steps
1.  **Decouple Execution**: Abstract the inference logic out of the file-trigger loop so `model_runner.py` can be called programmatically (e.g., via FastAPI) for background loops without writing `.txt` files.
2.  **Add a "Silent/Ephemeral" Flag**: Allow triggering a chat request with a flag that skips file writing entirely or uses a separate hidden buffer, so reflection loops don't pollute UI history.
3.  **Formalize Context Adapters**: Expand the `global_flags/repo_context.txt` concept into a multi-file injection directory so memory, world-state, and system context don't conflict over one file.
4.  **Extract Prompt Builder**: Move the prompt construction sequence (Snapshot -> Context -> History -> Deltas) out of `model_runner.py` and into a dedicated `PromptAssembler` class.

## 7. Appendix (Files Inspected)
*   `model_runner.py`
*   `chat_manager.py`
*   `routers/chat_router.py`
*   `routers/fs_router.py`
*   `routers/config_router.py`
*   `utils/helpers.py`
*   `snapshot_loader.py`
*   `delta_manager.py`
*   `LYRN_v6/modules/Chat Interface.html`
*   `start_lyrn.py`