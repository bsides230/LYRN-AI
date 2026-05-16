import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Let's see how `trayBtn.onclick` is bound.
match = re.search(r'const trayBtn = document\.getElementById\(\'sf-app-tray-btn\'\);.*?(?=function )', content, re.DOTALL)
if match:
    print(match.group(0))
else:
    print("trayBtn logic NOT FOUND")
