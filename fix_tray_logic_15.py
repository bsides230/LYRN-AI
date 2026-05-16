import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Let's see the full renderTray function
match = re.search(r'function renderTray\(\) \{.*?(?=</script>|function )', content, re.DOTALL)
if match:
    print(match.group(0))
