# LYRN-AI Cognitive Architecture - v5.0

**LYRN** is a highly modular, professional-grade interface for interacting with local Language Models. Version 5 introduces a new web-based architecture (Dashboard v5) separated from the core logic (Headless Worker).

## Key Features

*   **Web-Based Dashboard:** A modern, single-page application (SPA) dashboard (`lyrn_web_v5.py`) serving modules for Chat, Job Management, System Monitoring, and more. Also works as an installable **PWA** (Progressive Web App).
*   **Headless Worker:** A robust background worker (`headless_lyrn_worker.py`) that manages the LLM, memory systems, and automation logic independently of the UI.
*   **Modular Design:** Modules are self-contained HTML/JS files located in `LYRN_v5/modules/`, communicating with the backend via a REST API.
*   **Structured Memory:** Continues the philosophy of file-based, structured memory (Episodic, Deltas) for genuine cognitive continuity.

## Installation

1.  **Install Dependencies:**
    ```bash
    pip install -r dependencies/requirements.txt
    ```

2.  **Place Models:**
    -   Create a folder named `models` in the root directory.
    -   Place your GGUF-format model files inside the `models/` folder.

## Usage

1.  **Start the Dashboard:**
    Run `start_lyrn.bat` or:
    ```bash
    python lyrn_web_v5.py
    ```
    This will launch the web server and open the dashboard in your default browser (default port 8080).

    *   **Port Configuration:** You can change the port by editing `port.txt`.

2.  **Install as PWA:**
    -   Open the dashboard in Chrome/Edge.
    -   Click the "Install LYRN Dashboard" icon in the address bar to run it as a standalone app.

3.  **Configure Model:**
    -   Open the **Model Controller** module from the dashboard.
    -   Select a model and configure parameters (Context Size, GPU Layers, etc.).
    -   You can now save a **Default** preset for quick loading.
    -   Click "Start System" to launch the Headless Worker.

## Architecture

*   `lyrn_web_v5.py`: FastAPI server handling the UI and API requests.
*   `headless_lyrn_worker.py`: The "brain" process running `llama-cpp-python` and managing cognitive state.
*   `LYRN_v5/`: Contains the frontend static files and modules.
*   `settings.json`: Central configuration file.

## License

See the [LICENSE](LICENSE) file for details.
