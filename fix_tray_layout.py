import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Make the tray grid horizontal wrapped instead of single column vertical by adjusting the grid
tray_css_fix = """
.tray-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
    gap: 15px;
    margin-top: 20px;
    max-height: 400px;
    overflow-y: auto;
}
"""

content = content.replace("grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));", "grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));\n    max-height: 400px;\n    overflow-y: auto;")

# Also, the tray icons were stacking vertically because the modal was narrow.
# Let's ensure the modal is wide enough.
content = content.replace("width: 600px;", "width: 700px;")

with open("LYRN_v6/dashboard-monitoring.html", "w") as f:
    f.write(content)
