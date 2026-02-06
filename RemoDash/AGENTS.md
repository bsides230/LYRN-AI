# LYRN-AI Project Architectural Rules

This file contains critical architectural rules that must be followed during development.


 - Always update the build_notes.md file with detailed notes about the work done in the update. This should include a section on logging.
 
 - All python dependencies should be added to the `requirements.txt` file.
 
 - This system was designed after 90s text based game parser scripts and the simplicity of those triggers. We bring that same energy to this system.
 
 - Remember in this design we are building cognition for AI. We are building this with simplicty in mind. For example, no crazy coding to complete a function that just requires a file to be watched and the text pulled from formatted blocks. The llm does most of the heavy lifting. This system just moves files and data around dumbly. The affordances are just going to be simple triggers using the similar logic.

---
## Parser Contract (v1.0)

### Global rules

- **Markers:** Every block begins with `###<BLOCK>_START###` and ends with `###_END###` (exact, uppercase).
- **Enable switch:** The first logical field in each block MAY be `ENABLED=true|false`. If `false`, parsers MUST ignore the remainder of that block until `###_END###`.
- **Key:Value lines:** Fields are `KEY: value` on single lines. Booleans are `true|false`. Integers are base‑10. Times are ISO‑8601 UTC (`YYYY‑MM‑DDTHH:MM:SSZ`).
- **Arrays:** When present inline, arrays MUST be JSON (e.g., `["alpha","beta"]`), not comma lists.
- **Heredoc values:** Use `<<EOF`; the value is the following lines until a lone `EOF` on its own line.
- **No tabs:** Parsers MUST treat TAB as invalid; use spaces only.
- **Whitespace:** Parsers MUST trim trailing spaces but preserve interior whitespace of heredocs.
- **Order:** Block order is stable but not required by parsers. Within a block, field order is not significant.
---

## The LYRN Philosophy and Vision

This section provides insight into the core principles and long-term vision of the LYRN project. It is intended to help future developers and AI agents understand the "why" behind the architecture, not just the "how".

### Core Philosophy

LYRN is built on a philosophy that diverges significantly from mainstream LLM development. Instead of relying on ever-larger models and prompt injection, LYRN emphasizes **structured, live memory** to achieve genuine continuity, identity, and context. The core tenets are:

-   **Efficiency and Accessibility:** The primary goal is to create a powerful AI cognition framework that is lightweight enough to run on mobile, CPU-only hardware, completely offline. This is achieved through a ruthless focus on token efficiency.
-   **Structured Memory over Prompt Injection:** All core context—personality, memory, goals—lives in structured text files and memory tables. The LLM reasons from this stable foundation rather than having it repeatedly injected into a limited context window.
-   **Symbolic Reference:** The system avoids redundant tokenization by design. For example, in the Gamemaster system, a template for a new object is instantiated by passing only a template ID and a pipe-separated string of *values*. The LLM uses a central index to map these values to the correct fields, never needing to re-tokenize the field names.
-   **Simplicity and Robustness:** The architecture is inspired by the simplicity of 1990s text-based game parsers. The framework's job is to be a robust, simple system for moving data; the LLM's job is to do the heavy lifting of reasoning.

### The "Why": The Driving Motivation

The LYRN project was born from a single, driving goal: to solve the context bloat and statelessness problems that make most AI interactions feel repetitive and forgetful. The aim was to create a truly continuous and stateful AI companion that could be run by almost anyone, on readily available hardware, without a constant internet connection. It's an architecture built for persistence, presence, and partnership.

### Key Architectural Concepts

These are the pillars that support the LYRN philosophy:

-   **The Identity Core:** This is the stable, foundational layer that defines the AI's personality, ethical boundaries, and purpose. It is loaded into the LLM's KV cache and referenced, not constantly re-injected, providing a consistent anchor for all reasoning.
-   **The Heartbeat Cycle:** A secondary cognitive loop that runs between user interactions. It analyzes the recent dialogue, updates memory tables, and adapts the AI's internal state autonomously, allowing the system to learn and evolve without interrupting the conversational flow.
-   **The Snapshot & Delta System:** This is the core of LYRN's efficiency. Static "snapshots" of the core context are cached for speed. Any dynamic changes (e.g., a user adjusting the AI's personality) are recorded as "deltas" in a manifest file. The LLM is instructed to treat these deltas as high-priority overrides, enabling real-time adaptability without the cost of rebuilding the entire context.
-   **True Model-Agnosticism:** The framework is designed to be compatible with a wide variety of LLMs. It achieves this by stripping the model's native chat format and using its own standardized structure, allowing for consistent performance across different models and sizes.

