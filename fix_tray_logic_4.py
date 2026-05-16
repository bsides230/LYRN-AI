import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Let's see how MODULE_REGISTRY is defined.
# If it's defined after the script block, that's the issue.
# Let's search for MODULE_REGISTRY in dashboard-monitoring.html

match = re.search(r'const MODULE_REGISTRY = \[.*?\];', content, re.DOTALL)
if match:
    module_registry_str = match.group(0)
    print("Found MODULE_REGISTRY")
else:
    print("NOT FOUND MODULE_REGISTRY")
