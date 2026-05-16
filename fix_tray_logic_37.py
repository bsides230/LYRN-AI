import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Let's see what is inside <body>
match = re.search(r'<body.*?>', content)
if match:
    print(match.group(0))

# Let's print the first 500 chars of body
body_start = content.find('<body')
if body_start != -1:
    print(content[body_start:body_start+500])
