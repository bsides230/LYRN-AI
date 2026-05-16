import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Let's see the DOM element structure for the tray button
match = re.search(r'<button id="sf-app-tray-btn".*?</button>', content, re.DOTALL)
if match:
    print("Found button HTML")
else:
    print("Missing button HTML")
