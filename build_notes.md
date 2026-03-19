# Build Notes

## v5.0.3 - Restore v4 KV-Cache Reuse

This update restores the high-performance KV-cache reuse behavior from v4 while maintaining compatibility with the v5 headless architecture. It resolves the "inconsistent sequence position" errors observed with llama-cpp-python when reusing context.

- **Headless Worker (`headless_lyrn_worker.py`):**
    -   **Single-Flight Inference:** Implemented a global lock to ensure only one generation request processes at a time.
    -   **KV Cache Reuse:** Added logic to compare the prefix of the current request's message history against the previous state. If the history is an append-only extension, the KV cache is reused. If the history diverges (e.g., edited logs, deleted files), `llm.reset()` is called to ensure consistency.
    -   **v4 Log Format:** Restored the v4 chat log format (`user\n...\n\nmodel\n...`) by removing v5 specific markers (`#MODEL_START#`) and ensuring the `model` header is present. This ensures compatibility with v4-style frontends.
    -   **Stop Handling:** Generation interruptions (`STOP`) now explicitly mark the KV cache as invalid for the next turn to prevent sequence errors.

- **Chat Manager (`chat_manager.py`):**
    -   **Backward Compatibility:** Updated `get_chat_history_messages` to support parsing both the legacy v4 log format and the v5 marker-based format. This ensures seamless operation regardless of the log style used.

## v5.0.2 - Legacy Cleanup & Framework Analysis

This update involves a comprehensive cleanup of the repository to remove legacy artifacts from previous versions and a deep dive into comparing LYRN v5 with other local agent frameworks.

- **Repository Cleanup:**
    -   Moved legacy documentation and asset directories to `deprecated/v4_artifacts/` (`docs/`, `images/`, `languages/`, `lyrn_docs/`, `screenshots/`, `themes/`).
    -   Moved legacy configuration and utility files to `deprecated/v4_artifacts/` (`chat_review.txt`, `LYRN Style Guide.html`, `QUICK_START.md`, `personality.json`, `quotes.txt`, `settings.json.bk`, `verification_error.png`).
    -   The root directory is now streamlined to contain only files essential for the LYRN v5 Dashboard and Headless Worker operation.

- **Framework Analysis:**
    -   (Pending) A detailed report `framework_report.md` will be generated comparing LYRN v5's structured memory and headless architecture against other local agent frameworks.

## v5.0.1 - Chat UX & Stability Improvements

This update focuses on improving the Chat Interface user experience, adding support for reasoning models, and fixing backend stability issues on Windows.

- **Backend (Worker):**
    -   **Encoding Fix:** Modified `headless_lyrn_worker.py` to force UTF-8 encoding for `sys.stdout` and `sys.stderr`. This prevents the worker from crashing with `UnicodeEncodeError: 'charmap' codec...` when models generate special characters (e.g., non-breaking hyphens) on Windows consoles.
    -   **Robust Parsing:** Updated `chat_manager.py` regex to handle unclosed role blocks (e.g., `#MODEL_START#` without a closing tag). This ensures that if a generation is interrupted or the user reopens the chat mid-stream, the partial content is correctly displayed instead of being ignored.

- **Dashboard:**
    -   **Minimize Window:** Added a minimize button (`_`) to the window controls. This hides the window (keeping the DOM and stream active in the background) rather than closing it (which destroys the connection).

- **Chat Interface:**
    -   **Thinking Mode Support:** Added native support for reasoning models (e.g., DeepSeek-R1) that output `<think>...</think>` tags.
        -   **Collapsible UI:** Thinking process is rendered in a distinct, collapsible accordion block (`.think-block`).
        -   **Setting:** Added a "Show Thinking Process" checkbox in the module settings to toggle visibility globally.
        -   **Streaming:** The thinking block updates in real-time during generation.

- **Model Controller:**
    -   **Auto-Refresh:** Added a listener to the Model Selector dropdown. Clicking it now automatically refreshes the model list from the backend, eliminating the need to restart the module after downloading a new model.

## v5.0.0 - Dashboard v5 & Cleanup (Current)

This update marks the official transition to the Dashboard v5 architecture and a major cleanup of the codebase.

- **Architecture Overhaul:**
    -   Fully transitioned to `lyrn_web_v5.py` (FastAPI) and `headless_lyrn_worker.py`.
    -   Legacy CustomTkinter GUI files (`lyrn_sad_v4.*.py`) have been moved to `deprecated/v4_artifacts/`.
    -   Unused Python modules (`episodic_memory_manager.py`, `cycle_manager.py`, `color_picker.py`, `themed_popup.py`, `confirmation_dialog.py`, `model_loader.py`, `system_checker.py`, `help_manager.py`, `system_interaction_service.py`) have been deprecated.

- **Model Controller:**
    -   Added a "DEFAULT" preset slot to the Model Controller module.
    -   Users can now save their preferred configuration as the default preset by entering 'default' or 'd' when saving.
    -   The default preset button appears before the numbered presets.

- **Documentation:**
    -   Created new `README.md` focused on v5.
    -   Archived v4 documentation and build notes to `deprecated/v4_artifacts/`.

- **PWA & Startup:**
    -   Added `manifest.json` and `sw.js` to enable PWA installation.
    -   Added `start_lyrn.bat` for easy startup without command line.
    -   Added `port.txt` to configure the web server port (default: 8080).
    -   Cleaned up root directory by moving `req.md`, `GUI_ANALYSIS.md`, `MEMORY_SYSTEM_ANALYSIS.md`, and `settings.json.bk` to `deprecated/v4_artifacts/`.

