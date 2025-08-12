# LYRN-AI v3.4 Build Notes

## v3.4 - Popup Theming and Icon Consistency (2025-08-12)

This update focuses on improving the visual consistency of all popup windows by ensuring they use the application's theme and icon correctly.

- **Popup Icon Standardization:**
    - All popup windows now correctly display the main application icon (`favicon.ico`).
    - This was achieved by adding the icon-setting logic to the `ThemedPopup` base class, from which all other popups inherit.

- **Popup Theming and Title Bar Color:**
    - Fixed a major visual bug where most popups would appear with a jarring, un-themed (often white) title bar.
    - All popups are now correctly set as "transient" for the main window, which allows the operating system to manage them more closely and apply the correct title bar theme.
    - Fixed a bug where the "System Prompt Builder" popup was completely un-themed. Its broken, overriding `apply_theme` method was removed, allowing it to inherit the correct theming from its parent class.

- **Versioning:**
    - Renamed `lyrn_sad_v3.3.pyw` to `lyrn_sad_v3.4.pyw`.
    - Archived the previous version in `deprecated/Old/`.

# LYRN-AI v3.3 Build Notes

## v3.3 - UI Cleanup and Theming (2025-08-12)

This update addresses several UI issues, improves theming consistency for popups, and adds a convenience feature for accessing heartbeat logs.

- **Automation Popup Fixes:**
    - Corrected a major bug where the "Automation" popup's tabs ("Job Viewer", "Job Builder", "Reflection Cycle") were empty. The methods to create the tab content were incorrectly placed in the `AffordancePopup` class and have been moved to the correct `JobWatcherPopup` class.
    - Removed the "Open Affordance Editor" button from the "Automation" popup to streamline the UI, as it is already accessible from the main window.

- **Theming Engine for Popups:**
    - Created a new `ThemedPopup` base class to standardize theming across all popup windows.
    - All popups, including `JobWatcherPopup`, `AffordancePopup`, and `LogViewerPopup`, now inherit from this class and apply the application's current theme, ensuring a consistent look and feel.

- **Settings Window Modality:**
    - Fixed an issue where the "Settings" window would block interaction with all other application windows (modal behavior). The `grab_set()` call was removed, so it no longer blocks other windows from being closed.

- **Heartbeat Log Access:**
    - Added a new folder icon button next to the "Heartbeat Cycle" switch on the main UI.
    - Clicking this button opens the `automation/heartbeat_outputs` directory directly in the system's file explorer, providing quick access to the logs.

- **Versioning:**
    - Renamed `lyrn_sad_v3.2.pyw` to `lyrn_sad_v3.3.pyw`.
    - Archived the previous version in `deprecated/Old/`.

# LYRN-AI v3.2 Build Notes

## v3.2 - Heartbeat and Affordance GUI (2025-08-11)

This update focuses on fixing the heartbeat system to respect the global automation flag and implementing a full-featured GUI for managing internal affordances.

- **Heartbeat Watcher Fixes:**
    - The `heartbeat_watcher.py` script now correctly checks the `global_flags/automation.txt` file. The watcher will now only process heartbeat files when this flag is set to "on", preventing it from running when automation is disabled.
    - Cleaned up verbose logging from the watcher script to only show essential messages and errors.
    - Improved the parsing of the `CHAT_PAIR_ID` from heartbeat files to be more robust.

- **New Affordance Editor GUI:**
    - Implemented a new, full-featured "Affordance Editor" popup window.
    - The editor is accessible from the main UI via a new "Affordances" button in the "Job Automation" section, making it a first-class feature.
    - The popup has a two-tab layout:
        - **Viewer Tab:** Lists all saved affordances, with options to "Edit" or "Delete" them.
        - **Editor Tab:** A form for creating and editing affordances with fields for name, start/end triggers, output path, and filename.
    - All changes made in the GUI are saved to `automation/affordances.json` via the existing `AffordanceManager`.

- **Versioning:**
    - Renamed `lyrn_sad_v3.1.pyw` to `lyrn_sad_v3.2.pyw` to reflect the updates.
    - The previous version has been archived in `deprecated/Old/`.

# LYRN-AI v3.1 Build Notes

## v3.1 - Heartbeat and Internal Affordances (2025-08-11)

This is a major update that introduces the "Heartbeat," a toggleable, autonomous cognitive loop for the AI, and a system for "Internal Affordances," which are internal-only jobs triggered by the AI's reasoning during a heartbeat.

- **New Heartbeat System:**
    - A "Heartbeat Cycle" switch has been added to the "Automation" section of the right sidebar, allowing the user to toggle the autonomous loop on or off. The state is saved in settings.
    - When enabled, after every chat response, the AI performs an internal "heartbeat" cycle. It analyzes the preceding conversation and generates a structured output containing summaries, keywords, insights, and potential actions.
    - This output is saved to `automation/heartbeat_outputs/` for processing.

- **Heartbeat Watcher Enhancements:**
    - The `heartbeat_watcher.py` script has been updated to be the central processor for the new Heartbeat system.
    - It now parses the full heartbeat output, creates memory deltas, and adds jobs to the queue as instructed by the AI.

