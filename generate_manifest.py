import csv
from start_lyrn import app

manifest_data = []
for route in app.routes:
    if hasattr(route, "methods") and hasattr(route, "path"):
        methods = ", ".join(route.methods) if route.methods else ""
        manifest_data.append({
            "Path": route.path,
            "Methods": methods,
            "Name": route.name,
            "Tags": ", ".join(route.tags) if hasattr(route, "tags") and route.tags else ""
        })

with open("api_manifest.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["Path", "Methods", "Name", "Tags"])
    writer.writeheader()
    writer.writerows(manifest_data)
