# LYRN-AI v7 Cognition Upgrade Build Notes

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
