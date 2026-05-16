import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Let's completely restructure the script part of dashboard-monitoring.html to make sure it loads.
# I will output the script part to see what is currently there.
script_match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
if script_match:
    print(script_match.group(0))
