import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Let's override the theme dropdown in the settings panel to use our specific palettes
theme_dropdown_new = """
                    <div class="settings-row">
                        <span>Theme Color</span>
                        <select id="setting-theme" onchange="changeSFTheme(this.value)">
                            <option value="berry">Berry (Cyan/Blue)</option>
                            <option value="plum">Plum (Purple)</option>
                            <option value="lemon">Lemon (Yellow)</option>
                            <option value="lime">Lime (Green)</option>
                            <option value="tangerine">Tangerine (Orange)</option>
                            <option value="light-grey">Light Grey</option>
                            <option value="dark-grey">Dark Grey</option>
                        </select>
                    </div>
"""

# Find the old theme dropdown and replace it
content = re.sub(r'<div class="settings-row">[\s\S]*?id="setting-theme"[\s\S]*?</div>', theme_dropdown_new, content)

# Add the changeSFTheme function
theme_js = """
        function changeSFTheme(themeName) {
            document.body.setAttribute('data-theme', themeName);
            appSettings.theme = themeName;
            saveSettings();
        }

        // Initial load
        setTimeout(() => {
            const savedTheme = appSettings.theme;
            if(['berry', 'plum', 'lemon', 'lime', 'tangerine', 'light-grey', 'dark-grey'].includes(savedTheme)) {
                document.body.setAttribute('data-theme', savedTheme);
                document.getElementById('setting-theme').value = savedTheme;
            } else {
                document.body.setAttribute('data-theme', 'berry'); // Default fallback
            }
        }, 500);
"""
content = content.replace("function loadSettings() {", theme_js + "\n        function loadSettings() {")


with open("LYRN_v6/dashboard-monitoring.html", "w") as f:
    f.write(content)
