# LYRN-AI LLM Interface v7.1

A modern, professional GUI application for LLM interaction with advanced job automation, system monitoring, and theme customization capabilities.

## Quick Start

1.  **Install Dependencies**:
    ```bash
    pip install customtkinter llama-cpp-python pillow psutil
    ```
    *Optional for NVIDIA GPU monitoring:*
    ```bash
    pip install pynvml
    ```

2.  **Run Application**:
    ```bash
    python lyrn_gui_v7.1.pyw
    ```

3.  **First Launch Setup**:
    -   On first launch, a model selector will appear. Choose your GGUF model from the `models` folder.
    -   The application auto-generates `settings.json` for all configurations.
    -   Further settings can be configured via the "Settings" button in the GUI.

## Key Files

### Core Application
- `lyrn_gui_v7.1.pyw` - Main GUI application.
- `model_loader.py` - Script that runs the LLM in a separate process for a responsive GUI.
- `settings.json` - Auto-generated configuration file.
- `themes/` - Directory containing JSON theme files.
- `languages/` - Directory for UI language translations.

### Documentation
- `README.md` - This quick start guide.
- `AGENTS.md` - Instructions and guidelines for AI agent development on this codebase.

## Major Features

✅ **Responsive UI**: The LLM runs in a separate process, ensuring the GUI never freezes during model loading or generation.
✅ **Live System Monitoring**: Real-time gauges for CPU, RAM, Disk, and VRAM usage.
✅ **Advanced Theming**: A built-in, live theme editor to create, modify, and save color themes.
✅ **Dynamic Model Status**: A color-coded, animated status light shows the exact state of the model (Ready, Thinking, Error, etc.).
✅ **Flexible Window Management**: Non-modal popups allow multiple utility windows (like Logs and Personality) to be open at once.
✅ **Professional Interface**: Clean dark mode with extensive customization options.
✅ **Settings Management**: GUI editor with backup/restore capabilities.
✅ **Job Automation**: Condition-based processing of complex, chained jobs.
✅ **Performance Tracking**: Real-time tokens/second display.

## What's New in v7.1

- **UI Layout:** The time and date display has been moved to the right sidebar and enlarged to balance the UI. The corner radius of all major elements is now set to 38 for a more modern look.
- **Model Status Indicator:** The status light is now fully functional with a new color and animation key to clearly indicate the model's state (e.g., blinking blue for "Thinking", solid green for "Ready").
- **External Model Loading:** The language model now runs in a completely separate process (`model_loader.py`). This is the most significant architectural change, preventing the GUI from becoming unresponsive during model operations. A "Change Model" button has also been added for convenience.
- **Window Behavior Fixes:** The "Personality" and "View Logs" windows are no longer modal and can be opened simultaneously. The "Personality" window now correctly stays open after settings are applied.

## Architecture

### Core Classes
- `LyrnAIInterface` - The main GUI application window.
- `SettingsManager` - Manages loading/saving of `settings.json`.
- `ThemeManager` - Handles discovery, application, and editing of themes.
- `LanguageManager` - Manages UI string translations.
- `SnapshotLoader` - Builds the base prompt from the `build_prompt` directory.
- `SystemResourceMonitor` - Runs in a background thread to provide system stats.
- `AutomationController` - Manages the logic for job automation.

### Inter-Process Communication (IPC)
The GUI (`lyrn_gui_v7.1.pyw`) and the model process (`model_loader.py`) communicate via a simple file-based system in the `ipc/` directory.
- The GUI writes a `prompt_*.json` file.
- The model loader watches for this file, processes it, and writes a corresponding `response_*.json` file.
- A `ipc.lock` file is used to prevent race conditions.

### Folder Structure
```
/
├── ipc/                  # For communication between GUI and model process
│   ├── prompts/
│   └── responses/
├── models/               # Place your .gguf model files here
├── themes/               # .json theme files
├── languages/            # .json language files
├── build_prompt/         # Files for building the master prompt
├── chat/                 # Saved chat message history
├── deltas/               # System updates (timestamp ordered)
└── [other paths configurable via settings]
```

## Troubleshooting

### Common Issues
- **Model won't load**: Check the console output. The `model_loader.py` script prints detailed logs. Ensure the model path is correct and the file is not corrupt.
- **GUI is running but nothing happens**: Ensure the `model_loader.py` process started correctly. Check your system's task manager for a second python process.
- **Missing folders**: Most required folders are created automatically. Ensure you have a `models` folder with a valid GGUF model file inside.
- **Performance issues**: Adjust GPU layers and thread count in the model selector or settings window.

---

**Note**: This application has undergone significant architectural changes to improve stability and user experience. The core powerful features of LLM interaction and automation are retained and enhanced.