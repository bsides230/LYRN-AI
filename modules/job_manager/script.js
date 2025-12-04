// Global state
let currentJobs = {};
let currentSchedules = [];
let currentCycles = {};
let selectedJob = null;
let selectedCycle = null;
let currentDate = new Date();
let selectedDate = null; // For scheduler modal

const API_BASE = '/api';

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    fetchJobs();

    // Load theme
    const savedTheme = localStorage.getItem('theme') || 'dark';
    if(savedTheme === 'light') {
        document.body.setAttribute('data-theme', 'light');
        const themeToggle = document.getElementById('theme-toggle');
        if(themeToggle) themeToggle.checked = true;
    }
});

// --- Tabs ---
function switchTab(tabId) {
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

    document.querySelector(`.nav-tab[onclick="switchTab('${tabId}')"]`).classList.add('active');
    document.getElementById(`tab-${tabId}`).classList.add('active');

    if (tabId === 'scheduler') {
        refreshScheduler();
    } else if (tabId === 'cycles') {
        fetchCycles();
    }
}

// --- Theme ---
function toggleTheme(isLight) {
    const theme = isLight ? 'light' : 'dark';
    document.body.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
}

// --- Utils ---
function showToast(message, isError = false) {
    const toast = document.getElementById('toast');
    toast.innerText = message;
    toast.style.borderColor = isError ? 'var(--error-color)' : 'var(--brand-purple)';
    toast.style.color = isError ? 'var(--error-color)' : 'var(--text-head)';
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
}

function escapeHtml(text) {
    if (!text) return "";
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// ==========================================
// JOBS MANAGER
// ==========================================

async function fetchJobs() {
    try {
        const response = await fetch(`${API_BASE}/jobs`);
        if (!response.ok) throw new Error('Failed to fetch jobs');
        currentJobs = await response.json();
        renderJobsList();
    } catch (error) {
        showToast(`Error: ${error.message}`, true);
    }
}

function renderJobsList() {
    const listEl = document.getElementById('jobs-list');
    listEl.innerHTML = '';

    const jobNames = Object.keys(currentJobs).sort();

    jobNames.forEach(name => {
        const job = currentJobs[name];
        const isPinned = job.pinned === true;
        const item = document.createElement('div');
        item.className = `list-item ${selectedJob === name ? 'selected' : ''}`;

        item.innerHTML = `
            <span class="item-name">${name}</span>
            <span class="pin-icon ${isPinned ? 'pinned' : ''}" title="${isPinned ? 'Unpin' : 'Pin'}" onclick="togglePin(event, '${name}')">📌</span>
            <span class="btn-icon" style="color: var(--error-color); cursor: pointer;" title="Delete" onclick="deleteJob(event, '${name}')">✕</span>
        `;
        item.onclick = (e) => {
            if(e.target.classList.contains('pin-icon') || e.target.classList.contains('btn-icon')) return;
            selectJob(name);
        };
        listEl.appendChild(item);
    });
}

async function togglePin(event, name) {
    event.stopPropagation();
    try {
        const response = await fetch(`${API_BASE}/pin_job`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name })
        });
        if (!response.ok) throw new Error('Failed to toggle pin');

        fetchJobs(); // Refresh list
        showToast(`Toggled pin for ${name}`);
    } catch (error) {
        showToast(`Error: ${error.message}`, true);
    }
}

function selectJob(name) {
    selectedJob = name;
    renderJobsList();

    document.getElementById('job-editor-title').innerText = `Editing: ${name}`;
    // Run button only for existing jobs
    const runBtn = document.getElementById('run-job-btn');
    if(runBtn) runBtn.style.display = 'block';

    const jobData = currentJobs[name];
    renderJobEditor(name, jobData);
}

function addNewJob() {
    selectedJob = '_NEW_';
    renderJobsList(); // Updates selection visual

    document.getElementById('job-editor-title').innerText = 'New Job';
    const runBtn = document.getElementById('run-job-btn');
    if(runBtn) runBtn.style.display = 'none';

    renderJobEditor('_NEW_', { instructions: '', trigger: '' });
}