### Future Vision

LYRN is not just a framework; it's the foundation for much larger ambitions. The architecture was designed to enable two major future projects:

1.  **A Multi-Agent Dashboard:** A visual interface, imagined as a security camera manager, where each "cam feed" is a containerized LYRN agent. This dashboard will allow for the command and control of multiple agents, both local and remote, leveraging LYRN's simple, text-based nature for communication.
2.  **A Generative World Engine:** A system for creating vast, detailed, and persistent worlds for gaming, simulation, or even real-world mapping. This is not a pre-written world database; it's a true generative engine. The world is created on the fly as the user explores it. When a user interacts with an object, the LLM is triggered to "lazy load" its details by filling out a template based on the rich, hierarchical context of the player's location. The world itself is an emergent property of the LLM's interaction with the template system.

## Universal Server & Dashboard Architecture (Unified System)

To ensure scalability, maintainability, and rapid application development, the system has been unified into a single modular architecture. This allows any number of applications (LYRN, RemoDash, etc.) to run on the same core infrastructure while maintaining strict data isolation.

### 1. Unified Server Entry Point
-   **File:** `server.py` (Root Directory)
-   **Logic:** This script is designed to be executed from *within* an application directory (e.g., `cd LYRN_v5 && python ../server.py`).
-   **Behavior:**
    -   It detects the Current Working Directory (CWD) as the application context.
    -   It loads `settings.json` and `port.txt` from the CWD.
    -   It dynamically loads API routers from the `backend/` directory based on the `modules` list defined in `settings.json`.
    -   It serves static files (the dashboard) from the application directory (or `web/` if present).

### 2. Modular Backend
-   **Directory:** `backend/`
-   **Structure:** Logic is broken down into discrete, reusable modules:
    -   `system.py`: Health checks, OS info, Power control.
    -   `auth.py`: Centralized token verification (`admin_token.txt`).
    -   `files.py`: File operations, upload, zip.
    -   `git_mgr.py`: Git repository management.
    -   `chat.py`: LLM chat orchestration and history.
    -   `automation.py`: Jobs, Cron, Scripts.
    -   `vlc.py`, `shortcuts.py`, `models.py`, `snapshots.py`, etc.
-   **Config:** `settings.json` now includes a `"modules"` list (e.g., `["chat", "system"]`) which tells `server.py` exactly which routers to mount. This keeps lightweight apps (like RemoDash) free of heavy dependencies (like Chat).

### 3. Universal Dashboard
-   **File:** `dashboard.html` (Identical copy in every app folder)
-   **Philosophy:** "One Dashboard to Rule Them All."
-   **Behavior:**
    -   The dashboard is feature-agnostic. It queries the server configuration on load.
    -   Features (like the LLM Status Light) are toggled visible only if the corresponding backend module is active.
    -   It supports app-specific theming (colors, layout) which are persisted in `localStorage`.
    -   Modules (Chat, Terminal, Builder) are loaded as iframes from the `modules/` folder, which remains specific to the app.

### 4. Setup Wizard
-   **File:** `setup_wizard.py`
-   **Purpose:** One script to rule installation.
-   **Features:**
    -   Detects OS (Windows/Linux/Android/Mac).
    -   Installs unified dependencies from `requirements.txt`.
    -   Installs Tailscale automatically.
    -   Configures specific apps (LYRN or RemoDash) by generating `port.txt` and `admin_token.txt` in their respective folders.

### Why This Matters
-   **Development Speed:** Improving the `dashboard.html` or `backend/files.py` instantly benefits *all* applications using the system.
-   **Stability:** A single, tested server core reduces the surface area for bugs compared to maintaining divergent scripts.
-   **Isolation:** Despite sharing code, app data (logs, chat history, settings) never leaks because the server process is sandboxed to its startup directory.
