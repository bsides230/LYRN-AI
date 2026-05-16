import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# I see... the substitution didn't work because `<!-- SCI-FI BACKGROUND MONITORING LAYER -->` wasn't there when I tried to replace it? Let me check.
match = re.search(r'<!-- SCI-FI BACKGROUND MONITORING LAYER -->', content)
if match:
    print("Found background comment")
else:
    print("Not found")