function renderJobEditor(name, data) {
    const container = document.getElementById('job-editor-container');
    container.innerHTML = '';

    if (name === '_NEW_') {
         container.innerHTML = `
            <div class="form-group">
                <label>Job Name</label>
                <input type="text" id="edit-job-name" value="" placeholder="e.g., analyze_sentiment">
            </div>
         `;
    }

    container.innerHTML += `
        <div class="form-group">
            <label>Instructions (for build_prompt)</label>
            <textarea id="edit-job-instructions" style="height: 200px; font-family: monospace;">${escapeHtml(data.instructions || '')}</textarea>
        </div>
        <div class="form-group">
            <label>Trigger Prompt (for LLM execution)</label>
            <textarea id="edit-job-trigger" style="height: 100px; font-family: monospace;">${escapeHtml(data.trigger || '')}</textarea>
        </div>
    `;
}

async function saveCurrentJob() {
    const isNew = selectedJob === '_NEW_';
    const name = isNew ? document.getElementById('edit-job-name').value.trim() : selectedJob;

    if (!name) {
        showToast('Job name is required', true);
        return;
    }

    const data = {
        instructions: document.getElementById('edit-job-instructions').value,
        trigger: document.getElementById('edit-job-trigger').value
    };

    try {
        const response = await fetch(`${API_BASE}/job/${name}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error('Failed to save');
        showToast('Job Saved');
        selectedJob = name;
        fetchJobs();
    } catch (error) {
        showToast(`Error saving: ${error.message}`, true);
    }
}

async function deleteJob(event, name) {
    if(event) event.stopPropagation();

    const job = currentJobs[name];
    if (job && job.pinned) {
        showToast("Cannot delete pinned job", true);
        return;
    }

    if (!confirm(`Delete job '${name}'?`)) return;

    try {
        const response = await fetch(`${API_BASE}/job/${encodeURIComponent(name)}`, { method: 'DELETE' });
        if (!response.ok) throw new Error('Delete failed');
        showToast(`Deleted ${name}`);
        if(selectedJob === name) {
            selectedJob = null;
            document.getElementById('job-editor-container').innerHTML = '<p style="color: var(--text-dim); padding: 20px; text-align: center;">Select a job to edit.</p>';
            const runBtn = document.getElementById('run-job-btn');
            if(runBtn) runBtn.style.display = 'none';
        }
        fetchJobs();
    } catch (error) {
        showToast(`Delete error: ${error.message}`, true);
    }
}

async function runJob() {
    const jobToRun = selectedJob;
    if (!jobToRun || jobToRun === '_NEW_') {
        showToast("Select a saved job to run", true);
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/run_job/${jobToRun}`, { method: 'POST' });
        if (!response.ok) throw new Error('Failed to run job');
        showToast(`Job '${jobToRun}' triggered`);
    } catch (error) {
        showToast(`Run error: ${error.message}`, true);
    }
}


// ==========================================
// SCHEDULER
// ==========================================

async function refreshScheduler() {
    try {
        const response = await fetch(`${API_BASE}/schedules`);
        if (!response.ok) throw new Error('Failed to fetch schedules');
        currentSchedules = await response.json();
        renderCalendar();
    } catch (error) {
        showToast(`Error: ${error.message}`, true);
    }
}

function renderCalendar() {
    const grid = document.getElementById('calendar-grid');
    grid.innerHTML = '';

    // Header
    const monthYear = currentDate.toLocaleString('default', { month: 'long', year: 'numeric' });
    document.getElementById('current-month-label').innerText = monthYear;

    // Days header
    ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].forEach(day => {
        const d = document.createElement('div');
        d.className = 'day-number';
        d.style.textAlign = 'center';
        d.style.marginBottom = '5px';
        d.innerText = day;
        grid.appendChild(d);
    });

    // Calendar logic
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    // Empty slots
    for (let i = 0; i < firstDay; i++) {
        grid.appendChild(document.createElement('div'));
    }

    const today = new Date();

    for (let d = 1; d <= daysInMonth; d++) {
        const dateObj = new Date(year, month, d);
        const dayEl = document.createElement('div');
        dayEl.className = 'calendar-day';
        if (dateObj.toDateString() === today.toDateString()) dayEl.classList.add('today');

        // Find schedules for this day
        const schedules = currentSchedules.filter(s => {
            const sDate = new Date(s.scheduled_datetime);
            return sDate.toDateString() === dateObj.toDateString();
        });

        let eventsHtml = '';
        if (schedules.length > 0) {
            eventsHtml = `<div class="day-events">
                ${schedules.length} job${schedules.length > 1 ? 's' : ''}
                <div style="display:flex; gap:2px; margin-top:2px;">
                    ${schedules.map(() => '<span class="event-dot"></span>').join('')}
                </div>
            </div>`;
        }

        dayEl.innerHTML = `
            <div class="day-number">${d}</div>
            ${eventsHtml}
        `;

        dayEl.onclick = () => openSchedulerModal(dateObj);
        grid.appendChild(dayEl);
    }
}

