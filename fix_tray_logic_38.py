import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Let's see if <body> tag exists
match = re.search(r'<body', content)
if match:
    print("Found <body")
else:
    print("Not found <body")
