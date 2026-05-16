import re
import shutil

# Step 1: Reset the file
shutil.copyfile("LYRN_v6/dashboard.html", "LYRN_v6/dashboard-monitoring.html")

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Step 2: Update title and CSS links
content = re.sub(r'<title>.*?</title>', '<title>LYRN Command Center (Monitoring)</title>', content)
content = re.sub(r'<link rel="stylesheet" href="themes/corporate-terminal.css" />\s*<link rel="stylesheet" href="themes/corporate-2049.css" />', '<link rel="stylesheet" href="themes/sci-fi-monitoring.css" />', content)

# Step 3: Add data-theme to body and inject background layer + app tray
bg_layer = """
    <!-- SCI-FI BACKGROUND MONITORING LAYER -->
    <div id="sf-background-layer">

        <div class="sf-panel" id="sys-status-panel">
            <div class="sf-title">SYS.CORE</div>
            <div class="sf-accent-line"></div>
            <div class="data-row"><span class="data-label">CPU LOAD:</span><span class="data-value" id="sf-cpu">--%</span></div>
            <div class="data-row"><span class="data-label">MEM ALLOC:</span><span class="data-value" id="sf-ram">-- / --</span></div>
            <div class="data-row"><span class="data-label">UPTIME:</span><span class="data-value" id="sf-uptime">--:--:--</span></div>
            <div class="data-row"><span class="data-label">STATUS:</span><span class="data-value" id="sf-status">AWAITING</span></div>
        </div>

        <div class="sf-panel" id="neural-net-panel">
            <div class="sf-title">NEURAL.NET</div>
            <div class="sf-accent-line"></div>
            <div class="data-row"><span class="data-label">MODEL:</span><span class="data-value" id="sf-model-name">DISCONNECTED</span></div>
            <div class="data-row"><span class="data-label">STATE:</span><span class="data-value" id="sf-model-state">--</span></div>
        </div>

        <div class="sf-panel" id="job-queue-panel">
            <div class="sf-title">JOB.QUEUE</div>
            <div class="sf-accent-line"></div>
            <div class="data-row"><span class="data-label">ACTIVE:</span><span class="data-value" id="sf-job-active">0</span></div>
            <div class="data-row"><span class="data-label">PENDING:</span><span class="data-value" id="sf-job-pending">0</span></div>
        </div>

        <div class="sf-panel" id="system-logs-panel">
            <div class="sf-title">SYS.LOGS</div>
            <div class="sf-accent-line"></div>
            <div class="log-content" id="sf-log-content">
                <!-- Logs will be populated here -->
            </div>
        </div>

    </div>

    <!-- APP TRAY BUTTON AND MODAL -->
    <div id="sf-app-tray-btn" title="Launch Systems">[ LAUNCH SYSTEMS ]</div>
    <div id="sf-app-tray">
        <div class="tray-title">AVAILABLE SUBSYSTEMS</div>
        <div id="sf-tray-grid"></div>
    </div>
"""
content = re.sub(r'(<body.*?>)', r'\1\n' + bg_layer, content)

# Step 4: Hide old dock entirely using regex
content = re.sub(r'(<div id="dock".*?>)', r'<div id="dock" style="display: none;">', content)

# Step 5: Replace theme dropdown with custom colors
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
content = re.sub(r'<div class="settings-row">\s*<span>Theme</span>\s*<select id="setting-theme" onchange="toggleTheme\(\)">[\s\S]*?</select>\s*</div>', theme_dropdown_new, content)

# Step 6: Inject JS for Polling
health_injection = """
                        // SF PANEL UPDATES
                        const sfCpu = document.getElementById('sf-cpu');
                        if(sfCpu) sfCpu.innerText = data.system.cpu_percent + '%';

                        const sfRam = document.getElementById('sf-ram');
                        if(sfRam) {
                            const used = (data.system.ram_used_gb).toFixed(1);
                            const total = (data.system.ram_total_gb).toFixed(1);
                            sfRam.innerText = used + 'GB / ' + total + 'GB';
                        }

                        const sfUptime = document.getElementById('sf-uptime');
                        if(sfUptime) sfUptime.innerText = data.lyrn.uptime;

                        const sfStatus = document.getElementById('sf-status');
                        if(sfStatus) sfStatus.innerText = data.lyrn.status;

                        const sfModelName = document.getElementById('sf-model-name');
                        if(sfModelName) sfModelName.innerText = data.llm.active_model;

                        const sfModelState = document.getElementById('sf-model-state');
                        if(sfModelState) sfModelState.innerText = data.llm.status;
"""
content = content.replace("document.getElementById('sys-cpu').innerText = finalText;", "document.getElementById('sys-cpu').innerText = finalText;\n" + health_injection)

