import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Let's see how the JS click event is bound
match = re.search(r'let trayOpen = false;.*?(?=</script>|function )', content, re.DOTALL)
if match:
    print(match.group(0))
