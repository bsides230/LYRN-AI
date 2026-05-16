import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Let's see if the renderTray function is actually working and inserting DOM elements
# Is MODULE_REGISTRY available to `renderTray()`? `MODULE_REGISTRY` is defined in another `<script>` tag. Is it executing first?
# We put `MODULE_REGISTRY` in a `<script>` tag at the end of `<head>`.
# Let's move the `renderTray` call inside `DOMContentLoaded` to guarantee the DOM is ready.

fix_code = """
        document.addEventListener('DOMContentLoaded', () => {
            renderTray();
"""

content = content.replace("document.addEventListener('DOMContentLoaded', () => {", fix_code)

with open("LYRN_v6/dashboard-monitoring.html", "w") as f:
    f.write(content)
