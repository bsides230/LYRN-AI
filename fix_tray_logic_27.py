import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Let's see the SECOND script tag
script_match = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
if len(script_match) > 1:
    script_2 = script_match[1]
    # search for trayBtn
    if 'trayBtn' in script_2:
        print("trayBtn found in script 2")
    else:
        print("trayBtn missing from script 2!")
