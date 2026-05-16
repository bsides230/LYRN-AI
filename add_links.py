import re

# 1. Add link in existing dashboard.html
with open("LYRN_v6/dashboard.html", "r") as f:
    dash_content = f.read()

nav_btn_1 = """            <button class="bar-btn" title="Switch to Sci-Fi Monitoring" onclick="window.location.href='dashboard-monitoring.html'">[SCI-FI]</button>\n"""

# Insert before Help button
dash_content = dash_content.replace('<button class="bar-btn" title="Help" onclick="openWelcome()">?</button>', nav_btn_1 + '            <button class="bar-btn" title="Help" onclick="openWelcome()">?</button>')

with open("LYRN_v6/dashboard.html", "w") as f:
    f.write(dash_content)


# 2. Add back-link in new dashboard-monitoring.html
with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    mon_content = f.read()

nav_btn_2 = """            <button class="bar-btn" style="color: var(--theme-primary);" title="Switch to Classic Desktop" onclick="window.location.href='dashboard.html'">[CLASSIC]</button>\n"""
mon_content = mon_content.replace('<button class="bar-btn" title="Help" onclick="openWelcome()">?</button>', nav_btn_2 + '            <button class="bar-btn" title="Help" onclick="openWelcome()">?</button>')

with open("LYRN_v6/dashboard-monitoring.html", "w") as f:
    f.write(mon_content)
