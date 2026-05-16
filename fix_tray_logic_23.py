import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Make sure the app tray HTML is present
match = re.search(r'<div id="sf-app-tray">.*?</div>', content, re.DOTALL)
if match:
    print(match.group(0))
