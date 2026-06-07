[Output truncated for brevity]

rectory is now streamlined to contain only files essential for the LYRN v5 Dashboard and Headless Worker operation.

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

### Version 6.0 Update
- **Feature**: Added Claude Code Control Center GUI
  - Integrated `xterm.js` for an interactive terminal.
  - Added configuration flags and preset execution commands in the UI.
- **Backend**: Implemented WebSocket terminal streaming in `start_lyrn.py`.
  - Added `WebTerminalSession` (Windows) and `LocalPTYSession` (Linux/Mac using `pty`).
  - Added dependencies: `websockets`, `uvicorn[standard]`, `pty`.
- **Logging Updates**:
  - Terminal connection status and errors are now printed to `stdout` securely.

### Phase 4
- **What was moved:** Extracted the application lifespan context manager and scheduler loop background task into a new `core/lifecycle.py` file. Refactored `start_lyrn.py` to be exclusively a composition layer coordinating routers, static files, and initializations.
- **Issues encountered:** Adjusted the sleep interval on the `scheduler_loop` to 0.5s per memory instructions regarding background automated latency intervals. Encountered missing `fastapi` module when testing without loading standard dependencies; `uvicorn` starts correctly.
- **Risks or follow-ups:** This phase finalizes the `start_lyrn.py` decoupling. Remaining dependencies or edge cases could pop up in complex concurrent flows since the refactor significantly rearranged instantiation timing.

## v6.0.1 - Claude Code Runtime Reliability Audit (Remote + venv)

- **Backend hardening (`start_lyrn.py`)**
  - Added deterministic Claude binary resolution for backend-launched subprocesses.
  - Added support for explicit `LYRN_CLAUDE_BIN` / `CLAUDE_BIN` overrides.
  - Added PATH normalization for backend child processes so resolved Claude bin directories are inherited even when service PATH differs from interactive shells.
  - Updated orchestrated run launch and auth status checks to use resolved binary path and explicit subprocess environment.
  - Improved failure messaging when Claude is not visible in backend runtime context.

- **Terminal reliability (`start_lyrn.py`)**
  - Fixed websocket terminal reconnect behavior by introducing session reuse keyed by SID.
  - Added delayed cleanup for terminal sessions so brief browser disconnect/reconnect does not kill the shell.
  - Injected resolved Claude binary directory into PTY session PATH to reduce “works in local shell, fails in remote backend terminal” drift.

- **Logging updates**
  - Added clearer backend-facing error messages for Claude binary discovery failures (includes actionable env guidance).
  - Preserved terminal connection/disconnection logs and now keep reconnect continuity visible through session reuse behavior.

### Version 6.3 Update (Job Loop Injection System Enhancements)
- **Feature**: Expanded Job schema in `services/job_registry.py` and `routers/job_router.py` to include `affordances_json`, `max_retries`, and `retry_error_message`.
- **Feature**: Added `scripts/parse_job_response.py` to handle standard JSON parsing, structural validation, and retry logic (`max_retries`) of model output.
- **UI**: Overhauled Job Editor in `LYRN_v6/modules/JobManager.html` to use a toolbar (load, add, save, refresh, delete) and added inputs for max retries and editable affordance lists.
- **Docs**: Updated `lyrn_docs/JOB_LOOP_INJECTION_SYSTEM.md` to reflect new schema, standard output JSON format, usage of the parser, and explicitly confirmed why there is no separate loop builder.

### Verbatim Memory Module Integration
- Built "Verbatim Memory Module" prioritizing deterministic, inspectable file-based (CSV/JSON) storage over DB layers.
- Created `services/verbatim_memory.py` core logic restricting block files to max 50 pairs and dynamically updating `convo_meta.json`.
- Implemented core REST API in `routers/verbatim_router.py` covering creation, updating strings (including new `Summary` functionality), listing (views), and granular/bulk deletion operations matching requested schema constraints.
- Integrated `verbatim_router` into `start_lyrn.py`.
- Enforced required `ID, Timestamp_Start, Timestamp_End, Input, Output, Summary` formatting and UTC dates as per Parser Contract.
- Installed/Resolved implicit missing fastAPI/AIO dependencies ensuring clean boot.

### Index Recall System
- Developed a new backend storage service (`services/index_manager.py`) mapping pipe strings to `core.json`, `logs.csv`, and `entries.md` to represent dynamic indexes.
- Added API endpoints in `routers/index_router.py` to adjust default string recall thresholds for logs.
- Added a visual module to `LYRN_v6/modules/IndexSettings.html` mimicking styling to update recall values easily.
- Integrated the new module into `LYRN_v6/dashboard.html` dock layout.
- **Logging Updates**:
  - No changes.