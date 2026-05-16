import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Let's check where the app tray logic is.
# We inserted it right after DOMContentLoaded.
# The `renderTray` function relies on MODULE_REGISTRY.
# Let's ensure the toggleWindow function exists.

# Actually, the selector in playwright might be wrong, or the tray is hidden.
# `page.locator('.tray-item:has-text("Job Manager")').click()`

# Let's explicitly define a global variable for MODULE_REGISTRY just in case scope is an issue.
content = content.replace("const MODULE_REGISTRY = [", "window.MODULE_REGISTRY = [\n")
content = content.replace("MODULE_REGISTRY.forEach", "window.MODULE_REGISTRY.forEach")
content = content.replace("MODULE_REGISTRY.find", "window.MODULE_REGISTRY.find")

with open("LYRN_v6/dashboard-monitoring.html", "w") as f:
    f.write(content)
