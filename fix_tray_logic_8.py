import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Let's inspect renderTray:
match = re.search(r'function renderTray\(\) \{.*?\}', content, re.DOTALL)
if match:
    print(match.group(0))