function prevMonth() {
    currentDate.setMonth(currentDate.getMonth() - 1);
    renderCalendar();
}

function nextMonth() {
    currentDate.setMonth(currentDate.getMonth() + 1);
    renderCalendar();
}

function openSchedulerModal(date) {
    selectedDate = date;
    const modal = document.getElementById('scheduler-modal');
    modal.style.display = 'flex';
    document.getElementById('scheduler-modal-title').innerText = `Schedule: ${date.toDateString()}`;

    renderDaySchedulesList();
    populateJobSelect('scheduler-job-select');
}

function closeSchedulerModal() {
    document.getElementById('scheduler-modal').style.display = 'none';
}

function renderDaySchedulesList() {
    const listEl = document.getElementById('day-schedules-list');
    listEl.innerHTML = '';

    const schedules = currentSchedules.filter(s => {
        const sDate = new Date(s.scheduled_datetime);
        return sDate.toDateString() === selectedDate.toDateString();
    });

    if (schedules.length === 0) {
        listEl.innerHTML = '<p style="color:var(--text-dim)">No jobs scheduled.</p>';
        return;
    }

    schedules.sort((a,b) => new Date(a.scheduled_datetime) - new Date(b.scheduled_datetime));

    schedules.forEach(s => {
        // Display time in local format (AM/PM)
        const time = new Date(s.scheduled_datetime).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true });
        const item = document.createElement('div');
        item.style.display = 'flex';
        item.style.justifyContent = 'space-between';
        item.style.alignItems = 'center';
        item.style.padding = '5px 0';
        item.style.borderBottom = '1px solid var(--border-color)';

        item.innerHTML = `
            <span><span class="mono" style="color:var(--brand-purple)">${time}</span> - ${s.job_name}</span>
            <button class="btn-delete btn-icon" onclick="deleteSchedule('${s.id}')">Del</button>
        `;
        listEl.appendChild(item);
    });
}

function populateJobSelect(selectId) {
    const select = document.getElementById(selectId);
    select.innerHTML = '';
    Object.keys(currentJobs).sort().forEach(name => {
        const option = document.createElement('option');
        option.value = name;
        option.innerText = name;
        select.appendChild(option);
    });
}

async function addSchedule() {
    const jobName = document.getElementById('scheduler-job-select').value;
    let h = parseInt(document.getElementById('sched-hour').value) || 12;
    const m = parseInt(document.getElementById('sched-minute').value) || 0;
    const ampm = document.getElementById('sched-ampm').value;

    if (!jobName) return;

    // Convert 12h to 24h
    if (ampm === 'PM' && h < 12) h += 12;
    if (ampm === 'AM' && h === 12) h = 0;

    const dt = new Date(selectedDate);
    dt.setHours(h, m, 0);

    // Create a local ISO string (YYYY-MM-DDTHH:MM:SS) to send to backend
    // The backend should treat this as "Server Local Time"
    const offsetMs = dt.getTimezoneOffset() * 60000;
    const localISOTime = (new Date(dt.getTime() - offsetMs)).toISOString().slice(0, -1);

    try {
        const response = await fetch(`${API_BASE}/schedule`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                job_name: jobName,
                scheduled_datetime: localISOTime // Send naive local time (or pretend UTC)
            })
        });
        if (!response.ok) throw new Error('Failed to add schedule');

        await refreshScheduler(); // Reload global list
        renderDaySchedulesList(); // Update modal
        showToast('Schedule added');
    } catch (error) {
        showToast(`Error: ${error.message}`, true);
    }
}

async function deleteSchedule(id) {
    if (!confirm('Delete this schedule?')) return;
    try {
        const response = await fetch(`${API_BASE}/schedule/${id}`, { method: 'DELETE' });
        if (!response.ok) throw new Error('Failed delete');
        await refreshScheduler();
        renderDaySchedulesList();
        showToast('Schedule deleted');
    } catch (error) {
        showToast(`Error: ${error.message}`, true);
    }
}


