# LYRN-AI v4.0.0 Build Notes

## v4.0.0 - Prompt Builder Restructure (2025-08-15)

This major update modularizes the entire prompt building system for clarity, flexibility, and user control. The old system has been replaced with a new tabbed interface in a dedicated popup window.

- **New Modular Prompt Fragments:**
    - The prompt is no longer built from a single index file. Instead, it is constructed from modular fragments that are concatenated at runtime.
    - Each fragment is stored in its own file in a new directory structure under `build_prompt/`.
    - The new components are: Personality, Heartbeat, User Preferences, AI Preferences, and System Rules.

- **New System Prompt Builder UI:**
    - The old "System Prompt Builder" has been replaced with a new `SystemPromptBuilderPopup` window.
    - This new window features a tabbed interface with the following tabs:
        - **Personality:** Controls the LLM's personality settings and output tone.
        - **Heartbeat:** Manages when and how the heartbeat cycle is injected.
        - **Prompt Build Order:** A drag-and-drop list to control the order of prompt construction.
        - **User Preferences:** Fields for entering user preferences.
        - **AI Preferences:** Optional behaviors for the AI agent.
        - **System Rules & Toggles:** A GUI wrapper around system flags and hard constraints.

- **Toggle Logic and Configuration:**
    - Each prompt component can be toggled ON or OFF. If OFF, the component is skipped during the prompt build.
    - The toggle states are stored in a new `build_prompt/builder_config.json` file.
    - The order of the prompt components is defined in a new `build_prompt/prompt_order.json` file.

- **Refactored Prompt Loading Logic:**
    - The `SnapshotLoader` class has been refactored to use the new modular system.
    - It now reads the `builder_config.json` and `prompt_order.json` to build the `master_prompt.txt` file at runtime.

- **Versioning:**
    - The main application file has been versioned to `lyrn_sad_v4.0.0.pyw`.
    - The previous version `lyrn_sad_v3.9.6.pyw` has been archived.

# LYRN-AI v3.9.6 Build Notes

## v3.9.6 - Windows Environment Interaction System (2025-08-15)

This update introduces a powerful new "System Action" affordance type, allowing the AI to perform system-level actions on the Windows OS, similar to automation tools like AutoHotKey.

- **New 'system_action' Affordance Type:**
    - The core affordance system has been refactored to be type-based.
    - A new `system_action` type is now available, alongside the existing `text_parser` type.
    - This allows for greater flexibility and extensibility in creating new capabilities for the AI.

- **System Interaction Service:**
    - A new `system_interaction_service.py` module has been created to handle all OS-level interactions.
    - The `heartbeat_watcher.py` now dispatches `system_action` affordances to this new service.

- **Supported System Actions:**
    - **`open_app`**: Launch any application by its path.
    - **`send_keys`**: Send keystrokes to a specific application window.
    - **`click`**: Perform a mouse click at given coordinates.
    - **`move_mouse`**: Move the mouse cursor to a specific position on the screen.
    - **`window_focus`**: Bring a target window to the foreground.
    - **`window_resize`**: Resize and/or move a target window.

- **Dynamic Affordance Editor GUI:**
    - The "Affordance Editor" popup has been completely overhauled.
    - The UI now dynamically changes based on the selected affordance type (`text_parser` or `system_action`).
    - When creating a `system_action` affordance, the editor provides a nested, dynamic UI to select a specific action and configure its unique parameters.

- **Dependencies & Versioning:**
    - The following dependencies have been added to `dependencies/requirements.txt`: `pyautogui`, `pygetwindow`, `keyboard`, `pywin32`.
    - The main application file has been versioned to `lyrn_sad_v3.9.6.pyw`.
    - The previous version `lyrn_sad_v3.9.5.pyw` has been archived.

# LYRN-AI v3.9.5 Build Notes

## v3.9.5 - Granular Job Scheduler (2025-08-14)

