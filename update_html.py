import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Update title
content = re.sub(r'<title>.*?</title>', '<title>LYRN Command Center (Monitoring)</title>', content)

# Write it back for now
with open("LYRN_v6/dashboard-monitoring.html", "w") as f:
    f.write(content)
