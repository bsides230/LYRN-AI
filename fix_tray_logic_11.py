import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Let's verify `MODULE_REGISTRY` in the page and why `renderTray` is not rendering it properly.
# The HTML uses `MODULE_REGISTRY` array of objects.

fix_script = """
    <script>
        // Move MODULE_REGISTRY and renderTray explicitly outside to ensure scope
        const MODULE_REGISTRY = [
            { id: "mod_chat", file: "Chat Interface.html", name: "Chat", icon: "💬" },
            { id: "mod_claude_code", file: "ClaudeCode.html", name: "Claude Code", icon: "🤖" },
            { id: "mod_builder", file: "Snapshot Builder.html", name: "Snapshot Builder", icon: "🛠️" },
            { id: "mod_file_tree", file: "FileTreeViewer.html", name: "File Tree Viewer", icon: "📁" },
            { id: "mod_models", file: "ModelController.html", name: "Model Controller", icon: "🧠" },
            { id: "mod_model_manager", file: "ModelManager.html", name: "Model Manager", icon: "📦" },
            { id: "mod_logs", file: "LogViewer.html", name: "System Logs", icon: "📜" },
            { id: "mod_server_status", file: "ServerStatus.html", name: "System Status", icon: "📊" },
            { id: "mod_job_mgr", file: "JobManager.html", name: "Job Manager", icon: "🦺" },
            { id: "mod_delta_mgr", file: "DeltaManager.html", name: "Delta Manager", icon: "Δ" },
        ];

        function renderTray() {
            const trayGrid = document.getElementById('sf-tray-grid');
            const appTray = document.getElementById('sf-app-tray');
            if(!trayGrid || !appTray) return;

            trayGrid.innerHTML = '';
            MODULE_REGISTRY.forEach(mod => {
                const item = document.createElement('div');
                item.className = 'tray-item';
                item.innerHTML = `<div class="tray-icon">${mod.icon}</div><div class="tray-name">${mod.name}</div>`;
                item.onclick = () => {
                    toggleWindow(mod);
                    appTray.classList.remove('open');
                };
                trayGrid.appendChild(item);
            });
        }
    </script>
"""

# Find <head> and insert script at the end of head
content = content.replace("</head>", fix_script + "\n</head>")

# Remove duplicate window.MODULE_REGISTRY
content = re.sub(r'window\.MODULE_REGISTRY = \[.*?\];', '', content, flags=re.DOTALL)

with open("LYRN_v6/dashboard-monitoring.html", "w") as f:
    f.write(content)