This update introduces a new "Scheduler" tab in the Automation popup, allowing for granular, calendar-based job scheduling.

- **New Scheduler Tab:**
    - A new "Scheduler" tab has been added to the "Automation" window.
    - This tab features a full calendar view, with weeks starting on Sunday, allowing users to select a specific day to schedule jobs.
    - Days with scheduled jobs are highlighted in the calendar view.

- **Day-Specific Scheduling:**
    - Clicking on a day in the calendar opens a new popup window dedicated to that day's schedule.
    - Users can select a pre-existing job and schedule it to run at a precise time, with inputs for hour, minute, second, and millisecond.
    - The popup also lists all jobs already scheduled for that day.

- **New Backend Components:**
    - **`automation/scheduler_manager.py`**: A new manager class to handle saving and loading schedules to and from `automation/schedules.json`.
    - **`automation/scheduler_watcher.py`**: A new background watcher script that continuously checks for due schedules and adds them to the main job queue for execution.

- **Versioning:**
    - The main application file has been versioned to `lyrn_sad_v3.9.5.pyw`.
    - The previous version `lyrn_sad_v3.9.4.pyw` has been archived.

# LYRN-AI v3.9.4 Build Notes

## v3.9.4 - Task and Goal Management (2025-08-13)

This update introduces a new Task and Goal management system, allowing the AI to autonomously track and manage its objectives.

- **New Task/Goal Watcher:**
    - A new watcher script, `automation/task_goal_watcher.py`, runs in the background to monitor chat logs.
    - The watcher parses chat logs for specially formatted blocks (`###TASK_START###` and `###GOAL_START###`).
    - Extracted tasks and goals are saved as individual files in the `build_prompt/tasks/` and `build_prompt/goals/` directories, respectively.

- **New Tasks/Goals GUI:**
    - A new "Tasks/Goals" button has been added to the main UI.
    - This button opens a new popup window with a two-tab layout for managing tasks and goals.
    - The GUI allows users to view, add, edit, and delete tasks and goals, which correspond to files in the respective directories.

- **Versioning:**
    - The main application file has been versioned to `lyrn_sad_v3.9.4.pyw`.
    - The previous version `lyrn_sad_v3.9.3.pyw` has been archived.

# LYRN-AI v3.9.3 Build Notes

## v3.9.3 - Icon Loading Hotfix (2025-08-13)

This is a hotfix to address an issue with the application icon not displaying correctly on certain platforms.

- **Improved Icon Loading:**
    - Replaced the `wm_iconbitmap` method with the more robust `iconphoto` method for setting the application icon.
    - This change applies to both the main application window and all popup windows (via the `ThemedPopup` base class).
    - This ensures consistent and reliable icon display across different operating systems.

- **Versioning:**
    - The main application file has been versioned to `lyrn_sad_v3.9.3.pyw`.
    - The window title now correctly displays `v3.9.3`.
    - The previous version `lyrn_sad_v3.9.2.pyw` has been archived.

# LYRN-AI v3.9.2 Build Notes

## v3.9.2 - Feature Polish (2025-08-13)

This is a minor update to disable an unfinished feature and improve user feedback.

- **Disabled Theme Builder:**
    - The "Theme Builder" button, previously accessible from the Advanced tab in Settings, has been temporarily disabled.
    - Clicking the button now opens a popup informing the user that the feature is unfinished and will be coming in a future update.
    - This prevents users from accessing a non-functional part of the application.

- **Versioning:**
    - The main application file has been versioned to `lyrn_sad_v3.9.2.pyw`.
    - The window title now correctly displays `v3.9.2`.
    - The previous version `lyrn_sad_v3.9.1.pyw` has been archived.

# LYRN-AI v3.9.1 Build Notes

## v3.9.1 - Theming and Confirmation Dialogs (2025-08-13)

This update focuses on improving user experience by ensuring all popups are non-modal, fixing theme inconsistencies, and adding standardized confirmation dialogs for all destructive actions.

