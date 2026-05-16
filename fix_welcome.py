import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Disable welcome overlay popping up on the monitoring dashboard
content = content.replace("openWelcome();", "// openWelcome();")

# Remove dock logic from the old script that breaks when dock is hidden
content = re.sub(r'function updateDockPos.*?}', 'function updateDockPos() {}', content, flags=re.DOTALL)

with open("LYRN_v6/dashboard-monitoring.html", "w") as f:
    f.write(content)
