# Corporate Terminal Theme - Implementation Notes

## Overview
A new retro-futurist corporate sci-fi terminal dashboard skin has been added to the LYRN project. This theme applies dark industrial colors, an amber/gold monochrome UI glow, grid overlays, and command-console typography to create an elegant operations dashboard environment.

## What Files Changed
1. `LYRN_v6/themes/corporate-terminal.css` (New File): Contains all the theme overrides for the dashboard shell, as well as reusable design classes for future module use, and minimal fallback styling for existing iframe modules.
2. `LYRN_v6/dashboard.html`:
   - Added a `<link>` to the new `corporate-terminal.css`.
   - Replaced the "Dark Mode" boolean toggle with a `<select>` dropdown menu to accommodate multiple themes (Dark, Light, Corporate Terminal).
   - Updated the `toggleTheme()` JavaScript function to use string values.
3. `LYRN_v6/modules/*.html` and `LYRN_v6/modules/Gamemaster/*.html`: Added `<link>` tags pointing to `corporate-terminal.css` so that iframe modules can receive fallback styles when the dashboard broadcasts `data-theme="corporate-terminal"`.

## How the Skin is Selected
The skin can be selected from the `Settings` menu (gear icon in the dock). Under the `Appearance` section, use the `Theme` dropdown to select `Corporate Terminal`. This value is saved to `localStorage` and persists across app reloads. When changed, the dashboard immediately updates `body[data-theme="..."]` and broadcasts the `THEME_CHANGE` event via `postMessage` to all active iframe modules.

## How Future Modules Should Adopt the Dashboard Skin
To build new modules (or update existing ones) that fully utilize the corporate terminal visual language without relying on the dashboard shell's global overrides, use the following newly added CSS utility classes provided in `corporate-terminal.css`:

* `.corp-shell`
* `.corp-topbar`
* `.corp-taskbar`
* `.corp-dock`
* `.corp-panel`
* `.corp-card`
* `.corp-button`
* `.corp-input`
* `.corp-status`
* `.corp-log`
* `.corp-window`
* `.corp-module-frame`

## Remaining Module Redesign TODOs
Currently, all modules rely on the `body[data-theme="corporate-terminal"]` CSS overrides provided at the bottom of the `corporate-terminal.css` file as a *fallback*. This ensures they do not visually clash with the new dashboard shell.

**Future Work:**
Each module (e.g., `Chat Interface.html`, `JobManager.html`) should be revisited and its internal HTML structure rewritten to explicitly use the `.corp-*` classes for their layout, buttons, inputs, and panels. Once a module is rewritten to use the design system explicitly, it will not require the generic global fallbacks.