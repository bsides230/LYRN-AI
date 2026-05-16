import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Let's use get_by_text("[ LAUNCH SYSTEMS ]") instead of get_by_role in playwright.
# Wait, I am not in the playwright script, I need to see what's generated.
# Ah, I replaced the text `[ LAUNCH SYSTEMS ]` with something else? No, it's there.
# It might have multiple spaces. Let's make it EXACTLY `[ LAUNCH SYSTEMS ]`.

match = re.search(r'<button id="sf-app-tray-btn".*?>(.*?)</button>', content, re.DOTALL)
if match:
    print(f"Button text: '{match.group(1)}'")
