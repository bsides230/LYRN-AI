import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

tray_js = """
        // TRAY LOGIC
        const trayBtn = document.getElementById('sf-app-tray-btn');
        const appTray = document.getElementById('sf-app-tray');
        const trayGrid = document.getElementById('sf-tray-grid');

        let trayOpen = false;

        trayBtn.onclick = () => {
            trayOpen = !trayOpen;
            if(trayOpen) {
                appTray.classList.add('open');
                renderTray();
            } else {
                appTray.classList.remove('open');
            }
        };

        // Close tray when clicking outside
        document.addEventListener('mousedown', (e) => {
            if(trayOpen && !appTray.contains(e.target) && e.target !== trayBtn) {
                trayOpen = false;
                appTray.classList.remove('open');
            }
        });

        function renderTray() {
            trayGrid.innerHTML = '';
            MODULE_REGISTRY.forEach(mod => {
                const item = document.createElement('div');
                item.className = 'tray-item';
                item.innerHTML = `<div class="tray-icon">${mod.icon}</div><div class="tray-name">${mod.name}</div>`;
                item.onclick = () => {
                    toggleWindow(mod); // Uses existing floating window logic!
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
"""

# Insert right after the document.addEventListener('DOMContentLoaded', ...)
content = content.replace("document.addEventListener('DOMContentLoaded', () => {", "document.addEventListener('DOMContentLoaded', () => {\n" + tray_js)

with open("LYRN_v6/dashboard-monitoring.html", "w") as f:
    f.write(content)
