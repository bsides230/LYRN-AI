import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# We need to hook into updateHealth() and fetchLogs() to push data to our new SF panels.

# Look for: document.getElementById('sys-cpu').innerText = data.system.cpu_percent + '%';
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

content = content.replace("document.getElementById('sys-cpu').innerText = data.system.cpu_percent + '%';",
                          "document.getElementById('sys-cpu').innerText = data.system.cpu_percent + '%';\n" + health_injection)


with open("LYRN_v6/dashboard-monitoring.html", "w") as f:
    f.write(content)
