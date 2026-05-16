import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Let's see if there is any issue with the `renderTray` or `MODULE_REGISTRY` being inside the window.onload/DOMContentLoaded but not actually executing.

match = re.search(r'function renderTray\(\).*?\}', content, re.DOTALL)
if match:
    print(match.group(0))
else:
    print("renderTray NOT FOUND")

match = re.search(r'const MODULE_REGISTRY = \[.*?\];', content, re.DOTALL)
if match:
    print("MODULE_REGISTRY FOUND")
else:
    print("MODULE_REGISTRY NOT FOUND")
