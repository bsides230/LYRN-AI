# LYRN-AI v7 Cognition Upgrade Build Notes

## v7.2.7 - UI Layout and Readability Enhancements (2025-08-11)

This update focuses on improving the main user interface layout for better balance and readability, based on user feedback.

- **Right Sidebar Reorganization:**
    - The "Job Automation" section has been moved from the left sidebar to the right sidebar, positioned below the "System Resources" block. This consolidates monitoring and action-oriented controls in one place.

- **Cleaner Performance Metrics:**
    - The layout of the "Performance Metrics" and "System Resources" sections has been updated for improved clarity.
    - All progress bars are now positioned directly underneath their corresponding labels, creating a cleaner, more organized, and easier-to-read vertical layout.
    - This change also helps ensure that the left and right sidebars can maintain a consistent width, contributing to a more balanced and visually appealing interface.

## v7.2.6 - Job Automation Logging (2025-08-11)

This update introduces a new structured logging system specifically for job automation. The goal is to create a detailed, machine-readable log of each interaction, which can be monitored by an external "watcher" script to trigger automated workflows.

- **Structured Chat Logger:**
    - A new `StructuredChatLogger` class has been added to handle the creation of timestamped log files.
    - For each user interaction, a new log file is created (e.g., `chat_20250811_102000_123456.txt`).

- **Tagged Log Content:**
    - The logger saves the interaction in three distinct, tagged sections within the same file:
        - The user's input is saved under `#USER_START#` and `#USER_END#`.
        - The model's internal "thinking" process (text between `<thinking>` tags) is saved under `#THINKING_START#` and `#THINKING_END#`.
        - The final, complete response from the assistant is saved under `#RESPONSE_START#` and `#RESPONSE_END#`.
    - This structured format allows an external script to easily parse the different components of the conversation for automation purposes.

- **Integration:**
    - The new logger is integrated into the main chat workflow. It captures user input, thinking, and the final response, and logs them to the appropriate file.
    - The previous chat saving mechanism (`save_chat_message`) has been deprecated to avoid redundancy.

## v7.2.5 - Prompt Builder Overhaul (2025-08-11)

This update completely revamps the System Prompt Builder for a significantly improved user experience and adds powerful new features for managing prompt components.

- **Dedicated Prompt Builder Window:**
    - The "Prompt Manager" tab has been removed from the Settings window.
    - A new "Open System Prompt Maker" button has been added to the "Advanced" tab in Settings, which launches the prompt builder in a dedicated, non-modal popup window.
    - The popup includes a "Keep on Top" checkbox, allowing it to stay visible while interacting with the main application.

- **File Pinning:**
    - Users can now pin individual prompt files to the top of the build order.
    - Pinned files are visually distinct and will always be loaded first, regardless of other sorting.
    - The pinning status is saved and preserved when the prompt index is refreshed.

- **Enhanced Drag-and-Drop:**
    - The drag-and-drop functionality for reordering prompt files has been completely overhauled.
    - It now features a smooth dragging motion and a clear, visual drop indicator line, so users know exactly where a file will land.
    - The reordering logic now respects pinning, preventing un-pinned files from being dropped into the pinned section and vice-versa.

- **Underlying Data Structure:**
    - The `build_prompt_index.json` has been upgraded from a simple list of paths to a list of objects, allowing metadata like `pinned` status to be stored for each file.
    - A migration path has been added to automatically and seamlessly update the old file format for existing users.

## v7.2.4 - Settings Path Hotfix (2025-08-11)

This is a hotfix release to address a critical bug in the settings system.

- **Fixed Hardcoded Paths:** The `SettingsManager` was using a hardcoded absolute path (`D:\LYRN\chat`) for the chat directory, which would cause the application to fail for other users.
- **Improved First-Time Setup:** The system now correctly detects when `settings.json` is missing and generates a new, default settings file using relative paths (e.g., `./chat`), ensuring the application runs correctly on first launch without manual configuration.

