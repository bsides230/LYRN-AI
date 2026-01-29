# Build Notes

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

## Philosophy & Rules (Ported)

-   **Efficiency and Accessibility:** The primary goal is to create a powerful AI cognition framework that is lightweight enough to run on standard consumer hardware.
-   **Structured Memory over Prompt Injection:** All core context—personality, memory, goals—lives in structured text files and memory tables. The LLM reasons from this stable foundation rather than having it repeatedly injected into a limited context window.
-   **Simplicity and Robustness:** The architecture is inspired by the simplicity of 1990s text-based game parsers. The framework's job is to be a robust, simple system for moving data; the LLM's job is to do the heavy lifting of reasoning.
-   **UI Development:** New modules must be implemented as single-file solutions (combining HTML, CSS, and JS) in `LYRN_v5/modules/` to facilitate loading on smaller systems and minimize floating dependencies. UI must strictly follow `LYRN Style Guide.html`.
