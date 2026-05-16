import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Make sure the app tray is correctly populated by the new function. Let's make sure renderTray runs once to setup.
content = content.replace("document.addEventListener('DOMContentLoaded', () => {", "document.addEventListener('DOMContentLoaded', () => {\n        renderTray();")

with open("LYRN_v6/dashboard-monitoring.html", "w") as f:
    f.write(content)
