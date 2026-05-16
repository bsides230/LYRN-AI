import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Step: Hide old dock elements completely using regex so it doesn't intercept pointer events
content = re.sub(r'(<div id="floating-dock".*?>)', r'<div id="floating-dock" style="display: none;">', content)
content = re.sub(r'(<div id="dock".*?>)', r'<div id="dock" style="display: none;">', content)

# Remove old dock CSS / logic that might be un-hiding it
content = re.sub(r'document\.getElementById\(\'floating-dock\'\)\.style\.bottom = \'20px\';', '', content)
content = re.sub(r'document\.getElementById\(\'floating-dock\'\)\.style\.bottom = \'-100px\';', '', content)

with open("LYRN_v6/dashboard-monitoring.html", "w") as f:
    f.write(content)
