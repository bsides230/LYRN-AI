import re

with open("LYRN_v6/dashboard-monitoring.html", "r") as f:
    content = f.read()

# Instead of relying on a fetchLogs that might not be in the base dashboard.html,
# let's add a dedicated polling function for Jobs and Logs specifically for the SF background.
# Find the end of checkServerHealth() to inject.

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

# Insert right before checkServerHealth() interval
content = content.replace("setInterval(checkServerHealth, 3000);", "setInterval(checkServerHealth, 3000);\n" + job_log_polling)

with open("LYRN_v6/dashboard-monitoring.html", "w") as f:
    f.write(content)