- **Standardized Confirmation Dialogs:**
    - Implemented a new, reusable `ConfirmationDialog` class for all actions that require user confirmation (e.g., deleting modes, themes, jobs, or clearing directories).
    - This dialog includes a "Don't ask me again" checkbox, which saves the user's preference to `settings.json` to prevent future prompts for that specific action.
    - Replaced all previous `CTkInputDialog` confirmation prompts with the new standardized dialog for a consistent look and feel.

- **Non-Modal Popups:**
    - All secondary windows (like the Theme Builder, Automation, and Affordance Editor) are now non-modal. They no longer block interaction with the main application window, allowing for a more flexible workflow.
    - This was achieved by removing the `grab_set()` call from the respective popup classes.

- **Theming Fixes:**
    - Addressed an issue where the "Model Settings" (preset picker) popup might not have been themed correctly after loading a preset. The theme is now explicitly reapplied to ensure visual consistency.
    - As part of the fix, the core `ThemedPopup` and `ThemeManager` classes were refactored into a separate `themed_popup.py` file to resolve a circular dependency and improve code organization.

- **Versioning:**
    - The main application file has been versioned to `lyrn_sad_v3.9.1.pyw`.
    - The window title now correctly displays `v3.9.1`.
    - The previous version `lyrn_sad_v3.9.pyw` has been archived.

# LYRN-AI v3.9 Build Notes

## v3.9 - Custom Color Picker and Theme Builder Enhancements (2025-08-12)

This update introduces a new custom color picker for the theme builder, allowing for more flexible and user-friendly theme customization.

- **New Custom Color Picker:**
    - Replaced the default `tkinter.colorchooser` with a custom color picker popup.
    - The new picker is implemented in a separate `color_picker.py` module for better organization.
- **Color Grid Display:**
    - The custom color picker displays a grid of colors loaded from `color_grid.json`, organized by section.
- **Custom Color Input and Saving:**
    - Users can now directly input a hex color code into the picker.
    - A "Save Custom" button allows users to save their custom colors, which are stored in `custom_colors.json` and displayed in a separate section within the picker.
- **Bug Fixes:**
    - Fixed a bug in `gui_designer.py` where it was attempting to load a non-existent GUI file (`lyrn_gui_v6.8.pyw`). It now correctly loads `lyrn_sad_v3.9.pyw`.
- **Versioning:**
    - The main application file has been versioned to `lyrn_sad_v3.9.pyw`.
    - The previous version `lyrn_sad_v3.8.pyw` has been archived.

# LYRN-AI v3.8 Build Notes

## v3.8 - Preset and Prompt Management Overhaul (2025-08-12)

This update introduces significant improvements to user workflow by adding model setting presets and enhanced control over the system prompt building process.

- **Model Settings Presets:**
    - The "Model Settings" popup now features a preset system.
    - Users can save the current model configuration (model path, context size, GPU layers, etc.) into one of five numbered preset slots.
    - Added a "Save" button and five preset buttons (1-5) to the popup.
    - Clicking a preset button instantly loads the saved configuration into the UI fields.
    - Presets are stored in `settings.json` under the `model_presets` key.

- **UI Reorganization:**
    - To improve contextual grouping, several controls have been relocated.
    - The "System Prompt" button has been moved from the "Quick Controls" section to the "System Status" section, directly under the "Mode" dropdown.
    - The "Heartbeat Cycle" switch and its associated "Open Logs" button have been moved from the right sidebar's "Job Automation" section to the same location under the "Mode" dropdown.

- **Prompt Builder Enhancements:**
    - **Remove from Index:** A "Remove File" button has been added to the "Prompt Builder" popup. This allows a user to select a file in the build list and remove it from the `build_prompt_index.json` without deleting the actual file.
    - **Index and Prompt Refresh Control:**
        - The button for re-scanning subfolders has been renamed to "Rebuild Master Index from Folders" for clarity.
        - A new "Refresh Prompt from Index" button has been added. This rebuilds the `master_prompt.txt` using only the files currently visible in the UI list, respecting any files that have been manually removed from the index. This allows for quick prompt updates without a full file system re-scan.