## v7.2.3 - Settings Refactor & UI Cleanup (2025-08-11)

This update focuses on streamlining the settings window and improving user workflow based on feedback.

- **Settings Window Refactor:**
    - The "Model Config" tab has been removed from the settings window to reduce redundancy, as model selection is handled by the "Change Model" button on the main screen.
    - The "Theme Builder" tab has been removed. The theme builder is still accessible via a button in the "Advanced" tab.
    - The "Personality" editor, formerly a popup, has been moved into its own dedicated "Personality" tab within the settings window.
    - The "Reload Model (Full)" button has been removed from the "Advanced" tab to simplify the UI.

- **Prompt Manager Enhancements:**
    - The "Prompt Manager" tab in settings now includes a "Mode Management" section.
    - Users can now view all saved modes in a list.
    - A "Load Mode" button allows users to activate a saved mode, which updates the current prompt build order.
    - A "Delete Mode" button allows users to permanently remove a saved mode.

- **Chat History:**
    - Clarified that the chat history is saved as individual `.txt` files.
    - The save location is visible and configurable in the settings window under `Directory Paths -> Chat Directory`.

## v7.2.2 - UI Enhancements & Feature Additions (2025-08-11)

This update focuses on quality-of-life improvements, new features, and better project organization.

- **Terminal Popup:**
    - A new "Code Terminal" button has been added to the Quick Controls section.
    - This button opens a new native terminal window, allowing users to execute code or commands in a clean environment.
    - A "Terminal Start Path" setting was added to the "UI Settings" tab in the Settings window. This allows users to configure the default directory where the terminal opens. The default is the application's root directory.

- **Dependency Management:**
    - A new `dependencies` directory has been created to formalize project dependencies.
    - A `requirements.txt` file is now included in this directory, listing all required Python packages.
    - The `AGENTS.md` file has been updated to include a rule for maintaining this new dependency file, ensuring a smoother setup for future development.

- **Performance Metrics UI Overhaul:**
    - The status dot (●) next to the "generation tok/s" label has been removed, and the label is now centered for a cleaner look.
    - The "KV Cache" progress bar has been updated to accurately reflect the number of tokens used from the cache relative to the total context size (`n_ctx`), providing a more meaningful metric.
    - A new progress bar for "Total Tokens" has been added, which also shows the usage against the total context size, allowing for a quick comparison of token usage.

---

## Phase 1: Core Architecture (2025-08-09)

This initial phase implements the core architectural changes outlined in `cognition_upgrade_v1.2.md`.

- **New Modules:** Created `delta_manager.py`, `automation_controller.py`, `heartbeat.py`, `heartbeat_watcher.py`, and `file_lock.py`.
- **GUI Upgrade:** Upgraded `lyrn_gui` to v7, integrating the new components.
- **File-based IPC:** The architecture now uses the filesystem for inter-process communication. The GUI generates heartbeat files, which are processed by a separate `heartbeat_watcher` script. A shared `job_queue.json` is used for automation.
- **Locking:** A simple file-based lock (`SimpleFileLock`) has been implemented to prevent race conditions on shared resources like the job queue.
- **Features:** Implemented the new Personality Sliders UI, which uses the delta system for live updates.

---

## Phase 2: GUI v7.1 Refinement & Stability (2025-08-09)

This phase focuses on refining the v7 GUI, improving stability, and implementing key user-requested features.

- **External Model Process:** The most significant change is the offloading of the LLM into a separate process (`model_loader.py`). This prevents the GUI from freezing during model loading and generation, dramatically improving UI responsiveness. Communication is now handled via a file-based IPC system in the `ipc/` directory.
- **UI/UX Overhaul:**
    - The main layout was updated for better visual balance, moving the time/date display and increasing its size.
    - All major UI components now have a corner radius of 38 for a more modern aesthetic.
    - A "Change Model" button was added to the main interface for convenience.
