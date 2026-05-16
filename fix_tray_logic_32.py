import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Let's fix the duplication of `renderTray`
# We have a global `renderTray` defined in the first script tag.
# We also have a `renderTray` function defined *inside* DOMContentLoaded.

# Let's clean this up.
content = re.sub(r'function renderTray\(\) \{[\s\S]*?\}\s*trayBtn\.onclick = \(\) => \{[\s\S]*?\};\s*', '', content)

with open("LYRN_v6/dashboard-monitoring.html", "w") as f:
    f.write(content)
