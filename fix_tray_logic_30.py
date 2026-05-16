import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Let's see the DOM element structure for the tray itself
match = re.search(r'<div class="tray-grid" id="sf-tray-grid">.*?</div>', content, re.DOTALL)
if match:
    print("Found grid HTML")
else:
    print("Missing grid HTML")
