# LYRN GUI - Required Files and Folders

This document lists all the essential scripts, files, and folders required to run the LYRN GUI and its associated systems.

## Core Application Scripts

These are the essential Python scripts that make up the LYRN GUI application.

-   `lyrn_sad_v4.0.1.pyw` (Main application entry point)
-   `affordance_manager.py`
-   `automation_controller.py`
-   `color_picker.py`
-   `confirmation_dialog.py`
-   `cycle_manager.py`
-   `delta_manager.py`
-   `file_lock.py`
-   `heartbeat.py`
-   `model_loader.py`
-   `system_interaction_service.py`
-   `themed_popup.py`

## Automation System Scripts

These scripts are part of the automation framework and are executed as subprocesses.

-   `automation/cycle_watcher.py`
-   `automation/scheduler_manager.py`
-   `automation/scheduler_watcher.py`
-   `automation/task_goal_watcher.py`

## Configuration and Data

These files and folders store the application's configuration, data, and assets.

-   **Files:**
    -   `settings.json`
    -   `personality.json`
    -   `hover_tooltip.json`
    -   `favicon.ico`
-   **Folders:**
    -   `images/` (contains `lyrn_logo.png`, etc.)
    -   `languages/` (contains `en.json`, etc.)
    -   `themes/` (contains `lyrn_dark.json`, etc.)
    -   `global_flags/` (contains `automation.txt`, `next_job.txt`, `llm_status.txt`)

## Automation, Prompt, and Data Storage Systems

These directories are critical for the application's advanced functionalities, including job automation, prompt construction, and data logging.

-   **`build_prompt/`**: Contains all components for constructing the system's master prompt.
    -   Includes `master_prompt.txt`, `builder_config.json`, `prompt_order.json`, and subdirectories like `personality/`, `heartbeat/`, `system_rules/`, `tasks/`, `goals/`, etc.
-   **`automation/`**: The core of the automation system.
    -   Includes `jobs/jobs.json`, `scheduler.json`, `cycles.json`, and various queue files.
    -   Also contains `heartbeat_outputs/` and `queued_chunks/`.
-   **`deltas/`**: Stores logs of changes to system configuration or personality.
-   **`chat/`**: Logs user and AI interactions.
-   **`chat_parsed/`**: Stores parsed chat logs.
-   **`output/`**: A general-purpose directory for file outputs.
-   **`metrics_logs/`**: Contains saved performance metrics reports.

## Third-Party Dependencies

These external Python libraries must be installed. They are listed in `dependencies/requirements.txt`.

-   `customtkinter`
-   `llama-cpp-python`
-   `Pillow`
-   `psutil`
-   `pynvml`
