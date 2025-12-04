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

## v4.2.9 - RWI Builder Enhancements (2025-12-05)

This update adds requested features to the HTML RWI Builder.

- **RWI Builder Improvements:**
    - **File Lock:** Added a toggle to lock the master prompt from being overwritten by the builder. The state is saved in `build_prompt/builder_config.json`.
    - **Pinning:** Added functionality to pin components to the top of the list. Order and pin status are automatically saved.
    - **Theme Toggle:** Added a theme toggle in the new footer to switch between Light and Dark modes.
    - **Renamed HTML:** Renamed `index.html` to `rwi_builder.html` for better linking structure.

- **GUI Changes:**
    - Updated `lyrn_sad_v4.2.9.py` to point to the new `rwi_builder.html` URL.

- **Versioning:**
    - The main application file has been versioned to `lyrn_sad_v4.2.9.py`.
    - The previous version `lyrn_sad_v4.2.8.py` has been archived in `deprecated/Old/`.

### Logging
- Updated RWI Server to handle settings endpoints.
