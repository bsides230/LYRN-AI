import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Let's see if the button is even in the HTML.
match = re.search(r'<button id="sf-app-tray-btn".*?>.*?</button>', content, re.DOTALL)
if match:
    print(match.group(0))
else:
    print("Button not found.")
