import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Let's see the DOM element structure for the tray itself
match = re.search(r'<div id="sf-app-tray">.*?</div>', content, re.DOTALL)
if match:
    print("Found tray HTML")
else:
    print("Missing tray HTML")
