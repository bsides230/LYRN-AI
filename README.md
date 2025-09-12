# LYRN-AI LLM Interface v4.2.3

A modern, professional GUI application for LLM interaction with advanced job automation, system monitoring, and a highly modular architecture.

## Quick Start

1.  **Install Dependencies**:
    ```bash
    pip install -r dependencies/requirements.txt
    ```
    This will install the following packages:
    - `customtkinter`
    - `llama-cpp-python`
    - `Pillow`
    - `psutil`
    - `pynvml` (for NVIDIA GPU monitoring)

2.  **Run Application**:
    ```bash
    python lyrn_sad_v4.2.3.pyw
    ```

3.  **First Launch Setup**:
    -   On first launch, a model selector will appear. Choose your GGUF model from the `models/` folder (you must create this folder and place your models inside).
    -   The application auto-generates `settings.json` for all configurations.
    -   Further settings can be configured via the "Settings" button in the GUI.

## Key Files

### Core Application
- `lyrn_sad_v4.2.3.pyw` - Main GUI application.
- `settings.json` - Auto-generated configuration file for settings, paths, and UI preferences.
- `automation/` - Contains all background watcher scripts for autonomous operation.
- `build_prompt/` - Contains all modular components for building the system prompt.
- `themes/` - Directory containing JSON theme files.
- `dependencies/requirements.txt` - A list of all required Python packages.

### Documentation
- `README.md` - This guide.
- `build_notes.md` - A detailed, version-by-version change log.
- `AGENTS.md` - Instructions and architectural rules for AI agent development on this codebase.

## Major Features

✅ **Responsive UI**: Built with CustomTkinter for a modern look and feel. Asynchronous initialization ensures the UI loads instantly and never freezes.
✅ **Live System Monitoring**: Real-time gauges for CPU, RAM, Disk, and VRAM usage.
✅ **Advanced Theming**: A built-in, live theme editor to create, modify, and save color themes.
✅ **Modular System Prompt Builder**: Granular control over every component of the system prompt via a dedicated UI. Components can be toggled, reordered, and their content and formatting can be edited.
✅ **Job Automation & Scheduling**: A powerful automation system with:
    - A calendar-based scheduler to run jobs at specific times.
    - A Cycle Manager to create and execute custom, multi-step cognitive cycles.
    - Watcher scripts that run in the background to handle various automated tasks.
✅ **Episodic Memory**: A structured, file-based memory system that saves each chat interaction as a detailed "Verbatim Chat Entry Pair" for advanced search, filtering, and context management.
✅ **Topic Indexing Engine**: A long-term memory system that builds a personalized web of meaning from conversations by identifying and indexing topics.
✅ **OSS Tool Format**: The AI can be given the ability to perform system-level actions like opening applications, sending keystrokes, and clicking the mouse.
✅ **Task and Goal Management**: A system that allows the AI to autonomously track and manage its objectives.

## License

This project is licensed under a custom source-available license. See the [LICENSE](LICENSE) file for details. The key points are:
- The software is provided "as-is".
- You are free to use, modify, and redistribute it for non-commercial purposes.
- Commercial use requires express written permission from the copyright holder (LYRN-AI).


## Architecture

### Core Components
- `LyrnAIInterface` - The main GUI application window, built with CustomTkinter.
- **Manager Classes**: The application logic is organized into a series of manager classes (e.g., `SettingsManager`, `ThemeManager`, `AutomationController`, `CycleManager`, `EpisodicMemoryManager`, `TopicManager`) that handle specific domains of functionality.
- **Background Watchers**: A suite of scripts in the `automation/` directory run as separate processes, watching for file-based triggers to perform autonomous tasks like running scheduled jobs, executing cognitive cycles, and processing new topics.
- **File-Based IPC**: The main GUI and the background watchers communicate through a system of flag files (in `global_flags/`) and data files (in `ipc/`), allowing for a decoupled and robust architecture.

### Folder Structure
```
/
├── automation/           # Background watcher scripts and automation configs
├── build_prompt/         # Modular components for building the system prompt
├── dependencies/         # Contains requirements.txt
├── deprecated/           # Old, unused files
├── episodic_memory/      # Structured chat logs
├── global_flags/         # Flag files for IPC
├── ipc/                  # Data files for IPC
├── models/               # Place your .gguf model files here
├── themes/               # .json theme files
└── [other paths configurable via settings]
```

## Troubleshooting

### Common Issues
- **Application doesn't start**: Ensure all dependencies from `dependencies/requirements.txt` are installed.
- **Model won't load**: Check the console output. Ensure the model path is correct in the "Model Settings" popup and the file is not corrupt. Ensure you have created a `models/` folder and placed your GGUF file inside it.
- **Missing folders**: Most required folders are created automatically on startup. If you encounter issues, deleting `settings.json` will trigger the first-time setup again.
- **Automation not working**: Ensure the automation flag is enabled in the settings and that the relevant watcher scripts are running. You can check your system's task manager for multiple python processes.