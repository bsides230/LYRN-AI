import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Let's inspect the MODULE_REGISTRY logic again.
# The app tray is looking for an element containing "Job Manager"
# Let's see what MODULE_REGISTRY actually looks like.

match = re.search(r'const MODULE_REGISTRY = \[.*?\];', content, re.DOTALL)
if match:
    print(match.group(0))