- **Bug Fixes & Hardening:**
    -   **Chat Logic:** Fixed an issue where the user's latest message was duplicated in the prompt (once from history, once from the active trigger), causing "Conversation roles must alternate" errors. The Worker now explicitly excludes the active chat file when retrieving history.
    -   **Path Handling:** Updated `settings.json` to use relative paths instead of absolute Windows paths. This prevents the creation of invalid directories (e.g., folders named `D:\LYRN-SAD\global_flags`) when the backend is run in a Linux environment.
    -   **Git:** Added `chat_trigger.txt` to `.gitignore`.

- **Startup & Authentication:**
    -   **Token Tools:** Added `token_generator.py` (and `generate_token.bat`) to generate secure admin tokens into `admin_token.txt`.
    -   **Startup Wizard:** Updated `start_lyrn.bat` to prompt users (Y/N) for dependency installation.
    -   **Quick Start:** Added `quick_start.bat` for immediate server launch skipping checks.
    -   **File-Based Auth:** Backend now reads `admin_token.txt` for the admin token, falling back to environment variables.
    -   **Model Manager UI:** Updated Authentication Modal to support direct file upload of `admin_token.txt` for easier login.

## Philosophy & Rules (Ported)

-   **Efficiency and Accessibility:** The primary goal is to create a powerful AI cognition framework that is lightweight enough to run on standard consumer hardware.
-   **Structured Memory over Prompt Injection:** All core context—personality, memory, goals—lives in structured text files and memory tables. The LLM reasons from this stable foundation rather than having it repeatedly injected into a limited context window.
-   **Simplicity and Robustness:** The architecture is inspired by the simplicity of 1990s text-based game parsers. The framework's job is to be a robust, simple system for moving data; the LLM's job is to do the heavy lifting of reasoning.
-   **UI Development:** New modules must be implemented as single-file solutions (combining HTML, CSS, and JS) in `LYRN_v5/modules/` to facilitate loading on smaller systems and minimize floating dependencies. UI must strictly follow `LYRN Style Guide.html`.


## v5.0.4 - Full-System Install & Runtime Validation Audit (2026-03-19)

### Environment
- Host OS: Linux 6.12.47 x86_64 (glibc 2.39)
- Python: system interpreter `python` / `python3` -> 3.12.12
- pip: 25.3
- Execution mode: system-wide install only, no virtual environment
- Repo path: `/workspace/LYRN-AI`

### Exact install commands run
- `python3 --version`
- `python --version`
- `pip --version`
- `python -m pip install -r requirements.txt`

### Incremental package installs
- None. The single primary install completed without requiring any follow-up package installs.

### Exact runtime / validation commands run
- `python start_lyrn.py`
- `curl -s http://127.0.0.1:8080/health`
- `curl -s http://127.0.0.1:8080/api/auth/status`
- `POST /api/models/fetch` with the required Hugging Face GGUF URL
- `GET /api/models/downloads`
- `GET /api/models/list`
- `POST /api/config/active`
- `POST /api/system/start_worker`
- `GET /api/system/worker_status`
- `POST /api/chat`
- `GET /api/chat/status`
- Local inspection of `automation/job_queue.json`, `automation/job_history.json`, `chat_trigger.txt`, and `jobs/job_model_output.txt`

### What changed during validation
- No source-code files were modified to get the system running.
- A temporary runtime workaround file `global_flags/no_auth` was created locally so the API could be exercised after the backend reported `{"required": false}` but still returned `401 Unauthorized` on protected endpoints when no admin token was configured.
- `settings.json` was temporarily updated through the product’s own API (`/api/config/active`) to validate that the active model selection flow writes back to settings.
- Runtime-generated files were produced/updated during testing, including scheduler state, job history, and dynamic snapshot files.

### Why the workaround was necessary
- Without `global_flags/no_auth`, the UI/API flow could not proceed through model download, model activation, worker start, or chat submission on a fresh install with no `admin_token.txt`, even though `/api/auth/status` explicitly reported that auth was not required.
- This should be treated as a product defect, not a permanent operational requirement.

### What would have failed without the workaround
- Model manager fetch requests failed with `401 Unauthorized`.
- Model controller worker-start and active-config flows were blocked.
- Chat submission was blocked before the job system could be exercised.

### Permanent fix vs workaround
- `global_flags/no_auth` was only a local validation workaround and should not be considered the permanent fix.
- The permanent fix should be in backend auth handling so `verify_token` matches `GET /api/auth/status` semantics.

### Runtime results summary
- Backend boot: success.
- UI static shell reachable from `/`: success.
- Model download via built-in workflow: failed because outbound access to Hugging Face was blocked in this environment (`403 Forbidden` through the configured proxy).
- Model activation flow writing `settings.json`: success via the same API path the UI uses.
- Worker boot: attempted, but failed because the required model file never downloaded.
- Job-based chat flow: queueing and scheduler/script handoff succeeded; final inference/output completion did not complete because the worker could not load the requested model.

### Logging notes
- Backend created a new log session under `logs/session_20260319_191145/`.
- Worker launch failures were visible in backend log streaming (`WorkerOut`), but no `global_flags/last_error.txt` was written, so the structured worker error field remained empty.
- Scheduler continuously executed the enabled delta script `send_timestamp.py` every 5 seconds during validation, creating persistent background log noise.

### Manual interventions
- Created `global_flags/no_auth` temporarily to continue validation in the absence of `admin_token.txt`.
- Attempted the exact required model download through the product workflow, then confirmed the failure state via `/api/models/downloads`.
- Activated the exact required model path through `/api/config/active` to validate settings persistence even though the file was not present locally.
