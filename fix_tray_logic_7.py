import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Playwright fails to click on the tray item because maybe it's not generating correctly?
# The `MODULE_REGISTRY` in dashboard-monitoring.html:
# Let's check how we loop it.
# `window.MODULE_REGISTRY.forEach(mod => { ... })`
# Wait, did we change `const MODULE_REGISTRY` to `window.MODULE_REGISTRY = []` but then we did string replacement incorrectly?

match = re.search(r'window\.MODULE_REGISTRY = \[.*?\];', content, re.DOTALL)
if match:
    print("Found window.MODULE_REGISTRY")
else:
    print("NOT FOUND window.MODULE_REGISTRY")