- **Versioning:**
    - The main application file has been versioned to `lyrn_sad_v3.8.pyw`.
    - The window title now correctly displays `v3.8`.
    - The previous version `lyrn_sad_v3.7.pyw` has been archived.

# LYRN-AI v3.7 Build Notes

## v3.7 - UI and Configuration Fixes (2025-08-12)

This update addresses several bugs and UI inconsistencies related to model configuration and window behavior.

- **Model Chat Format Configuration:**
    - Fixed a bug in the "Model Settings" popup where the `chat_format` could not be set to `None` (no format).
    - The UI now correctly saves an empty input as `None` in the settings, allowing a clear distinction between no format and an explicitly named format like `"none"`.
    - The model loader now correctly defaults to `None` if the `chat_format` setting is missing, improving initial setup.

- **"Keep on Top" Toggle Fix:**
    - Fixed a bug where the "Keep on Top" checkbox on popups (like the Log Viewer and Prompt Builder) had no effect.
    - The underlying window property (`transient`) that forced popups to always stay on top of the main window has been removed, allowing the toggle to function as expected.

- **Model Settings UI Enhancements:**
    - Renamed the "Change Model" button on the main UI to "Model Settings" for better clarity.
    - The corresponding popup window title has also been updated to "Model Settings".
    - A warning label has been added to the "Model Settings" popup to remind users that the model must be reloaded for changes to take effect.

- **Versioning:**
    - The main application file has been versioned to `lyrn_sad_v3.7.pyw`.
    - The window title now correctly displays `v3.7`.
    - The previous version `lyrn_sad_v3.6.pyw` has been archived.

# LYRN-AI v3.6 Build Notes

## v3.6 - Generation Control and Model Configuration (2025-08-12)

This update introduces critical user control features for model generation and enhances model configuration options.

- **Stop Generation Button:**
    - A "Stop" button has been added to the main chat interface next to the "Send" and "Copy" buttons.
    - This allows the user to immediately interrupt the model while it is generating a response, preventing runaway generation and providing more control.
    - The underlying logic uses a flag to gracefully exit the generation loop in the background thread.

- **Enhanced Model Settings:**
    - The "Change Model" popup has been updated with two new configuration fields:
        - **Chat Style:** A text input that allows the user to specify the `chat_format` for the model (e.g., `qwen`, `chatml`). It defaults to "none".
        - **Max Output Tokens:** A text input for the user to set the `max_tokens` parameter for the model's output.
    - These settings are now saved to and loaded from `settings.json`, allowing for persistent configuration.

- **Versioning:**
    - The main application file has been versioned to `lyrn_sad_v3.6.pyw`.
    - The window title now correctly displays `v3.6`.

# LYRN-AI v3.5 Build Notes

## v3.5 - Theming and Versioning Fixes (2025-08-12)

This update addresses several small but important UI and versioning issues to improve visual consistency and correctness.

- **Settings Border Theming:**
    - Fixed a bug where the borders around text boxes and entries in the Settings window were not using the correct color from the loaded theme. They now correctly apply the theme's `border_color`.

- **Icon Application:**
    - Changed the method for setting the application icon from `iconbitmap` to `wm_iconbitmap` to improve consistency across different window managers and platforms.

- **Title Bar Versioning:**
    - The main application window's title bar now correctly displays the current version, `v3.5`.

- **Versioning:**
    - Renamed `lyrn_sad_v3.4.pyw` to `lyrn_sad_v3.5.pyw`.
    - Archived the previous version in `deprecated/Old/`.

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
        - The's internal "thinking" process (text between `<thinking>` tags) is saved under `#THINKING_START#` and `#THINKING_END#`.
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
