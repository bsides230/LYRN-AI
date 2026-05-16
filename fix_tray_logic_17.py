import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Let's see if we accidentally deleted the trayBtn.onclick assignment
match = re.search(r'trayBtn\.onclick = \(\) => \{[\s\S]*?\};', content, re.DOTALL)
if match:
    print(match.group(0))
else:
    print("trayBtn.onclick NOT FOUND")
