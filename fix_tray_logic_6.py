import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Let's see if the module registry array is loading properly and if it's being added to DOM.
# Oh, we set `const MODULE_REGISTRY` in the file.

# Check if `renderTray` is being defined inside the script correctly.
match = re.search(r'function renderTray\(\) \{.*?\}', content, re.DOTALL)
if match:
    print("Found renderTray")
else:
    print("NOT FOUND renderTray")
