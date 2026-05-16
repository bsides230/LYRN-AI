import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Make sure trayBtn.onclick is correctly bound in DOMContentLoaded
fix_code = """
        document.addEventListener('DOMContentLoaded', () => {
            const trayBtn = document.getElementById('sf-app-tray-btn');
            const appTray = document.getElementById('sf-app-tray');

            if (trayBtn && appTray) {
                let trayOpen = false;
                trayBtn.onclick = () => {
                    trayOpen = !trayOpen;
                    if(trayOpen) {
                        appTray.classList.add('open');
                        if(typeof renderTray === 'function') renderTray();
                    } else {
                        appTray.classList.remove('open');
                    }
                };

                document.addEventListener('mousedown', (e) => {
                    if(trayOpen && !appTray.contains(e.target) && e.target !== trayBtn) {
                        trayOpen = false;
                        appTray.classList.remove('open');
                    }
                });
            }
"""

content = content.replace("document.addEventListener('DOMContentLoaded', () => {", fix_code)

# Let's remove the stray old code if present
content = re.sub(r'if\(typeof renderTray === \'function\'\) renderTray\(\);[\s\S]*?function renderTray\(\) \{[\s\S]*?\}', '', content)

with open("LYRN_v6/dashboard-monitoring.html", "w") as f:
    f.write(content)
