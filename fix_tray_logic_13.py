import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

fix_tray_code = """
        // TRAY LOGIC
        const trayBtn = document.getElementById('sf-app-tray-btn');
        const appTray = document.getElementById('sf-app-tray');
        const trayGrid = document.getElementById('sf-tray-grid');

        let trayOpen = false;

        function renderTray() {
            if(!trayGrid) return;
            trayGrid.innerHTML = '';

            const localRegistry = [
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

            localRegistry.forEach(mod => {
                const item = document.createElement('div');
                item.className = 'tray-item';
                item.innerHTML = `<div class="tray-icon">${mod.icon}</div><div class="tray-name">${mod.name}</div>`;
                item.onclick = () => {
                    toggleWindow(mod);
                    trayOpen = false;
                    appTray.classList.remove('open');
                };
                trayGrid.appendChild(item);
            });

            // Add settings button to tray
            const settingsItem = document.createElement('div');
            settingsItem.className = 'tray-item';
            settingsItem.innerHTML = `<div class="tray-icon">⚙️</div><div class="tray-name">Settings</div>`;
            settingsItem.onclick = () => {
                if(document.getElementById('settings-panel').classList.contains('open')) {
                    closeSettings();
                } else {
                    openSettings();
                }
                trayOpen = false;
                appTray.classList.remove('open');
            };
            trayGrid.appendChild(settingsItem);
        }

        trayBtn.onclick = () => {
            trayOpen = !trayOpen;
            if(trayOpen) {
                renderTray();
                appTray.classList.add('open');
            } else {
                appTray.classList.remove('open');
            }
        };
"""

# Let's remove any previous occurrences of tray logic
content = re.sub(r'// TRAY LOGIC.*?\}\s*\};\s*', '', content, flags=re.DOTALL)
content = re.sub(r'let trayOpen = false;\s*trayBtn\.onclick = \(\) => \{[\s\S]*?\}\s*;\s*', '', content, flags=re.DOTALL)

# Insert it fresh before loadSettings()
content = content.replace("loadSettings();", fix_tray_code + "\n            loadSettings();")

with open("LYRN_v6/dashboard-monitoring.html", "w") as f:
    f.write(content)