job_log_polling = """
        // SF MONITORING SPECIFIC POLLING
        async function fetchMonitoringData() {
            try {
                const logsRes = await fetch(coreUrl + '/api/system/logs?lines=10', { headers: { 'Authorization': 'Bearer ' + authToken }});
                if(logsRes.ok) {
                    const logsData = await logsRes.json();
                    const logContainer = document.getElementById('sf-log-content');
                    if(logContainer && logsData.logs) {
                        logContainer.innerHTML = '';
                        // Show last 10 logs
                        logsData.logs.slice(-10).forEach(log => {
                            const div = document.createElement('div');
                            div.className = 'log-entry';
                            if(log.toLowerCase().includes('error')) div.classList.add('error');
                            div.innerText = log.length > 80 ? log.substring(0, 80) + '...' : log;
                            logContainer.appendChild(div);
                        });
                    }
                }

                const jobsRes = await fetch(coreUrl + '/api/jobs/status', { headers: { 'Authorization': 'Bearer ' + authToken }});
                if(jobsRes.ok) {
                    const jobsData = await jobsRes.json();
                    const sfActive = document.getElementById('sf-job-active');
                    const sfPending = document.getElementById('sf-job-pending');
                    if(sfActive) sfActive.innerText = jobsData.active_jobs ? jobsData.active_jobs.length : 0;
                    if(sfPending) sfPending.innerText = jobsData.pending_jobs ? jobsData.pending_jobs.length : 0;
                }

            } catch (err) {
                console.warn("Monitoring data fetch failed.");
            }
        }

        setInterval(fetchMonitoringData, 5000);
        setTimeout(fetchMonitoringData, 1000);
"""
content = content.replace("monitorInterval = setInterval(fetchStats, 2000);", "monitorInterval = setInterval(fetchStats, 2000);\n" + job_log_polling)

# Step 7: Inject JS for Tray and Theme
tray_js = """
        // TRAY LOGIC & THEME LOGIC
        const trayBtn = document.getElementById('sf-app-tray-btn');
        const appTray = document.getElementById('sf-app-tray');
        const trayGrid = document.getElementById('sf-tray-grid');

        let trayOpen = false;

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

        // Close tray when clicking outside
        document.addEventListener('mousedown', (e) => {
            if(trayOpen && appTray && !appTray.contains(e.target) && e.target !== trayBtn) {
                trayOpen = false;
                appTray.classList.remove('open');
            }
        });

        function renderTray() {
            if(!trayGrid) return;
            trayGrid.innerHTML = '';

            // Define registry here locally for the tray
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
                    // Need to find the original object so toggleWindow works
                    const origMod = MODULE_REGISTRY.find(m => m.id === mod.id);
                    if(origMod) toggleWindow(origMod);
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

        function changeSFTheme(themeName) {
            document.body.setAttribute('data-theme', themeName);
            appSettings.theme = themeName;
            saveSettings();
        }

        // Setup initial theme
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

content = content.replace("document.addEventListener('DOMContentLoaded', () => {", "document.addEventListener('DOMContentLoaded', () => {\n" + tray_js)

with open("LYRN_v6/dashboard.html", "r") as f:
    dash_content = f.read()

# Fix Nav links
nav_btn_1 = """            <button class="bar-btn" title="Switch to Sci-Fi Monitoring" onclick="window.location.href='dashboard-monitoring.html'">[SCI-FI]</button>\n"""
dash_content = dash_content.replace('<button class="bar-btn" title="Help" onclick="openWelcome()">?</button>', nav_btn_1 + '            <button class="bar-btn" title="Help" onclick="openWelcome()">?</button>')
with open("LYRN_v6/dashboard.html", "w") as f:
    f.write(dash_content)

nav_btn_2 = """            <button class="bar-btn" style="color: var(--theme-primary); margin-right: 10px;" title="Switch to Classic Desktop" onclick="window.location.href='dashboard.html'">[CLASSIC]</button>\n"""
content = re.sub(r'(<button class="bar-btn" title="Help" onclick="openWelcome\(\)">\?</button>)', nav_btn_2 + r'\1', content)

with open("LYRN_v6/dashboard-monitoring.html", "w") as f:
    f.write(content)
