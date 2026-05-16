import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Let's see where the app tray button is and if it has the right ID.
match = re.search(r'<button id="sf-app-tray-btn".*?>.*?</button>', content, re.DOTALL)
if match:
    print(match.group(0))
