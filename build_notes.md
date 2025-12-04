## v4.2.8 - HTML RWI Builder (2025-12-04)

This update introduces a new HTML-based module for building the RWI system prompt, replacing the old `SystemPromptBuilderPopup`.

- **New RWI Builder Module:**
    - A new web-based interface has been created in `modules/rwi_builder/`.
    - It runs on a local Python server (port 8000) started by the main application.
    - The interface allows users to create, edit, reorder, and toggle prompt components.
    - It communicates with the backend via API endpoints to read and write configuration files in `build_prompt/`.
    - Style matches the `LYRN Style Guide.html`.

- **GUI Changes:**
    - The "System Prompt" button now opens the new HTML interface in the default web browser.
    - Removed `SystemPromptBuilderPopup`, `ComponentBuilderPopup`, and `FullRWIViewerPopup` classes and files.
    - Removed `full_rwi_viewer_popup.py`.

- **Versioning:**
    - The main application file has been versioned to `lyrn_sad_v4.2.8.py`.
    - The previous version `lyrn_sad_v4.2.7.py` (and `.pyw`) have been archived in `deprecated/Old/`.

### Logging
- No changes to logging mechanisms were necessary for this update.