// ==========================================
// CYCLES MANAGER
// ==========================================

async function fetchCycles() {
    try {
        const response = await fetch(`${API_BASE}/cycles`);
        if (!response.ok) throw new Error('Failed to fetch cycles');
        currentCycles = await response.json();
        renderCyclesList();
    } catch (error) {
        showToast(`Error: ${error.message}`, true);
    }
}

function renderCyclesList() {
    const listEl = document.getElementById('cycles-list');
    listEl.innerHTML = '';

    const cycleNames = Object.keys(currentCycles).sort();

    cycleNames.forEach(name => {
        const item = document.createElement('div');
        item.className = `list-item ${selectedCycle === name ? 'selected' : ''}`;
        item.innerHTML = `
            <span class="item-name">${name}</span>
            <span class="btn-icon" style="color: var(--error-color); cursor: pointer;" title="Delete" onclick="deleteCycle(event, '${name}')">✕</span>
        `;
        item.onclick = (e) => {
            if(e.target.classList.contains('btn-icon')) return;
            selectCycle(name);
        };
        listEl.appendChild(item);
    });
}

function selectCycle(name) {
    selectedCycle = name;
    renderCyclesList();

    document.getElementById('cycle-editor-title').innerText = `Cycle: ${name}`;

    const cycleData = currentCycles[name];
    renderCycleEditor(name, cycleData);
}

function addNewCycle() {
    selectedCycle = '_NEW_';
    renderCyclesList();

    document.getElementById('cycle-editor-title').innerText = 'New Cycle';

    renderCycleEditor('_NEW_', { triggers: [] });
}

function renderCycleEditor(name, data) {
    const container = document.getElementById('cycle-editor-container');
    container.innerHTML = '';

    if (name === '_NEW_') {
         container.innerHTML = `
            <div class="form-group">
                <label>Cycle Name</label>
                <input type="text" id="edit-cycle-name" value="">
            </div>
         `;
    }

    // Triggers editor (Simple text area for JSON editing for now, or a list builder)
    // For simplicity, let's just use a JSON textarea for triggers initially.
    // Ideally this would be a draggable list UI.
    const triggersJson = JSON.stringify(data.triggers || [], null, 2);

    container.innerHTML += `
        <div class="form-group">
            <label>Cycle Triggers (JSON Format)</label>
            <p style="font-size:10px; color:var(--text-dim); margin-top:-5px; margin-bottom:5px;">
                List of objects: [{"name": "Step 1", "prompt": "..."}]
            </p>
            <textarea id="edit-cycle-triggers" style="height: 300px; font-family: monospace;">${triggersJson}</textarea>
        </div>
    `;
}

async function saveCurrentCycle() {
    const isNew = selectedCycle === '_NEW_';
    const name = isNew ? document.getElementById('edit-cycle-name').value.trim() : selectedCycle;

    if (!name) {
        showToast('Cycle name required', true);
        return;
    }

    let triggers = [];
    try {
        triggers = JSON.parse(document.getElementById('edit-cycle-triggers').value);
    } catch (e) {
        showToast('Invalid JSON for triggers', true);
        return;
    }

    const data = { triggers: triggers };

    try {
        const response = await fetch(`${API_BASE}/cycle/${name}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error('Failed to save cycle');
        showToast('Cycle Saved');
        selectedCycle = name;
        fetchCycles();
    } catch (error) {
        showToast(`Error saving: ${error.message}`, true);
    }
}

async function deleteCycle(event, name) {
    if(event) event.stopPropagation();

    if (!confirm(`Delete cycle '${name}'?`)) return;

    try {
        const response = await fetch(`${API_BASE}/cycle/${encodeURIComponent(name)}`, { method: 'DELETE' });
        if (!response.ok) throw new Error('Delete failed');
        showToast(`Deleted ${name}`);
        if(selectedCycle === name) {
            selectedCycle = null;
            document.getElementById('cycle-editor-container').innerHTML = '<p style="color: var(--text-dim); padding: 20px; text-align: center;">Select a cycle to edit.</p>';
        }
        fetchCycles();
    } catch (error) {
        showToast(`Delete error: ${error.message}`, true);
    }
}

