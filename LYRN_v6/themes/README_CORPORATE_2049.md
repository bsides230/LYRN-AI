# Corporate 2049 Theme - Implementation Notes

## Overview
A new futuristic cinematic analysis dashboard skin has been added to the LYRN project: **Corporate 2049**. This theme features a cool-toned, technical, and holographic aesthetic resembling high-end sci-fi investigative environments. It relies on a dark green-black background, glassy panels, thin glowing wireframes, and soft bloom, avoiding chunky retro terminal blocks.

## What Files Changed
1. `LYRN_v6/themes/corporate-2049.css` (New File): Contains all the theme overrides for the dashboard shell, as well as reusable design classes for future module use, and minimal fallback styling for existing iframe modules.
2. `LYRN_v6/dashboard.html`:
   - Added a `<link>` to the new `corporate-2049.css`.
   - Added `<option value="corporate-2049">Corporate 2049</option>` to the settings theme dropdown to allow selection of this new skin.
   - Updated the logic assigning the selected theme from `localStorage` to include `corporate-2049`.
3. `LYRN_v6/modules/*.html` and `LYRN_v6/modules/Gamemaster/*.html`: Added `<link>` tags pointing to `corporate-2049.css` so that iframe modules receive fallback styles when the dashboard broadcasts `data-theme="corporate-2049"`.

## How the Skin is Selected
The skin can be selected from the `Settings` menu (gear icon in the dock). Under the `Appearance` section, use the `Theme` dropdown to select `Corporate 2049`. This value is saved to `localStorage` and persists across app reloads. When changed, the dashboard immediately updates `body[data-theme="..."]` and broadcasts the `THEME_CHANGE` event via `postMessage` to all active iframe modules.

## How Future Modules Should Adopt the Corporate 2049 Theme
To build new modules (or update existing ones) that fully utilize the 2049 visual language without relying on the dashboard shell's global overrides, use the following newly added CSS utility classes provided in `corporate-2049.css`:

* `.corp2049-shell`
* `.corp2049-topbar`
* `.corp2049-dock`
* `.corp2049-panel`, `.corp2049-glass`, `.corp2049-window`
* `.corp2049-frame`
* `.corp2049-card`
* `.corp2049-button`
* `.corp2049-input`
* `.corp2049-status` (with variants `.warning`, `.danger`)
* `.corp2049-graph`, `.corp2049-overlay`

## Remaining Module Redesign TODOs
Currently, all modules rely on the `body[data-theme="corporate-2049"]` CSS overrides provided at the bottom of the `corporate-2049.css` file as a *fallback*. This ensures they do not visually clash with the new dashboard shell, giving them a translucent, cyan-bordered dark aesthetic.

**Future Work:**
Each module (e.g., `Chat Interface.html`, `JobManager.html`) should be revisited and its internal HTML structure rewritten to explicitly use the `.corp2049-*` classes (or similar theming tokens) for their layout, buttons, inputs, and panels. Once a module is rewritten to use the design system explicitly, it will not require the generic global fallbacks.
