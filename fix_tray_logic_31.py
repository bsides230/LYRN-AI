import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Let's see the entire script tag contents to see what's wrong.
script_match = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
if len(script_match) > 1:
    print(script_match[1][:1500]) # Print first 1500 chars