- **Model Status Indicator:** The status light is now fully functional with a new, detailed color and animation key to provide clear feedback on the model's state (e.g., Ready, Thinking, Error).
- **Windowing Fixes:**
    - The "Personality" and "View Logs" popups are no longer modal, allowing them to be used simultaneously.
    - The "Personality" window now correctly remains open after applying changes, improving the workflow.
- **Documentation:** The project's `README.md` has been comprehensively updated to reflect all the new features and the v7.1 architecture.

---

## Design Philosophy Notes

### Heartbeat Parser Philosophy (verbatim from user, 2025-08-09)
> The heartbeat parser will just be a watcher for the folder that the heartbeat text goes into. This heartbeat is not just another job like i thought but does need to be a toggleable runtime. We are just injecting the trigger like a job though. So you need to think in terms of simple grab text from provided structured blocks and put them where its told to put them every time. no smart logic routing or handling. just dumb take this block of text between the brackets and place it where it needs to go. The entire system runs off of this logic and it will be simple to implement.

---

## Phase 3: Next Steps & Todos

- **Implement Delta Consumption**: The system currently *generates* deltas, but does not yet *consume* them. The next task is to implement the logic that, for each reasoning cycle, gathers all new delta files, reads their content, and injects the resulting block of strings into the LLM's context. This is a critical step for enabling the AI's self-monitoring capabilities. Refer to `AGENTS.md` for the specific injection point and architectural purpose.

---

## v7.2 - Multi-Agent Constellation (2025-08-10)

This major update introduces a multi-agent architecture, allowing users to load and interact with multiple language models simultaneously in a tabbed interface.

- **Multi-Agent GUI:**
    - The central chat window has been replaced with a custom tabbed interface.
    - Agent tabs are managed via a vertical set of buttons on the right side of the chat area, allowing for quick switching between conversations.
    - A new "+" button launches the "Add New Agent" popup to configure and load a new model into a new tab.

- **Dynamic Agent Loading:**
    - A new `AddNewAgentPopup` provides a comprehensive UI for loading new agents.
    - Users can name each agent tab, select a model file, and configure all model parameters (context size, GPU layers, etc.).
    - **Quick Picks:** The popup includes a preset system. Users can save a complete agent configuration as a named "Quick Pick" for one-click loading in the future. Presets are saved in `model_presets.json`.

- **Enhanced Process Management:**
    - Introduced `MultiModelManager`, a new class responsible for launching, tracking, and terminating multiple `model_loader.py` processes.
    - The file-based IPC system has been upgraded to support isolated communication channels for each agent, using unique subdirectories under the `ipc/` folder.
    - `model_loader.py` was updated to accept an `--ipc-id` to operate in its designated directory.

- **Startup Configuration:**
    - A new "Startup Agents" tab has been added to the main Settings window.
    - Users can select from their saved "Quick Picks" to create a list of agents that will be loaded automatically when the application starts.
    - This startup configuration is saved in `settings.json`. The application will now auto-load the user's preferred set of agents for a personalized experience.

---

## v7.2.1 - Revert to In-Process Model Loading (2025-08-10)

This update reverts the model loading mechanism to an in-process approach, removing the external `model_loader.py` and the associated file-based IPC. This change was made to simplify the architecture and resolve issues related to the IPC implementation, as the multi-agent control for which it was designed is no longer a project goal.

- **In-Process Model Loading:**
    - The `Llama` model is now instantiated directly within the main GUI process, as it was in v6.8 and earlier.
    - The `setup_model` function was updated to handle direct, in-process loading.
- **Removed External Process:**
    - The `model_loader.py` script is no longer used.
    - The `subprocess` calls and file-based trigger system (`chat_trigger.txt`) have been completely removed from the GUI.
- **Direct Response Generation:**
    - The `send_message` function now directly calls the `generate_response` method in a thread.
    - The `generate_response` method uses `self.llm.create_chat_completion` to stream the response directly to the GUI, eliminating the need for file tailing.
- **Code Simplification:** The removal of the IPC layer has simplified the codebase, making it easier to maintain and debug.
