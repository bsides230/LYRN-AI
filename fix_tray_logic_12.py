import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Ah! The click is failing because the `MODULE_REGISTRY` doesn't get populated into the DOM during `DOMContentLoaded` because the tray isn't strictly necessary until clicked. BUT my `renderTray` function relies on `MODULE_REGISTRY`. Let's ensure the tray is populated properly.

# Let's change how `renderTray` works so it's guaranteed to have the list.
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

content = re.sub(r'// TRAY LOGIC.*?trayBtn\.onclick = \(\) => \{[\s\S]*?};', tray_logic_fix, content) # remove old

# Now insert the new tray logic cleanly before loadSettings()
content = content.replace("        let trayOpen = false;", tray_logic_fix) # Replace the previous injected tray_logic_fix variable

content = re.sub(r'        let trayOpen = false;\s*trayBtn\.onclick = \(\) => \{\s*trayOpen = !trayOpen;\s*if\(trayOpen\) \{\s*renderTray\(\); // Ensure it builds the grid\s*appTray\.classList\.add\(\'open\'\);\s*\} else \{\s*appTray\.classList\.remove\(\'open\'\);\s*\}\s*\};\s*', tray_code, content)

with open("LYRN_v6/dashboard-monitoring.html", "w") as f:
    f.write(content)
