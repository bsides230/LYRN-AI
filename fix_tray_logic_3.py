import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Let's see why renderTray isn't firing.
# Ah, MODULE_REGISTRY is parsed at the top. Let's make sure it's accessible.
# In the original, it was `const MODULE_REGISTRY = [...]`. It should still be there.
# But `renderTray` is defined inside a `<script>` block.

# Let's force it to render the tray explicitly when clicking the button instead of relying on DOMContentLoaded.
tray_logic_fix = """
        let trayOpen = false;

        trayBtn.onclick = () => {
            trayOpen = !trayOpen;
            if(trayOpen) {
                renderTray(); // Ensure it builds the grid
                appTray.classList.add('open');
            } else {
                appTray.classList.remove('open');
            }
        };
"""

content = re.sub(r'let trayOpen = false;\s+trayBtn\.onclick = \(\) => {[\s\S]*?};', tray_logic_fix, content)

with open("LYRN_v6/dashboard-monitoring.html", "w") as f:
    f.write(content)
