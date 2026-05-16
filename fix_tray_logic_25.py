import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Ah! The click handler was lost!
# Let's add it back.
fix_code = """
        let trayOpen = false;

        const trayBtn = document.getElementById('sf-app-tray-btn');
        const appTray = document.getElementById('sf-app-tray');

        if (trayBtn && appTray) {
            trayBtn.onclick = () => {
                trayOpen = !trayOpen;
                if(trayOpen) {
                    renderTray();
                    appTray.classList.add('open');
                } else {
                    appTray.classList.remove('open');
                }
            };
        }
"""

content = content.replace("let trayOpen = false;", fix_code)

with open("LYRN_v6/dashboard-monitoring.html", "w") as f:
    f.write(content)
