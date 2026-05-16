import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Ah! `window.MODULE_REGISTRY` is defined AFTER `renderTray` is called inside `DOMContentLoaded`.
# Because I injected the `tray_js` right after `DOMContentLoaded` hook, but `MODULE_REGISTRY` is declared later in the file.

# Let's move MODULE_REGISTRY to the very top of the script tag.

# Extract the registry
match = re.search(r'window\.MODULE_REGISTRY = \[.*?\];', content, re.DOTALL)
if match:
    registry_str = match.group(0)
    # Remove it from its current location
    content = content.replace(registry_str, "")

    # Insert it right after <script>
    content = content.replace("<script>", f"<script>\n{registry_str}\n")

with open("LYRN_v6/dashboard-monitoring.html", "w") as f:
    f.write(content)
