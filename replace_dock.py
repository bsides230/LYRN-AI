import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# We need to hide/remove the original dock and insert our App Tray button and Modal

app_tray_html = """
    <!-- APP TRAY BUTTON (replaces dock) -->
    <button id="sf-app-tray-btn" style="position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%); z-index: 99999; background: var(--theme-dim); border: 1px solid var(--theme-primary); color: var(--theme-primary); padding: 10px 30px; font-family: 'JetBrains Mono'; font-weight: bold; cursor: pointer; clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px); box-shadow: 0 0 15px var(--theme-glow);">
        [ LAUNCH SYSTEMS ]
    </button>

    <!-- APP TRAY MODAL -->
    <div id="sf-app-tray">
        <div class="sf-title">AVAILABLE SUBSYSTEMS</div>
        <div class="sf-accent-line"></div>
        <div class="tray-grid" id="sf-tray-grid">
            <!-- Populated via JS -->
        </div>
    </div>
"""

# Insert the app tray HTML right after the background layer
content = content.replace('<!-- SCI-FI BACKGROUND MONITORING LAYER -->', app_tray_html + '\n    <!-- SCI-FI BACKGROUND MONITORING LAYER -->')

# Hide original dock via CSS injection since the JS relies on it existing
hide_dock_css = """
        /* HIDE ORIGINAL DOCK */
        #dock-container { display: none !important; }
"""
content = content.replace('/* FLOATING WINDOWS (Overriding default styles for the new theme) */', hide_dock_css + '\n/* FLOATING WINDOWS (Overriding default styles for the new theme) */')


with open("LYRN_v6/dashboard-monitoring.html", "w") as f:
    f.write(content)
