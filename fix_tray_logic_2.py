import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Let's fix the MODULE_REGISTRY logic since we overrode the tray loading
# And the new dashboard-monitoring.html might be missing it if the script block order is weird

content = content.replace("renderTray();", "if(typeof renderTray === 'function') renderTray();")

with open("LYRN_v6/dashboard-monitoring.html", "w") as f:
    f.write(content)