- **New Internal Affordance System:**
    - Implemented a new class of internal-only jobs called "Affordances." These are simple, trigger-based parsers that the AI can activate to extract specific information from a conversation.
    - The `heartbeat_watcher.py` can now process `AFFORD|` commands from a heartbeat file, find the relevant chat log, and execute the affordance to save the extracted data.
    - A new `affordance_manager.py` module and `automation/affordances.json` file have been created to manage these new objects.

- **New Affordance Editor GUI:**
    - A new "Affordance Editor" popup has been created, accessible from the "Automation" window.
    - This editor, modeled on the Job Watcher, allows users to easily create, view, edit, and delete affordances through a user-friendly interface.

# LYRN-AI v3.0 Build Notes

## v3.0 - Reflection Cycle and Autonomous Refinement (2025-08-11)

This is a major update that introduces the "Reflection Cycle," a new system for evaluating and refining job outputs using LLM-based reflection. This feature allows for autonomous improvement of job prompts over time.

- **New "Reflection Cycle" Tab:**
    - A new tab has been added to the "Automation" window to configure the reflection process.
    - Users can provide custom instructions for the LLM on how to evaluate job outputs.
    - A "gold-standard" example output can be provided for comparison.
    - The number of reflection iterations can be set.

- **Automated Prompt Refinement:**
    - A checkbox allows the LLM to automatically rewrite a job's prompt based on its reflection of the outputs.
    - Updated prompts are saved with versioning (e.g., `jobname_v2.txt`) to the `automation/jobs/` directory.

- **Autonomous Job Continuation:**
    - A checkbox enables the job to automatically continue running with the newly refined prompt, creating a self-improving loop of execution → reflection → refinement.

- **Traceability and Logging:**
    - All reflection outputs, including scores, notes, and any generated prompts, are saved to a new `reflections/` directory.
    - Each reflection run is stored in a timestamped subfolder (e.g., `/reflections/jobname_timestamp/`).
    - A `reflection_changelog.txt` file tracks all prompt updates for full traceability.

- **Batch Reflection:**
    - Reflection can be configured to run automatically after a set number of job outputs are generated, allowing for batch analysis and refinement.

# LYRN-AI v2.9 Build Notes

## v2.9 - Versioning Cleanup and Deprecation (2025-08-11)

This update officially moves the project to a `v2.x` versioning scheme, dropping the legacy `v7` prefix which was a remnant from a previous development branch. This is a maintenance and cleanup release.

- **Version Renumbering:**
    - The main application file has been renamed from `lyrn_sad_v7.2.9.pyw` to `lyrn_sad_v2.9.pyw`.
    - The project's official version is now `v2.9`.

- **Deprecation of Multi-Agent Components:**
    - All files and folders related to the deprecated multi-agent dashboard have been moved into a `deprecated/` directory for future review. This includes the `Old/` and `ipc/` directories, and the `multi_model_manager.py` script.

- **Architectural Rules Update:**
    - The `AGENTS.md` file has been updated to reflect the new location for storing old GUI versions (`deprecated/Old/`).

# LYRN-AI v7 Cognition Upgrade Build Notes

## v7.2.9 - UI Polish and Combobox Fix (2025-08-11)

This update focuses on minor UI polishing and fixing a persistent issue with `CTkComboBox` widgets.

- **Combobox Default Text:**
    - Fixed a bug where several `CTkComboBox` widgets across the application would display the text "ctkcombobox" when they had no items to show.
    - All relevant comboboxes now correctly display an empty string ("") by default, providing a cleaner and more professional user experience.

- **UI Text Cleanup:**
    - The "Job Automation Watcher" button on the right sidebar has been renamed to simply "Automation" for a cleaner look.
    - The title of the corresponding popup window has also been updated to "Automation" for consistency.

## v7.2.8 - Job Automation Watcher (2025-08-11)

This update introduces a new "Job Automation Watcher" feature, providing a user-friendly interface to create, manage, and run simple parser jobs. These jobs can extract text from the main chat window based on user-defined start and end triggers and save the result to a specified file.

- **New Backend Module:**
    - A new `job_watcher_manager.py` file was created to handle the logic for these new parser jobs, keeping them separate from the existing prompt-based automation system.
    - It uses a new `automation/watcher_jobs.json` file to store job definitions.

- **Job Automation Watcher Popup:**
    - A new "Job Automation Watcher" button has been added to the right sidebar, launching a dedicated popup for this feature.
    - The popup has a two-tab interface:
        - **Job Viewer:** Displays a list of all saved parser jobs. Users can select a job to run, edit, or delete it. A confirmation dialog has been added for deletions.
        - **Job Builder:** A form for creating or editing jobs. It includes fields for a job name, start/end triggers, an output filename, and a directory selector for the output path.

- **Functionality:**
    - Users can now define simple, reusable parsing tasks directly within the GUI.
    - The "Run" function a job against the current content of the chat display, making it easy to extract information from conversations.

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
